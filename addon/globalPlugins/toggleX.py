# toggleX: flip common NVDA settings and swap synthesizers from a single layered command.
# Copyright (C) 2012-2023 Tyler Spivey <tspivey@pcdesk.net> and Erion
# Copyright (C) 2026 Josh Kennedy <joshknnd1982@gmail.com>
# This file is covered by the GNU General Public License version 2.
# See the file LICENSE for more details.

import json
import os
import pickle
from functools import wraps
from typing import NamedTuple

import addonHandler
import config
import globalPluginHandler
import globalVars
import speech
import synthDriverHandler
import tones
import ui
from config.configFlags import ReportLineIndentation, ReportTableHeaders
from logHandler import log
from scriptHandler import script

try:
	addonHandler.initTranslation()
except addonHandler.AddonError:
	# Running from the scratchpad rather than an installed add-on; NVDA's own catalogue will do.
	pass

#: Where the synthesizer slots are stored, relative to the user's configuration directory.
CONFIG_FILE_NAME = "toggleX.json"
#: The pickle written by toggleX 0.x, imported once and then left alone.
LEGACY_CONFIG_FILE_NAME = "switch_synth.pickle"

#: Our section in NVDA's own configuration.
CONFIG_SECTION = "toggleX"

#: State that NVDA has nowhere else to keep. Living in config.conf means NVDA saves it
#: along with everything else on NVDA+control+c, and restores it on the next start.
CONFIG_SPEC = {
	"speechDictionaryProcessing": "boolean(default=true)",
	"textProcessing": "boolean(default=true)",
	"activeSlot": "integer(default=1)",
	# The mode to come back to when a multi-state setting is switched on again.
	"lineIndentationMode": "integer(0, 3, default=3)",
	"tableHeadersMode": "integer(0, 3, default=1)",
}
config.conf.spec[CONFIG_SECTION] = CONFIG_SPEC


class BooleanSetting(NamedTuple):
	section: str
	key: str
	label: str


class MultiStateSetting(NamedTuple):
	section: str
	key: str
	flags: type
	defaultOn: int
	#: Key under CONFIG_SECTION holding the mode to restore when switching back on.
	modeKey: str
	label: str


#: Two state NVDA settings, keyed by the key pressed after NVDA+0.
BOOLEAN_SETTINGS = {
	# Translators: Announced when toggling reporting of tables.
	"t": BooleanSetting("documentFormatting", "reportTables", _("Tables")),
	# Translators: Announced when toggling reporting of headings.
	"h": BooleanSetting("documentFormatting", "reportHeadings", _("Headings")),
	# Translators: Announced when toggling reporting of lists.
	"l": BooleanSetting("documentFormatting", "reportLists", _("Lists")),
	# Translators: Announced when toggling reporting of table cell coordinates.
	"c": BooleanSetting("documentFormatting", "reportTableCellCoords", _("Cell coordinates")),
	# Translators: Announced when toggling reporting of links.
	"k": BooleanSetting("documentFormatting", "reportLinks", _("Links")),
	# Translators: Announced when toggling reporting of object position information.
	"p": BooleanSetting("presentation", "reportObjectPositionInformation", _("Position")),
	# Translators: Announced when toggling reporting of keyboard shortcuts.
	"u": BooleanSetting("presentation", "reportKeyboardShortcuts", _("Shortcuts")),
	# Translators: Announced when toggling automatic language switching.
	"m": BooleanSetting("speech", "autoLanguageSwitching", _("Automatic language switching")),
	# Translators: Announced when toggling trusting the voice's language.
	"r": BooleanSetting("speech", "trustVoiceLanguage", _("Trust voice language")),
}

#: NVDA settings with more than an on and off state. These are announced as on or off like
#: everything else, but the chosen mode is preserved across a toggle rather than being
#: flattened to a boolean.
MULTI_STATE_SETTINGS = {
	"i": MultiStateSetting(
		"documentFormatting",
		"reportLineIndentation",
		ReportLineIndentation,
		ReportLineIndentation.SPEECH_AND_TONES,
		"lineIndentationMode",
		# Translators: Announced when toggling reporting of line indentation.
		_("Indentation"),
	),
	"o": MultiStateSetting(
		"documentFormatting",
		"reportTableHeaders",
		ReportTableHeaders,
		ReportTableHeaders.ROWS_AND_COLUMNS,
		"tableHeadersMode",
		# Translators: Announced when toggling reporting of table headers.
		_("Table headers"),
	),
}

#: Keys that load a saved synthesizer, mapped to their slot number.
SYNTH_SLOTS = {
	"1": 1,
	"2": 2,
	"3": 3,
	"4": 4,
	"5": 5,
	"6": 6,
	"7": 7,
	"8": 8,
	"9": 9,
	"0": 0,
	"-": 11,
	"=": 12,
	"`": 13,
}

#: Synthesizer settings saved and restored with a slot, in the order they must be applied.
#: Voice comes first because changing it reloads that voice's own rate, pitch and volume.
SYNTH_SETTINGS = ("voice", "variant", "rate", "pitch", "volume")


def finally_(func, final):
	"""Returns a wrapper around func that calls final afterwards, even if func fails."""

	@wraps(func)
	def new(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		finally:
			final()

	return new


def passThroughText(locale, text, symbolLevel, normalize=False):
	"""Stands in for speech.speech.processText, returning text untouched.

	The signature must track NVDA's, which passes the first three arguments positionally
	and normalize by keyword.
	"""
	return text


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	# Translators: The category for toggleX commands in the Input Gestures dialog.
	scriptCategory = _("toggleX")

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.synths = {}
		self.toggling = False
		#: NVDA's real processText while the z toggle is suppressing text processing.
		self.originalProcessText = None
		keys = list(BOOLEAN_SETTINGS) + list(MULTI_STATE_SETTINGS) + list(SYNTH_SLOTS) + ["d", "a", "z"]
		self.__toggleGestures = {"kb:%s" % key: "toggleX" for key in keys}
		self.load()
		self.applySavedState()
		# A profile switch can bring a different toggleX section into view.
		config.post_configProfileSwitch.register(self.handleConfigProfileSwitch)

	def terminate(self):
		config.post_configProfileSwitch.unregister(self.handleConfigProfileSwitch)
		# Unloading the add-on must not leave NVDA patched, but it must not look like the
		# user switched processing back on either, so this doesn't touch the config.
		self.unpatchTextProcessing()
		super().terminate()

	def handleConfigProfileSwitch(self, **kwargs):
		self.applySavedState()

	def applySavedState(self):
		"""Brings the settings NVDA has nowhere else to keep back in line with the config.

		Everything else toggleX touches lives in NVDA's own configuration and is restored by
		NVDA itself; these two are a plain module variable and a patched function.
		"""
		section = config.conf[CONFIG_SECTION]
		self.setDictionaryProcessing(section["speechDictionaryProcessing"])
		self.setTextProcessing(section["textProcessing"])

	# Slots live in their own file, but which one is active belongs with the rest of the
	# state NVDA saves, so that NVDA+control+c and profile switches cover it too.
	def _get_activeSlot(self):
		return config.conf[CONFIG_SECTION]["activeSlot"]

	def _set_activeSlot(self, slot):
		config.conf[CONFIG_SECTION]["activeSlot"] = slot

	def getConfigPath(self, fileName):
		# appArgs.configPath is the directory NVDA is actually using, and writes to itself.
		# config.getUserDefaultConfigPath() only knows where an installed copy would keep
		# its configuration: it ignores --config-path, and for every other copy it answers
		# with a path relative to the working directory.
		return os.path.join(globalVars.appArgs.configPath, fileName)

	def load(self):
		path = self.getConfigPath(CONFIG_FILE_NAME)
		if not os.path.isfile(path):
			self.importLegacySlots()
			return
		try:
			with open(path, "r", encoding="utf-8") as f:
				self.synths = {int(slot): settings for slot, settings in json.load(f).items()}
		except OSError:
			log.error("toggleX: could not read %s" % path, exc_info=True)
		except ValueError:
			# Every slot now looks empty, and saving one would write over the file that
			# still holds them, so keep the original for the user to salvage.
			log.error("toggleX: could not parse %s" % path, exc_info=True)
			self.setAside(path)

	def setAside(self, path):
		"""Renames a slots file that could not be read, so that it is not written over."""
		keptPath = "%s.bad" % path
		try:
			os.replace(path, keptPath)
		except OSError:
			log.error("toggleX: could not move %s aside" % path, exc_info=True)
			return
		log.warning("toggleX: %s could not be read and has been kept as %s" % (path, keptPath))

	def importLegacySlots(self):
		"""Brings across the slots saved by toggleX 0.x, which used a pickle file."""
		path = self.getConfigPath(LEGACY_CONFIG_FILE_NAME)
		if not os.path.isfile(path):
			return
		try:
			with open(path, "rb") as f:
				self.synths = {int(slot): settings for slot, settings in pickle.load(f).items()}
		except Exception:
			log.error("toggleX: could not import legacy slots from %s" % path, exc_info=True)
			return
		log.info("toggleX: imported %d synthesizer slots from %s" % (len(self.synths), path))
		self.write()

	def write(self):
		"""Writes the slots out, reporting whether they reached the disk.

		Encoding everything before going near the file, and then replacing the file rather
		than writing over it, means a failure leaves the slots that were already saved
		alone. Writing in place empties the file first, and a synthesizer that hands back
		something JSON cannot encode would take every saved slot with it.
		"""
		path = self.getConfigPath(CONFIG_FILE_NAME)
		try:
			slots = json.dumps({str(slot): settings for slot, settings in self.synths.items()}, indent="\t")
		except (TypeError, ValueError):
			log.error("toggleX: could not encode the synthesizer slots", exc_info=True)
			return False
		newPath = "%s.new" % path
		try:
			with open(newPath, "w", encoding="utf-8") as f:
				f.write(slots)
			os.replace(newPath, path)
		except OSError:
			log.error("toggleX: could not write %s" % path, exc_info=True)
			return False
		return True

	def setSynth(self, slot):
		self.activeSlot = slot
		settings = self.synths.get(slot)
		if settings is None:
			# Translators: Announced when a synthesizer slot has nothing saved in it.
			ui.message(_("Empty slot"))
			return
		name = settings["name"]
		if not synthDriverHandler.setSynth(name):
			# Translators: Announced when a saved synthesizer could not be loaded.
			ui.message(_("Could not load {synth}").format(synth=name))
			return
		synth = synthDriverHandler.getSynth()
		if synth is None:
			ui.message(_("Could not load {synth}").format(synth=name))
			return
		for setting in SYNTH_SETTINGS:
			value = settings.get(setting)
			if value is None or not synth.isSupported(setting):
				continue
			if setting == "voice":
				if synth.voice != value:
					# changeVoice does the initialisation that assigning to voice alone skips.
					synthDriverHandler.changeVoice(synth, value)
				continue
			setattr(synth, setting, value)
		# Applying a slot only changes the running driver. Without this, the config still
		# holds the settings the synthesizer was loaded with, so saving the configuration
		# would write those back and the slot would be lost on the next start.
		synth.saveSettings()
		ui.message(synth.description or synth.name)

	def saveSynth(self):
		synth = synthDriverHandler.getSynth()
		if synth is None:
			# Translators: Announced when asked to save a synthesizer while none is active.
			ui.message(_("No synthesizer is active"))
			return
		settings = {"name": synth.name}
		for setting in SYNTH_SETTINGS:
			if synth.isSupported(setting):
				settings[setting] = getattr(synth, setting)
		self.synths[self.activeSlot] = settings
		if not self.write():
			# The slot still works for the rest of this session, but saying it was saved
			# would be a lie: it will not be there the next time NVDA starts.
			# Translators: Announced when a synthesizer slot could not be written to disk.
			ui.message(_("Could not save slot {slot}").format(slot=self.activeSlot))
			return
		# Translators: Announced when the current synthesizer is saved into the active slot.
		ui.message(_("Saved to slot {slot}").format(slot=self.activeSlot))

	def onoff(self, value, msg=None):
		if msg:
			ui.message(msg)
		if value:
			tones.beep(700, 120)
		else:
			tones.beep(270, 80)

	def toggleBoolean(self, key):
		setting = BOOLEAN_SETTINGS[key]
		value = not config.conf[setting.section][setting.key]
		config.conf[setting.section][setting.key] = value
		self.onoff(value, setting.label)

	def toggleMultiState(self, key):
		setting = MULTI_STATE_SETTINGS[key]
		current = config.conf[setting.section][setting.key]
		label = setting.label
		if current != setting.flags.OFF.value:
			config.conf[CONFIG_SECTION][setting.modeKey] = current
			config.conf[setting.section][setting.key] = setting.flags.OFF.value
			self.onoff(False, label)
			return
		value = config.conf[CONFIG_SECTION][setting.modeKey]
		if value == setting.flags.OFF.value:
			value = setting.defaultOn.value
		config.conf[setting.section][setting.key] = value
		try:
			# Say which mode came back, since these settings have more than two states.
			label = "%s %s" % (label, setting.flags(value).displayString)
		except ValueError:
			pass
		self.onoff(True, label)

	def setDictionaryProcessing(self, enabled):
		globalVars.speechDictionaryProcessing = enabled
		config.conf[CONFIG_SECTION]["speechDictionaryProcessing"] = enabled

	def toggleDictionaryProcessing(self):
		enabled = not globalVars.speechDictionaryProcessing
		self.setDictionaryProcessing(enabled)
		# Translators: Announced when toggling speech dictionary processing.
		self.onoff(enabled, _("Dictionary"))

	def unpatchTextProcessing(self):
		"""Puts NVDA's own processText back without recording that as a preference."""
		if self.originalProcessText is None:
			return
		if speech.speech.processText is passThroughText:
			speech.speech.processText = self.originalProcessText
		self.originalProcessText = None

	def setTextProcessing(self, enabled):
		if enabled:
			self.unpatchTextProcessing()
		elif self.originalProcessText is None:
			self.originalProcessText = speech.speech.processText
			speech.speech.processText = passThroughText
		config.conf[CONFIG_SECTION]["textProcessing"] = enabled

	def toggleTextProcessing(self):
		# Processing is suppressed exactly while we are holding NVDA's original function.
		enabled = self.originalProcessText is not None
		self.setTextProcessing(enabled)
		# Translators: Announced when toggling all symbol, dictionary and normalization processing.
		self.onoff(enabled, _("Text processing"))

	def getScript(self, gesture):
		script = super().getScript(gesture)
		if not self.toggling:
			return script
		if not script:
			script = self.script_error
		return finally_(script, self.finish)

	def finish(self):
		self.toggling = False
		self.clearGestureBindings()
		self.bindGestures(self.__gestures)

	def script_error(self, gesture):
		# No docstring, so this stays out of the Input Gestures dialog.
		tones.beep(120, 100)

	@script(speakOnDemand=True)
	def script_toggleX(self, gesture):
		# The normalized identifiers are the ones the binding matched, so the key is lower case here.
		key = gesture.normalizedIdentifiers[-1].rsplit(":", 1)[-1]
		if key in BOOLEAN_SETTINGS:
			self.toggleBoolean(key)
		elif key in MULTI_STATE_SETTINGS:
			self.toggleMultiState(key)
		elif key in SYNTH_SLOTS:
			self.setSynth(SYNTH_SLOTS[key])
		elif key == "d":
			self.toggleDictionaryProcessing()
		elif key == "a":
			self.saveSynth()
		elif key == "z":
			self.toggleTextProcessing()
		else:
			self.script_error(gesture)

	@script(
		description=_(
			# Translators: Input help message for the toggleX layer command.
			"Starts toggleX. Press a single key afterwards to flip a setting or load a saved synthesizer.",
		),
		speakOnDemand=True,
	)
	def script_toggle(self, gesture):
		# If already toggling, send it on and clean up.
		if self.toggling:
			gesture.send()
			return
		# Alert the user to a gesture map error, rather than making the machine unusable.
		try:
			self.bindGestures(self.__toggleGestures)
		except Exception:
			# Translators: Announced when the toggleX layer could not be started.
			ui.message(_("Error binding toggle gestures"))
			raise
		self.toggling = True
		tones.beep(100, 10)

	__gestures = {
		"kb:NVDA+0": "toggle",
	}
