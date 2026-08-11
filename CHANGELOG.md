# Changelog

## 1.2

### Changed

- The add-on is now listed as **ToggleX** in NVDA's Add-on Store and Add-ons
  Manager, rather than "Settings Toggler, with Xtra features".

### Fixed

- **Saved synthesizer slots no longer go missing.** toggleX was asking NVDA where
  an *installed* copy would keep its configuration rather than where the running
  copy actually keeps it. On a portable copy, or with NVDA started using
  `--config-path`, `toggleX.json` was read and written somewhere else entirely —
  for a portable copy, a path relative to whatever directory NVDA happened to be
  sitting in at the time. Slots saved in one moment reported "Empty slot" in the
  next. toggleX now uses the configuration directory NVDA is really using, which
  is the one NVDA writes `nvda.ini` to.

- **A failed save no longer destroys the slots you already had.** The slots file
  was emptied before the new contents had been worked out, so a synthesizer
  handing back a setting that could not be stored left a half-written file
  behind, and every saved slot with it. toggleX now prepares the whole file
  first and puts it into place in one step, leaving the previous slots untouched
  if anything goes wrong.

- **A save that does not reach the disk now says so** instead of announcing
  "Saved to slot" and losing the slot at the next restart.

- **A slots file that cannot be read is kept rather than written over.** It is
  renamed to `toggleX.json.bad` and the reason is logged, so the slots in it can
  still be recovered.

## 1.1

### Fixed

- **toggleX settings are now saved with the rest of your NVDA configuration.**
  Pressing `NVDA+control+c` saves them, and they come back the next time NVDA
  starts.

  The settings toggleX shares with NVDA — tables, headings, lists, links, cell
  coordinates, position, shortcuts, language switching and the rest — were
  already being saved, because they live in NVDA's own configuration. Three
  things were not, because NVDA has nowhere to keep them:

  - **Speech dictionary processing (`d`)** is a plain variable inside NVDA that
    resets to on every time NVDA starts.
  - **All text processing (`z`)** works by replacing one of NVDA's functions for
    the lifetime of the session, which nothing persists.
  - **Which synthesizer slot is active**, which decides where `a` saves.

  toggleX now keeps these in its own section of NVDA's configuration, so NVDA
  saves and restores them like everything else. They also follow NVDA's
  configuration profiles: switching to a profile with its own toggleX settings
  applies them immediately.

- **Loading a synthesizer slot now sticks.** Applying a slot only changed the
  running synthesizer; the configuration still held the settings the
  synthesizer had been loaded with. Saving your configuration therefore wrote
  those older settings back, and the next NVDA session started with the right
  synthesizer but the wrong voice, rate, pitch and volume. toggleX now writes a
  loaded slot into the configuration, the same way NVDA does when you change a
  synthesizer setting yourself.

- The mode remembered for line indentation (`i`) and table headers (`o`) is
  saved too, so switching one back on after a restart returns to the mode you
  had chosen rather than the default.

### Changed

- Unloading the add-on no longer counts as switching text processing back on;
  it restores NVDA's function without changing what you had saved.

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
