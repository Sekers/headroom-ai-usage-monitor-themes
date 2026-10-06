# Headroom: usage themes for Claude Code Usage Monitor

Headroom is a set of compact taskbar themes for [Claude Code Usage Monitor](https://github.com/CodeZeno/Claude-Code-Usage-Monitor),
the Windows taskbar widget by CodeZeno. They show how much headroom you have left on your AI usage
limits: every Claude and Codex account you've set up, plus Antigravity, OpenCode, Cursor, Grok and
Copilot if you've turned them on in the monitor. Each one gets a slot, and each theme sizes itself to
the slots you use, so there's nothing to pick per setup.

![All four themes with different mixes of accounts and providers](previews/designs.png)

The previews are rendered by the monitor's own theme engine with sample data and a stand-in font; on
Windows the themes use Segoe UI.

## The themes

| Theme | Download | Width for 1, 2, 3 slots | Shows up to | Best for |
| --- | --- | --- | --- | --- |
| [Headroom Lanes](#headroom-lanes) | [headroom-lanes.json](themes/headroom-lanes.json) | 145 px for any number | 3 slots | Reading exact numbers at a glance |
| [Headroom Cells](#headroom-cells) | [headroom-cells.json](themes/headroom-cells.json) | 30, 62, 94 px | 6 slots | The smallest footprint |
| [Headroom Cells Horizon](#headroom-cells-horizon) | [headroom-cells-horizon.json](themes/headroom-cells-horizon.json) | 30, 62, 94 px | 6 slots | Cells, with both limits a hover away |
| [Headroom Pills](#headroom-pills) | [headroom-pills.json](themes/headroom-pills.json) | 60, 123, 186 px | 6 slots | The largest, easiest-to-read numbers |

Every slot has a main limit and, for most providers, a second one. For Claude and Codex they're the
5-hour and weekly windows; the other providers' limits are listed under
[Other providers](#other-providers).

### Headroom Lanes

![Headroom Lanes](previews/lanes.png)

* **Each slot** is a row: the name, a bar for the main limit over a thin line for the second, and the
  percentage with the time to reset.
* **On hover** each row switches to the second limit: its bar, percentage and time to reset, dimmed
  unless it's running high.
* **Size:** 145 px wide whatever it shows, with up to 3 rows.
* **File:** [themes/headroom-lanes.json](themes/headroom-lanes.json)

### Headroom Cells

![Headroom Cells](previews/cells.png)

* **Each slot** is a vertical gauge for the main limit with a thin sliver for the second, and the
  name underneath.
* **On hover** each cell shows the main limit's percentage and time to reset.
* **Size:** 30 px for one slot and 32 px more for each extra one, up to 6.
* **File:** [themes/headroom-cells.json](themes/headroom-cells.json)

### Headroom Cells Horizon

![Headroom Cells Horizon](previews/cells-horizon.png)

* **Each slot** looks just like Cells.
* **On hover** each cell shows the main limit's percentage and time to reset, with the second limit's
  percentage under them, in gray unless it's running high. Its time to reset is the one number left
  out; Lanes and Pills show it.
* **Size:** the same as Cells.
* **File:** [themes/headroom-cells-horizon.json](themes/headroom-cells-horizon.json)

### Headroom Pills

![Headroom Pills](previews/pills.png)

* **Each slot** is a card: the name and time to reset, a large percentage, a bar for the main limit
  and a thin line for the second.
* **On hover** each card switches to the second limit, dimmed unless it's running high.
* **Size:** 60 px per card with 3 px between them, up to 6.
* **File:** [themes/headroom-pills.json](themes/headroom-pills.json)

## Install

1. Install Claude Code Usage Monitor (`winget install CodeZeno.ClaudeCodeUsageMonitor`), version
   2.11.28 or later for multiple accounts. The themes were built and tested against 2.18.1.
2. Download a theme from [The themes](#the-themes): open its file and click **Download raw file**.
3. Open the monitor's dashboard, go to **Theme Studio**, click **Import...** and choose the file.
4. Select it under **Settings > Appearance > Active theme** if it isn't already active.

## What shows

Each account or provider you use gets one slot, in this order:

| Provider | Slots | Why |
| --- | --- | --- |
| Claude | 1 per account, up to 5 | The monitor supports several Claude accounts; the themes look for the first 5. |
| Codex | 1 per account, up to 5 | The same as Claude. |
| Antigravity, OpenCode, Cursor, Grok, Copilot | 1 each | The monitor supports one account for each of these. |

* **How many show at once:** Lanes shows the first 3 slots and the other themes the first 6, counting
  in the order above. With only two providers turned on, say Cursor and Copilot, you get exactly two
  slots.
* **Order:** Claude accounts first, then Codex accounts, each in the order you added them, then the
  other providers.
* **Anything turned off** under **Settings > Providers** doesn't show and takes no space. The widget
  resizes itself when you add or remove an account or turn a provider on or off.
* **Claude is on by default** in the monitor. If you don't use it, turn it off; otherwise its unused
  account still gets a slot, showing `CLD` and `!`.
* **At startup** each Claude or Codex account appears once its first refresh finishes; until then the
  widget shows `--`.

### Account names

* **Short names work best.** Each Claude and Codex account is labeled with its name, so rename them
  to three or four characters, such as `PER`, `WRK` or `CDX`, under **Settings > Providers >
  Accounts**. Longer names are cut off.
* **Accounts you haven't renamed** keep the names the monitor gave them, "Default" and "Account 1",
  "Account 2" and so on. Those show as `CLD` or `CDX` for a provider's first account and with the
  account's number after that, such as `CLD2` or `CDX3`.
* **The Default account dropdown** doesn't change what these themes show; it still picks the account
  behind the tray icons.
* **Account IDs.** The monitor gives each account a fixed ID: a provider's first account is `default`,
  accounts you add are `account_1`, `account_2` and so on, and an ID is never reused. The themes look
  for `default` through `account_4` for each provider, which is where the limit of 5 comes from. If you've removed and added accounts often
  enough to reach `account_5`, add more IDs to `ACCOUNT_IDS` in the generator (see
  [Make your own](#make-your-own)).

To keep several Claude logins signed in at once, give each its own configuration directory (Claude
Code's `CLAUDE_CONFIG_DIR`) and point the account's **Config directory** at it.

### Other providers

Antigravity, OpenCode, Cursor, Grok and Copilot have a single account and no name, so each gets a
fixed label and color. Their limits aren't all 5-hour and weekly windows:

| Provider | Label | Main limit | Second limit |
| --- | --- | --- | --- |
| Antigravity | `AGY` | session quota | weekly quota, when reported |
| OpenCode | `OPC` | rolling window | longer window (weekly or 30 days) |
| Cursor | `CUR` | included plan usage | API usage (same billing cycle) |
| Grok | `GRK` | usage pool (weekly or 30 days) | none |
| Copilot | `CPL` | premium requests this month | none |

Grok and Copilot have no second limit, so hovering shows their one limit again. A provider that's
turned on but not installed or signed in shows `!`.

## Reading the widget

* **Colors.** Each slot keeps its own color wherever it sits. By account ID, Claude accounts are
  coral, lavender, mint, rose and olive; Codex accounts are blue, teal, indigo, steel and violet. The
  other providers are green (Antigravity), magenta (OpenCode), silver (Cursor), tan (Grok) and pink
  (Copilot).
* **Warnings.** Both limits warn the same way: a bar, line or figure turns amber at 75% used and red
  at 90%. The thin line stays quiet until then, so a weekly limit that's running out stands out even
  while you're watching the 5-hour bar.
* **After a reset.** Once a limit's reset time passes, it shows `0%` and `reset` right away instead of
  the old figure, until the monitor's next refresh brings the new reading.
* **Faded figures** are left over from an earlier refresh because the latest one failed, often an
  HTTP 429 from Anthropic's usage endpoint. If that happens a lot, raise **Update frequency** under
  **Settings > General** (the default is 15 minutes).
* **`!`** means the last refresh failed with nothing to fall back on; hover the tray icon for the
  reason. **`--`** means it's still loading. **`n/a`** means the plan has no such limit.
* **Used or remaining.** **Settings > Display > Usage direction** switches between showing what
  you've used and what's left.
* Light and dark taskbars both have their own colors.

![Every state, shown for 2 Claude + 1 Codex](previews/states.png)

## Make your own

The themes come from [generator/build.py](generator/build.py). Edit `ACCOUNT_IDS`, the colors, the
other providers' limits or the warning thresholds near the top, or a theme's maximum number of slots in
`DESIGNS`, then run it with Python 3:

```
python generator/build.py
```

It writes the four themes to `themes/`. To check them with the monitor's own engine and redraw the
previews, see [generator/engine-test](generator/engine-test/README.md).

## Credits and license

MIT; see [LICENSE](LICENSE). The tray icons come from Claude Code Usage Monitor's built-in Compact
Fluent Quad theme (MIT, Code Zeno Pty Ltd); see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

This project isn't affiliated with or endorsed by CodeZeno or any of the AI providers it shows.
Product names are trademarks of their owners.
