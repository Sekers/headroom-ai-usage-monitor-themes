"""Build the README's preview pages from the engine test's PNGs.

    python make_previews.py <PNG folder> <page folder>

Writes one HTML page per preview image (designs, states, and one per theme) to <page folder>;
screenshot.js then turns them into PNGs. The engine test must have run in both dark and light mode
first, so every PNG the pages use exists.
"""
import sys
from pathlib import Path

STYLE = (
    "body{margin:0;padding:16px 20px;background:#161b22;color:#c9d1d9;"
    "font-family:'Segoe UI',Arial,sans-serif;width:max-content}"
    "h1{font-size:15px;margin:2px 0 12px;font-weight:600} table{border-collapse:collapse}"
    "td{padding:5px 14px 5px 0;vertical-align:middle;font-size:12px;color:#8b949e;white-space:nowrap}"
    "th{font-size:12px;font-weight:600;text-align:left;padding:0 14px 4px 0;color:#c9d1d9}"
)
DESIGNS = [("headroom-lanes", "Headroom Lanes"), ("headroom-cells", "Headroom Cells"),
           ("headroom-cells-horizon", "Headroom Cells Horizon"), ("headroom-pills", "Headroom Pills")]
# (scenario from pack_tests.rs, row label, dark or light)
MIXES = [("c1x0", "1 Claude", "dark"), ("c1x1", "1 Claude + 1 Codex", "dark"),
         ("c2x1", "2 Claude + 1 Codex", "dark"), ("c1x2", "1 Claude + 2 Codex", "dark"),
         ("c0x3", "3 Codex", "dark"), ("c3x3", "3 Claude + 3 Codex", "dark"),
         ("default-names", "Accounts not renamed yet", "dark"),
         ("all-providers", "Claude + Codex + the other 5 providers", "dark"),
         ("providers-only", "Only Cursor, Grok and Copilot", "dark")]
STATES = [("weekly-high", "Weekly limits running high (PER 80%, WRK 100%)", "dark"),
          ("states", "PER out of date (faded), CDX has no 5-hour window", "dark"),
          ("reset", "WRK's 5-hour window just reset", "dark"),
          ("error-loading", "PER's refresh failed (!), CDX still loading (--)", "dark"),
          ("remaining", "Showing what's left (Remaining)", "dark"),
          ("c2x1", "Light taskbar", "light"),
          ("weekly-high", "Light taskbar, weekly limits running high", "light")]
PER_THEME = [("c1x0", "1 Claude account", "dark"), ("c1x1", "1 Claude + 1 Codex", "dark"),
             ("c2x1", "2 Claude + 1 Codex", "dark"),
             ("c1x2", "1 Claude + 2 Codex", "dark"), ("c3x3", "3 Claude + 3 Codex", "dark"),
             ("all-providers", "Claude + Codex + 5 other providers", "dark"),
             ("weekly-high", "Weekly limits running high", "dark"), ("c2x1", "Light taskbar", "light")]


def image(pngs, design, scenario, hover, mode):
    suffix = "-hover" if hover else ""
    path = (pngs / f"{design}__{scenario}{suffix}__{mode}.png").resolve()
    return f'<td><img src="{path.as_uri()}" style="height:40px"></td>'


def page(title, header, rows):
    return f"<!doctype html><meta charset=utf-8><style>{STYLE}</style><h1>{title}</h1><table>{header}{''.join(rows)}</table>"


def sheet(pngs, title, rows):
    header = "<tr><th></th>" + "".join(f"<th colspan=2>{name}</th>" for _, name in DESIGNS) + "</tr>"
    header += "<tr><td></td>" + "<td>normal</td><td>on hover</td>" * len(DESIGNS) + "</tr>"
    body = [f"<tr><td>{label}</td>" + "".join(image(pngs, d, key, h, mode) for d, _ in DESIGNS for h in (False, True))
            + "</tr>" for key, label, mode in rows]
    return page(title, header, body)


def main(pngs, out):
    out.mkdir(parents=True, exist_ok=True)
    pages = {"designs": sheet(pngs, "Headroom: one theme per design, sized to what you use", MIXES),
             "states": sheet(pngs, "States, shown for 2 Claude + 1 Codex", STATES)}
    for design, name in DESIGNS:
        header = "<tr><th></th><th>normal</th><th>on hover</th></tr>"
        rows = [f"<tr><td>{label}</td>{image(pngs, design, key, False, mode)}{image(pngs, design, key, True, mode)}</tr>"
                for key, label, mode in PER_THEME]
        pages[design.removeprefix("headroom-")] = page(name, header, rows)
    for name, html in pages.items():
        (out / f"{name}.html").write_text(html, encoding="utf-8")
        print(out / f"{name}.html")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
