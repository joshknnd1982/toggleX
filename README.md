# toggleX — Settings Toggler, with Xtra features

An [NVDA](https://www.nvaccess.org/) add-on that turns settings you change often
into two keystrokes, and lets you switch between saved synthesizer
configurations instantly.

Press `NVDA+0` to start the toggleX layer, then press one more key. Each toggle
is confirmed by name, followed by a high beep for on or a low beep for off.

**Requires NVDA 2026.1 or later.**

## Install

Download `toggleX-1.0.nvda-addon` from the
[releases page](https://github.com/joshknnd1982/toggleX/releases) and open it,
or install it from NVDA's Add-on Store via *Install from external source*.

## Commands

All of these are pressed after `NVDA+0`. The layer lasts for exactly one
keystroke — an unused key plays an error beep and leaves the layer, and pressing
`NVDA+0` again leaves the layer and passes the keystroke through.

| Key | Toggles |
| --- | --- |
| `t` | Tables |
| `c` | Table cell coordinates |
| `o` | Table headers |
| `h` | Headings |
| `l` | Lists |
| `k` | Links |
| `i` | Line indentation |
| `p` | Object position information |
| `u` | Keyboard shortcuts |
| `m` | Automatic language switching |
| `r` | Trust the voice's language when processing characters and symbols |
| `d` | Speech dictionary processing |
| `z` | All text processing — symbols, dictionaries and Unicode normalization |

| Key | Synthesizer slot |
| --- | --- |
| `1`–`9` | Load slots 1 to 9 |
| `0` | Load slot 0 |
| `-` | Load slot 11 |
| `=` | Load slot 12 |
| `` ` `` | Load slot 13 |
| `a` | Save the current synthesizer into the active slot |

A slot records the synthesizer along with its voice, variant, rate, pitch and
volume — whichever of those the synthesizer supports. Full usage notes are in
[the add-on documentation](addon/doc/en/readme.html), which NVDA also opens from
*Tools > Add-on Store*.

## Building

No third-party dependencies; any Python 3 will do.

```bash
python build.py
```

This writes `toggleX-1.0.nvda-addon` (a zip of `addon/`) to the repository root.
The version in the file name comes from `addon/manifest.ini`.

## Layout

| Path | Contents |
| --- | --- |
| `addon/manifest.ini` | Add-on metadata NVDA reads at load time |
| `addon/globalPlugins/toggleX.py` | The entire add-on |
| `addon/doc/en/readme.html` | User documentation shipped inside the add-on |
| `build.py` | Packages `addon/` into a `.nvda-addon` bundle |

## History and authorship

toggleX was originally written by **Tyler Spivey** (tspivey@pcdesk.net) and
**Erion**. The last release under the original authors was version
0.20121226.01, which targeted NVDA 2019.2 and was last tested against 2024.1.

**Josh Kennedy** (joshknnd1982@gmail.com) took over maintenance in 2026 and
released version 1.0, which brings the add-on up to date for NVDA 2026.1. The
original code is preserved unmodified as the first commit in this repository.

See [CHANGELOG.md](CHANGELOG.md) for what changed.

## License

toggleX is released under the [GNU General Public License version 2](LICENSE),
the licence NVDA itself uses and the convention for NVDA add-ons. The original
release carried no explicit licence statement; GPL v2 was applied when the
add-on moved to this repository.

