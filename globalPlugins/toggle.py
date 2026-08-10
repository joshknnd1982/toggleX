from functools import wraps
import globalPluginHandler
import ui
import globalVars
import tones
import config
import pickle
import os
import speech
import synthDriverHandler

def finally_(func, final):
	"""Calls final after func, even if it fails."""
	def wrap(f):
		@wraps(f)
		def new(*args, **kwargs):
			try:
				func(*args, **kwargs)
			finally:
				final()
		return new
	return wrap(final)

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self, *args, **kwargs):
		super(GlobalPlugin, self).__init__(*args, **kwargs)
		self.synths = {}
		self.slot = 1
		self.toggling = False
		self.__toggle_gestures = {}
		for c in "tdhilcpuomr`1234567890-=akz":
			self.__toggle_gestures["KB:%s" % c] = "toggleX"
		self.load()
		self.processText = None

	def setSynth(self, gesture):
		self.slot = slot = int(gesture)
		if slot in self.synths:
			synthDriverHandler.setSynth(self.synths[slot]['name'])
			try:
				if 'rate' in self.synths[slot]:
					synthDriverHandler.getSynth().rate=self.synths[slot]['rate']
			except NotImplementedError:
				pass
			try:
				if 'voice' in self.synths[slot] and synthDriverHandler.getSynth().voice != self.synths[slot]['voice']:
					synthDriverHandler.changeVoice(synthDriverHandler.getSynth(), self.synths[slot]['voice'])
			except NotImplementedError:
					pass
			try:
				if 'variant' in self.synths[slot] and synthDriverHandler.getSynth().variant != self.synths[slot]['variant']:
					synthDriverHandler.getSynth().variant = self.synths[slot]['variant']
			except NotImplementedError:
				pass
			try:
				if 'volume' in self.synths[slot] and synthDriverHandler.getSynth().volume != self.synths[slot]['volume']:
					synthDriverHandler.getSynth().volume = self.synths[slot]['volume']
			except NotImplementedError:
				pass
			try:
				if 'pitch' in self.synths[slot] and synthDriverHandler.getSynth().pitch != self.synths[slot]['pitch']:
					synthDriverHandler.getSynth().pitch = self.synths[slot]['pitch']
			except NotImplementedError:
				pass
		if slot not in self.synths:
			ui.message("empty slot")
		else:
			ui.message(synthDriverHandler.getSynth().name)

	def saveSynth(self, gesture):
		if self.slot not in self.synths:
			self.synths[self.slot] = {}
		self.synths[self.slot]['name'] = synthDriverHandler.getSynth().name
		self.synths[self.slot]['voice'] = synthDriverHandler.getSynth().voice
		try:
			self.synths[self.slot]['variant'] = synthDriverHandler.getSynth().variant
		except NotImplementedError:
			pass
		self.synths[self.slot]['rate'] = synthDriverHandler.getSynth().rate
		self.synths[self.slot]['volume'] = synthDriverHandler.getSynth().volume
		try:
			self.synths[self.slot]['pitch'] = synthDriverHandler.getSynth().pitch
		except NotImplementedError:
			pass
		self.write()
		ui.message("save")

	def write(self):
		path = os.path.join(config.getUserDefaultConfigPath(), "switch_synth.pickle")
		with open(path, 'wb') as f:
			pickle.dump(self.synths, f)

	def load(self):
		path = os.path.join(config.getUserDefaultConfigPath(), "switch_synth.pickle")
		if not os.path.exists(path): return
		with open(path, 'rb') as f:
			self.synths = pickle.load(f)

	def onoff(self, value, msg=None):
		if msg:
			ui.message(msg)
		if value:
			tones.beep(700, 120)
		else:
			tones.beep(270, 80)

	def getScript(self, gesture):
		if not self.toggling:
			return globalPluginHandler.GlobalPlugin.getScript(self, gesture)
		script = globalPluginHandler.GlobalPlugin.getScript(self, gesture)
		if not script:
			script = finally_(self.script_error, self.finish)
		return finally_(script, self.finish)

	def finish(self):
		self.toggling = False
		self.clearGestureBindings()
		self.bindGestures(self.__gestures)

	def script_error(self, gesture):
		tones.beep(120, 100)

	def script_toggleX(self, gesture):
		char = gesture.identifiers[-1][-1]
		if char == 't':
			config.conf['documentFormatting']['reportTables'] = not config.conf['documentFormatting']['reportTables']
			self.onoff(config.conf['documentFormatting']['reportTables'], "Tables")
		elif char == 'd':
			globalVars.speechDictionaryProcessing = not globalVars.speechDictionaryProcessing
			self.onoff(globalVars.speechDictionaryProcessing, "Dictionary")
		elif char == 'h':
			config.conf['documentFormatting']['reportHeadings'] = not config.conf['documentFormatting']['reportHeadings']
			self.onoff(config.conf['documentFormatting']['reportHeadings'], "Headings")
		elif char == 'i':
			config.conf['documentFormatting']['reportLineIndentation'] = not config.conf['documentFormatting']['reportLineIndentation']
			self.onoff(config.conf['documentFormatting']['reportLineIndentation'], "Indentation")
		elif char == 'l':
			config.conf['documentFormatting']['reportLists'] = not config.conf['documentFormatting']['reportLists']
			self.onoff(config.conf['documentFormatting']['reportLists'], "Lists")
		elif char == 'c':
			config.conf['documentFormatting']['reportTableCellCoords'] = not config.conf['documentFormatting']['reportTableCellCoords']
			self.onoff(config.conf['documentFormatting']['reportTableCellCoords'], "Coords")
		elif char == 'p':
			config.conf['presentation']['reportObjectPositionInformation'] = not config.conf['presentation']['reportObjectPositionInformation']
			self.onoff(config.conf['presentation']['reportObjectPositionInformation'], "Position")
		elif char == 'u':
			config.conf['presentation']['reportKeyboardShortcuts'] = not config.conf['presentation']['reportKeyboardShortcuts']
			self.onoff(config.conf['presentation']['reportKeyboardShortcuts'], "Shortcuts")
		elif char == 'o':
			config.conf['documentFormatting']['reportTableHeaders'] = not config.conf['documentFormatting']['reportTableHeaders']
			self.onoff(config.conf['documentFormatting']['reportTableHeaders'], "Table headers")
		elif char == '1':
			self.setSynth(1)
		elif char == '2':
			self.setSynth(2)
		elif char == '3':
			self.setSynth(3)
		elif char == '4':
			self.setSynth(4)
		elif char == '5':
			self.setSynth(5)
		elif char == '6':
			self.setSynth(6)
		elif char == '7':
			self.setSynth(7)
		elif char == '8':
			self.setSynth(8)
		elif char == '9':
			self.setSynth(9)
		elif char == '0':
			self.setSynth(0)
		elif char == '-':
			self.setSynth(11)
		elif char == '=':
			self.setSynth(12)
		elif char == '`':
			self.setSynth(13)
		elif char == 'a':
			self.saveSynth("a")
		elif char == 'k':
			config.conf['documentFormatting']['reportLinks'] = not config.conf['documentFormatting']['reportLinks']
			self.onoff(config.conf['documentFormatting']['reportLinks'], "Links")
		elif char == 'm':
			config.conf['speech']['autoLanguageSwitching'] = not config.conf['speech']['autoLanguageSwitching']
			self.onoff(config.conf['speech']['autoLanguageSwitching'], "auto language")
		elif char == 'r':
			config.conf['speech']['trustVoiceLanguage'] = not config.conf['speech']['trustVoiceLanguage']
			self.onoff(config.conf['speech']['trustVoiceLanguage'], "trust")
		elif char == 'z':
			if self.processText:
				speech.speech.processText = self.processText
				self.processText = None
				self.onoff(True, "process")
			else:
				self.processText = speech.speech.processText
				speech.speech.processText = lambda locale,text,symbolLevel,normalize: text
				self.onoff(False, "process")

	def script_toggle(self, gesture):
		#If already toggling, send it on and clean up
		if self.toggling:
			gesture.send()
			return
		#alert the user of a gesture map error, rather than making the machine unusable
		try:
			self.bindGestures(self.__toggle_gestures)
		except:
			ui.message("Error binding toggle gestures")
			raise
		self.toggling = True
		tones.beep(100, 10)

	__gestures = {
	"KB:NVDA+0":"toggle",
}
