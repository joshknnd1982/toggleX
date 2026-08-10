# Changelog

## 1.0

First release under new maintainership. Josh Kennedy has taken over toggleX from
its original authors, Tyler Spivey and Erion, whose last release was version
0.20121226.01.

This release brings the add-on up to date for **NVDA 2026.1**, which is an
API-compatibility-breaking release. toggleX 1.0 requires NVDA 2026.1 or later;
earlier versions of NVDA need toggleX 0.x.

### Fixed for NVDA 2026.1

- **The add-on now loads at all.** NVDA 2026.1 refuses add-ons whose
  `lastTestedNVDAVersion` is below 2026.1. The manifest now declares 2026.1 for
  both the minimum and last-tested versions.
- **Line indentation (`i`) no longer corrupts the setting.**
  `documentFormatting.reportLineIndentation` is a four-state integer in current
  NVDA (off, speech, tones, both), not a boolean. toggleX was writing a boolean
  over it. It now writes valid integers and remembers the mode you had chosen,
  restoring it when you switch the setting back on.
- **Table headers (`o`) no longer corrupts the setting.** Same problem and same
  fix: `documentFormatting.reportTableHeaders` is a four-state integer (off,
  rows and columns, rows, columns).
- **Removed `updateChannel` from the manifest**, which is not a field NVDA
  recognises.
- The replacement used by the "all text processing" toggle (`z`) now matches the
  signature of NVDA's current `speech.speech.processText`, including its
  `normalize` argument.

### Changed

- **Saved synthesizer slots have moved to JSON.** Slots now live in
  `toggleX.json` in your NVDA user configuration directory instead of a Python
  pickle. Existing slots are imported automatically the first time 1.0 runs; the
  old `switch_synth.pickle` is left in place and never read again.
- **Loading a slot applies the voice before rate, pitch and volume.** Changing a
  voice makes NVDA reload that voice's own settings, so the previous order meant
  a saved rate was silently discarded whenever the slot also changed voice.
- Loading a slot announces the synthesizer's display name ("Windows OneCore
  voices") rather than its internal module name ("oneCore"), and reports a
  failure instead of raising if the saved synthesizer can no longer be loaded.
- Saving a slot confirms which slot was written.
- Unsupported synthesizer settings are now detected with NVDA's `isSupported`
  API rather than by catching `NotImplementedError`.
- Messages are wrapped for translation, and the `NVDA+0` command now appears in
  NVDA's Input Gestures dialog under a *toggleX* category with a description.
- Both commands are marked to speak in NVDA's on-demand speech mode.
- The global plugin module was renamed from `globalPlugins/toggle.py` to
  `globalPlugins/toggleX.py`. All add-ons share the `globalPlugins` namespace,
  and `toggle` was generic enough to collide with another add-on.
- Failures reading or writing the slots file are logged instead of being raised
  into NVDA.

### Fixed

- The add-on no longer leaves NVDA's `processText` patched if it is unloaded
  while the `z` toggle is active.
- The wrapper that ends the toggleX layer now copies metadata from the script it
  wraps rather than from the cleanup function, so NVDA sees the correct script
  name and properties.

## 0.20121226.01 and earlier

Released by Tyler Spivey and Erion. See the first commit in this repository for
the code as it was distributed.
