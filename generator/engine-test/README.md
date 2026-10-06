# Engine test

Checks the themes with Claude Code Usage Monitor's own code rather than a lookalike: it loads each
theme through the monitor's theme loader, which also validates it, and renders it with the monitor's
engine at five display scales (100% to 200%), normal and hovered, for many account and provider
mixes. It fails on any load, validation or render problem, and checks the widget's width for every
mix. It also saves PNGs, which `make_previews.py` and `screenshot.js` turn into the README's previews.

| File | What it is |
| --- | --- |
| `pack_tests.rs` | The test, added to a checkout of the monitor. |
| `make_previews.py` | Builds the preview pages from the test's PNGs. |
| `screenshot.js` | Turns those pages into the PNGs in `previews/`. |
| `wine/` | What it takes to run the test on Linux, under Wine. |

The mixes cover 1 to 7 Claude and Codex accounts in every combination, account IDs with gaps,
accounts with the names the monitor gave them, every other provider on, providers without Claude,
and a provider with no reading yet. Each also renders with a stale reading, a passed reset, a failed
refresh, loading, a plan without a 5-hour window, weekly limits running high, Remaining mode, and
four-letter names at 100%.

## Run it on Windows

1. Clone [Claude Code Usage Monitor](https://github.com/CodeZeno/Claude-Code-Usage-Monitor) and check
   out the version to test against (the themes were last tested with `v2.18.1`). Set it up to build
   as its `CONTRIBUTING.md` describes.
2. Copy `pack_tests.rs` into the checkout as `src/theme_engine/pack_tests.rs`, and add these two
   lines at the end of `src/theme_engine.rs`:

   ```rust
   #[cfg(test)]
   mod pack_tests;
   ```

3. From the checkout, with `THEME_PACK_DIR` pointing at this repo's `themes` folder:

   ```powershell
   $env:THEME_PACK_DIR = "C:\path\to\headroom-ai-usage-monitor-themes\themes"
   $env:THEME_PACK_OUT = "C:\path\to\renders"
   cargo test theme_pack_validates -- --nocapture
   ```

   It prints how many themes and renders it checked and any problems. The test reads Windows'
   light or dark setting, so to get both sets of PNGs, run it once in each.
4. To redraw the README's previews from those PNGs (needs Python 3.9 or later, and Playwright for
   Node: `npm install playwright`, then `npx playwright install chromium`):

   ```powershell
   python generator\engine-test\make_previews.py C:\path\to\renders C:\path\to\pages
   node generator\engine-test\screenshot.js C:\path\to\pages previews
   ```

Keep the changes in the monitor's checkout local; they're for this test only.

`pack_tests.rs` also has `theme_render_timing`, which prints the average render time of every theme
in `THEME_TIMING_DIR`. Put other themes there, such as the monitor's own `src/themes/`, to compare.

## Run it on Linux, under Wine

The same test, cross-compiled for Windows and run under Wine 9. Text renders in a stand-in font,
since Wine has no Segoe UI. It's usually a little wider, so text that fits under Wine fits on
Windows too.

1. Install mingw-w64, Wine and Rust's `x86_64-pc-windows-gnu` target, then run `wine/setup.sh`. It
   links mingw-w64's libraries under the names the monitor's dependencies ask for, and builds a
   stand-in `winsqlite3.dll`, which Windows has and Wine doesn't.
2. Do step 2 above. Wine 9 also lacks `SystemTimeToTzSpecificLocalTimeEx`, so in
   `src/theme_engine/theme_datetime.rs` change that call to `SystemTimeToTzSpecificLocalTime`, which
   takes the same arguments.
3. Build with the line `setup.sh` prints, copy its `winsqlite3.dll` next to the test executable,
   then run that executable under Wine with the same two variables, `THEME_PACK_DIR` and
   `THEME_PACK_OUT` (as Windows paths, such as `Z:\home\you\...`) and the argument
   `theme_pack_validates`. For the light-mode PNGs, set Wine's
   `HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize\SystemUsesLightTheme` to 1
   and run it again.
