# toggleX: flip common NVDA settings and swap synthesizers from a single layered command.
# Copyright (C) 2012-2023 Tyler Spivey <tspivey@pcdesk.net> and Erion
# Copyright (C) 2026 Josh Kennedy <joshknnd1982@gmail.com>
# This file is covered by the GNU General Public License version 2.
# See the file LICENSE for more details.

import json
import os
import pickle
from functools import wraps

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

#: Two state settings: key -> (config section, config key, spoken label).
BOOLEAN_SETTINGS = {
	# Translators: Announced when toggling reporting of tables.
	"t": ("documentFormatting", "reportTables", _("Tables")),
	# Translators: Announced when toggling reporting of headings.
	"h": ("documentFormatting", "reportHeadings", _("Headings")),
	# Translators: Announced when toggling reporting of lists.
	"l": ("documentFormatting", "reportLists", _("Lists")),
	# Translators: Announced when toggling reporting of table cell coordinates.
	"c": ("documentFormatting", "reportTableCellCoords", _("Cell coordinates")),
	# Translators: Announced when toggling reporting of links.
	"k": ("documentFormatting", "reportLinks", _("Links")),
	# Translators: Announced when toggling reporting of object position information.
	"p": ("presentation", "reportObjectPositionInformation", _("Position")),
	# Translators: Announced when toggling reporting of keyboard shortcuts.
	"u": ("presentation", "reportKeyboardShortcuts", _("Shortcuts")),
	# Translators: Announced when toggling automatic language switching.
	"m": ("speech", "autoLanguageSwitching", _("Automatic language switching")),
	# Translators: Announced when toggling trusting the voice's language.
	"r": ("speech", "trustVoiceLanguage", _("Trust voice language")),
}

#: Settings with more than an on and off state:
#: key -> (config section, config key, flag enum, value used when switching back on, spoken label).
#: These are announced as on or off like everything else, but the chosen mode is preserved
#: across a toggle rather than being flattened to a boolean.
MULTI_STATE_SETTINGS = {
	"i": (
		"documentFormatting",
		"reportLineIndentation",
		ReportLineIndentation,
		ReportLineIndentation.SPEECH_AND_TONES,
		# Translators: Announced when toggling reporting of line indentation.
		_("Indentation"),
	),
	"o": (
		"documentFormatting",
		"reportTableHeaders",
		ReportTableHeaders,
		ReportTableHeaders.ROWS_AND_COLUMNS,
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
		self.slot = 1
		self.toggling = False
		#: NVDA's real processText while the z toggle is suppressing text processing.
		self.originalProcessText = None
		#: The last enabled value of each multi state setting, so that switching one back
		#: on restores the mode the user actually had chosen.
		self.lastEnabledValue = {}
		keys = list(BOOLEAN_SETTINGS) + list(MULTI_STATE_SETTINGS) + list(SYNTH_SLOTS) + ["d", "a", "z"]
		self.__toggleGestures = {"kb:%s" % key: "toggleX" for key in keys}
		self.load()

	def terminate(self):
		# Don't leave NVDA patched if the add-on is unloaded while processing is suppressed.
		self.restoreTextProcessing()
		super().terminate()

	def getConfigPath(self, fileName):
		return os.path.join(config.getUserDefaultConfigPath(), fileName)

	def load(self):
		path = self.getConfigPath(CONFIG_FILE_NAME)
		if not os.path.isfile(path):
			self.importLegacySlots()
			return
		try:
			with open(path, "r", encoding="utf-8") as f:
				self.synths = {int(slot): settings for slot, settings in json.load(f).items()}
		except (OSError, ValueError):
			log.error("toggleX: could not read %s" % path, exc_info=True)

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
		path = self.getConfigPath(CONFIG_FILE_NAME)
		try:
			with open(path, "w", encoding="utf-8") as f:
				json.dump({str(slot): settings for slot, settings in self.synths.items()}, f, indent="\t")
		except OSError:
			log.error("toggleX: could not write %s" % path, exc_info=True)

	def setSynth(self, slot):
		self.slot = slot
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
		self.synths[self.slot] = settings
		self.write()
		# Translators: Announced when the current synthesizer is saved into the active slot.
		ui.message(_("Saved to slot {slot}").format(slot=self.slot))

	def onoff(self, value, msg=None):
		if msg:
			ui.message(msg)
		if value:
			tones.beep(700, 120)
		else:
			tones.beep(270, 80)

	def toggleBoolean(self, key):
		section, setting, label = BOOLEAN_SETTINGS[key]
		value = not config.conf[section][setting]
		config.conf[section][setting] = value
		self.onoff(value, label)

	def toggleMultiState(self, key):
		section, setting, flags, onValue, label = MULTI_STATE_SETTINGS[key]
		current = config.conf[section][setting]
		if current != flags.OFF.value:
			self.lastEnabledValue[key] = current
			config.conf[section][setting] = flags.OFF.value
			self.onoff(False, label)
			return
		value = self.lastEnabledValue.get(key, onValue.value)
		config.conf[section][setting] = value
		try:
			# Say which mode came back, since these settings have more than two states.
			label = "%s %s" % (label, flags(value).displayString)
		except ValueError:
			pass
		self.onoff(True, label)

	def toggleDictionaryProcessing(self):
		globalVars.speechDictionaryProcessing = not globalVars.speechDictionaryProcessing
		# Translators: Announced when toggling speech dictionary processing.
		self.onoff(globalVars.speechDictionaryProcessing, _("Dictionary"))

	def restoreTextProcessing(self):
		"""Puts NVDA's own processText back, if the z toggle replaced it. Returns whether it did."""
		if self.originalProcessText is None:
			return False
		if speech.speech.processText is passThroughText:
			speech.speech.processText = self.originalProcessText
		self.originalProcessText = None
		return True

	def toggleTextProcessing(self):
		# Translators: Announced when toggling all symbol, dictionary and normalization processing.
		label = _("Text processing")
		if self.restoreTextProcessing():
			self.onoff(True, label)
			return
		self.originalProcessText = speech.speech.processText
		speech.speech.processText = passThroughText
		self.onoff(False, label)

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
