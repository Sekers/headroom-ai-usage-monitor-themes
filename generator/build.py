"""Generate the Headroom themes: one self-adjusting theme per design.

Run from anywhere: `python generator/build.py`. Output goes to `themes/<id>.json`.

How a theme finds your accounts
-------------------------------
CodeZeno exposes each Claude and Codex account by provider and account ID. A provider's first
account has the ID `default`; accounts you add get `account_1`, `account_2` and so on, in the
order you add them, and an ID is never reused. Every enabled account has a name (CodeZeno fills
in the ID if you clear it), so an account exists when its name isn't empty.

Each theme has a slot for every ID in ACCOUNT_IDS, for Claude and then Codex, and then one slot
for each of CodeZeno's other providers (OTHER_PROVIDERS), which have a single account and no name.
A slot shows when its account exists (or its provider is turned on) and fewer than the design's
`max` slots come before it. The slots sit in a row (a column for Lanes) that skips hidden slots,
and the widget's width follows the number of slots shown.

Every slot has a main limit (the big bar) and maybe a second one (the thin line). For Claude and
Codex they are the 5-hour and weekly windows; the other providers report different limits, listed
in OTHER_PROVIDERS. Hovering swaps the two, or shows the main limit's numbers if there's no second.
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_THEME = ROOT / "generator" / "vendor" / "compact-fluent-quad.json"

PROVIDER_NAMES = {"claude": "Claude", "codex": "Codex"}
# Shown instead of an account's name while it still has the name CodeZeno gave it: "Default" for a
# provider's first account and "Account 1", "Account 2"... for added ones (or the account ID, if the
# name was cleared). The first account gets the code alone, later ones the code and their number.
SHORT_NAMES = {"claude": "CLD", "codex": "CDX"}
# Raise this list if you add and remove accounts often: an account outside it never shows.
ACCOUNT_IDS = ["default", "account_1", "account_2", "account_3", "account_4"]

# Account colors by account ID, in ACCOUNT_IDS order: (bar fill, text on dark, text on light).
ACCOUNT_COLORS = {
    "claude": [("#D97757FF", "#F09A7AFF", "#A94F32FF"),   # coral
               ("#B48AF0FF", "#D4B5FAFF", "#6D3FB8FF"),   # lavender
               ("#4FBF9FFF", "#8EDDC4FF", "#1E7A60FF"),   # mint
               ("#E57AA5FF", "#F5A9C7FF", "#A8366AFF"),   # rose
               ("#9DBB4AFF", "#C3DC84FF", "#56701EFF")],  # olive
    "codex": [("#3B82F6FF", "#93C5FDFF", "#1D4ED8FF"),    # blue
              ("#22B8CFFF", "#8AE0EEFF", "#0E7490FF"),    # teal
              ("#8B93F8FF", "#C3C8FDFF", "#4338CAFF"),    # indigo
              ("#7FA2CCFF", "#B8CDE8FF", "#3D5F8AFF"),    # steel
              ("#C084FCFF", "#DDB8FEFF", "#7E22CEFF")],   # violet
}
# CodeZeno's other providers, in its order: key, label, colors as above, and which of the
# provider's windows is its main limit and which its second (None if it reports only one).
OTHER_PROVIDERS = [
    ("antigravity", "Antigravity", "AGY", ("#5DB86AFF", "#93D69CFF", "#2E7D3AFF"), "five_hour", "weekly"),  # green
    ("opencode", "OpenCode", "OPC", ("#D46BCCFF", "#EBA6E5FF", "#97308FFF"), "five_hour", "weekly"),  # magenta
    # Cursor: the plan's included usage, then API usage, over the same billing cycle.
    ("cursor", "Cursor", "CUR", ("#AEB6C2FF", "#D3D8DFFF", "#525B68FF"), "five_hour", "weekly"),  # silver
    # Grok and Copilot report one pool (weekly or 30 days) in the weekly slot.
    ("grok", "Grok", "GRK", ("#C29A6EFF", "#DEC3A2FF", "#77583AFF"), "weekly", None),  # tan
    ("copilot", "Copilot", "CPL", ("#EF7FB1FF", "#F7B3D1FF", "#B0386EFF"), "weekly", None),  # pink
]
WARN = {"amber": ("#F5A524FF", "#F7B955FF", "#B45309FF"), "red": ("#F2555AFF", "#FF6B6BFF", "#C62828FF")}
NEUTRAL = {"dark": {"dim": "#A3A3A3FF", "track": "#3A3A3AFF", "strong": "#EEEEEEFF"},
           "light": {"dim": "#5F5F5FFF", "track": "#D0D0D0FF", "strong": "#222222FF"}}
THEMES = (("dark", "system.dark"), ("light", "1 - system.dark"))
AMBER_AT, RED_AT = 75, 90
STALE_TEXT, STALE_BAR = "0.5", "0.4"


# ---------------------------------------------------------------- slots and expressions

def all_slots():
    """Every slot a theme has: Claude and Codex accounts in the order they were added, then the
    other providers."""
    slots = []
    for provider in ("claude", "codex"):
        for index, account_id in enumerate(ACCOUNT_IDS):
            key = f"accounts.{provider}.{account_id}"
            fill, dark, light = ACCOUNT_COLORS[provider][index]
            given = "Default" if index == 0 else f"Account {index}"
            unnamed = f'(({key}.name == "{given}") || ({key}.name == "{account_id}"))'
            short = SHORT_NAMES[provider] + ("" if index == 0 else str(index + 1))
            slots.append({"provider": provider, "key": key, "label": f"{{{key}.name}}",
                          "unnamed": unnamed, "short": short,
                          "slug": f"{provider[:2]}{index}",
                          "title": f"{PROVIDER_NAMES[provider]} {account_id}",
                          "present": f'({key}.name != "")', "exists": None,
                          "main": "five_hour", "second": "weekly",
                          "fill": fill, "text": {"dark": dark, "light": light}})
    for provider, title, short, (fill, dark, light), main, second in OTHER_PROVIDERS:
        slots.append({"provider": provider, "key": provider, "label": short, "unnamed": "(0)", "short": short,
                      "slug": provider[:3], "title": title,
                      "present": f"(providers.{provider}.enabled != 0)", "exists": None,
                      "main": main, "second": second,
                      "fill": fill, "text": {"dark": dark, "light": light}})
    return slots


def windows(slot, view):
    """(primary, secondary) windows for a view: "near" shows the main limit over the second, "far"
    swaps them, or keeps the main limit alone when there's no second."""
    main, second = slot["main"], slot["second"]
    if view == "near":
        return main, second
    return (second, main) if second else (main, None)


def expired(key, window):
    """The window's reset time has passed but the next refresh hasn't arrived yet."""
    return f"(({key}.{window}.reset.unix > 0) && ({key}.{window}.reset.seconds <= 0))"


def missing(key, window):
    """The account reported usage, but not for this window (some plans have no 5-hour limit)."""
    return f"(({key}.available != 0) && ({key}.{window}.available == 0))"


def eff_pct(key, window):
    return f"if({expired(key, window)}, 0, {key}.{window}.percentage)"


def eff_disp(key, window):
    return f"if({expired(key, window)}, if(display.countdown, 100, 0), {key}.{window}.display)"


def faded(key, normal="1", stale=STALE_TEXT):
    """Opacity that fades readings carried over from an earlier refresh."""
    return f"if({key}.stale, {stale}, {normal})"


def warn_states(pct):
    return ((f"({pct} < {AMBER_AT})", None),
            (f"({pct} >= {AMBER_AT}) && ({pct} < {RED_AT})", "amber"),
            (f"({pct} >= {RED_AT})", "red"))


# ---------------------------------------------------------------- scene objects

def num(value):
    """A coordinate: a number, or an expression string passed through."""
    return value if isinstance(value, str) else f"{value:g}"


def layer(id_, name, parent, x, y, w, h, content=None, render="1"):
    return {"id": id_, "name": name, "render": render, "visibility": "100", "parent": parent,
            "x": num(x), "y": num(y), "width": num(w), "height": num(h),
            "background": {"type": "none"}, "border": None, "corner_radius": "0",
            "layout": "freeform", "align": "start", "gap": "0", "content": content or {"type": "none"}}


def text(template, color, size, weight="medium", align="left", opacity="1"):
    return {"type": "text", "template": template, "font_family": "Segoe UI", "font_size": f"{size:g}",
            "weight": weight, "rendering": "clear_type", "contrast": "1", "align": align,
            "color": {"color": color, "opacity": opacity}}


def progress(value, fill, radius, direction="left_to_right", opacity="1"):
    return {"type": "progress", "value": value, "direction": direction,
            "fill": {"color": fill, "opacity": opacity}, "track": {"color": "#00000000", "opacity": "1"},
            "corner_radius": f"{radius:g}", "segments": 0, "segment_gap": "0"}


def shape(id_, name, parent, x, y, w, h, color, radius, render, border=None):
    obj = layer(id_, name, parent, x, y, w, h, render=render)
    # CodeZeno's theme format spells these two keys "colour".
    obj["background"] = {"type": "colour", "colour": {"color": color, "opacity": "1"}}
    obj["corner_radius"] = f"{radius:g}"
    if border:
        obj["border"] = {"color": {"color": border, "opacity": "1"}, "width": "1"}
    return obj


def tracks(base, name, parent, x, y, w, h, radius):
    return [shape(f"{base}-track-{theme}", f"{theme} {name} track", parent, x, y, w, h,
                  NEUTRAL[theme]["track"], radius, cond) for theme, cond in THEMES]


def bar(base, name, parent, x, y, w, h, slot, window, radius, direction="left_to_right", warn=True,
        opacity="1"):
    """A bar for one window. With `warn`, it turns amber and red; it fades when stale.

    `opacity` applies while the window is below the warning threshold; a warning always shows at full
    strength, so a quiet secondary line still stands out once it matters.
    """
    key, value, pct = slot["key"], eff_disp(slot["key"], window), eff_pct(slot["key"], window)
    if not warn:
        return [layer(f"{base}-fill", f"{name} fill", parent, x, y, w, h,
                      progress(value, slot["fill"], radius, direction, faded(key, opacity, STALE_BAR)))]
    out = []
    for render, level in warn_states(pct):
        color = WARN[level][0] if level else slot["fill"]
        strength = opacity if level is None else "1"
        out.append(layer(f"{base}-fill-{level or 'ok'}", f"{name} fill ({level or 'normal'})", parent,
                         x, y, w, h, progress(value, color, radius, direction, faded(key, strength, STALE_BAR)),
                         render))
    return out


def readout(base, name, parent, x, y, w, h, slot, window, template, size, weight="medium", align="left",
            tone="account", after_reset=("0% · reset", "100% · reset"), not_available="n/a"):
    """The text for one window: live value, a reset placeholder, or "n/a" when the plan lacks
    the window.

    `tone` is "account" (account color), "strong" (bright neutral) or "quiet" (dim neutral); each
    turns amber and red when the window runs high.
    """
    key = slot["key"]
    gone, absent, pct = expired(key, window), missing(key, window), eff_pct(key, window)
    out = []
    for theme, cond in THEMES:
        cond = f"({cond})"
        base_color = {"account": slot["text"][theme], "strong": NEUTRAL[theme]["strong"],
                       "quiet": NEUTRAL[theme]["dim"]}[tone]
        for render, level in warn_states(pct):
            color = WARN[level][1 if theme == "dark" else 2] if level else base_color
            out.append(layer(f"{base}-{level or 'ok'}-{theme}", f"{theme} {name} ({level or 'normal'})", parent,
                             x, y, w, h, text(template, color, size, weight, align, faded(key)),
                             f"{cond} && {render} && !{gone} && !{absent}"))
        used, left = after_reset
        out.append(layer(f"{base}-reset-used-{theme}", f"{theme} {name} after reset (used)", parent, x, y, w, h,
                         text(used, base_color, size, weight, align, faded(key)),
                         f"{cond} && {gone} && !display.countdown"))
        out.append(layer(f"{base}-reset-left-{theme}", f"{theme} {name} after reset (remaining)", parent,
                         x, y, w, h, text(left, base_color, size, weight, align, faded(key)),
                         f"{cond} && {gone} && display.countdown"))
        out.append(layer(f"{base}-na-{theme}", f"{theme} {name} not on this plan", parent, x, y, w, h,
                         text(not_available, NEUTRAL[theme]["dim"], size, weight, align), f"{cond} && {absent}"))
    return out


def labels(base, name, parent, x, y, w, h, slot, size, align):
    """The account's name in its color, or its short label while it has CodeZeno's default name."""
    out = []
    for theme, cond in THEMES:
        out.append(layer(f"{base}-{theme}", f"{theme} {name}", parent, x, y, w, h,
                         text(slot["label"], slot["text"][theme], size, "bold", align),
                         f"({cond}) && !{slot['unnamed']}"))
        out.append(layer(f"{base}-short-{theme}", f"{theme} {name} (default name)", parent, x, y, w, h,
                         text(slot["short"], slot["text"][theme], size, "bold", align),
                         f"({cond}) && {slot['unnamed']}"))
    return out


def reset_time(base, name, parent, x, y, w, h, slot, window, size, align):
    """Time to the window's reset, or "reset" once it has passed."""
    key, out = slot["key"], []
    for theme, cond in THEMES:
        out.append(layer(f"{base}-{theme}", f"{theme} {name}", parent, x, y, w, h,
                         text(f"{{{key}.{window}.reset.seconds:duration_short}}", NEUTRAL[theme]["dim"],
                              size, "regular", align, faded(key)),
                         f"({cond}) && ({key}.{window}.reset.seconds > 0)"))
        out.append(layer(f"{base}-done-{theme}", f"{theme} {name} (reset passed)", parent, x, y, w, h,
                         text("reset", NEUTRAL[theme]["dim"], size, "regular", align),
                         f"({cond}) && {expired(key, window)}"))
    return out


# ---------------------------------------------------------------- designs
#
# Each design draws one account inside a slot group of `slot` size, in the group's own
# coordinates. A group clips what it draws to its box, so everything stays inside it.

def lanes_slot(mode):
    """A row: label, thick bar over a hairline for the other limit, value. Hover: the second limit."""
    view = "near" if mode == "5h" else "far"
    thick_y, thin_y = (2, 9) if mode == "5h" else (6, 2)
    label_w, bar_x, bar_w, text_x, width, row_h = 30, 34, 42, 80, 145, 13

    def build(slot, g):
        primary, secondary = windows(slot, view)
        out = labels(f"{g}-label", "label", g, 0, 0, label_w, row_h, slot, 9, "right")
        out += tracks(f"{g}-thick", primary, g, bar_x, thick_y, bar_w, 5, 2.5)
        out += bar(f"{g}-thick", f"{primary} bar", g, bar_x, thick_y, bar_w, 5, slot, primary, 2.5)
        if secondary:
            out += tracks(f"{g}-thin", secondary, g, bar_x, thin_y, bar_w, 2, 1)
            out += bar(f"{g}-thin", f"{secondary} hairline", g, bar_x, thin_y, bar_w, 2, slot, secondary, 1,
                       opacity="0.55")
        out += readout(f"{g}-text", f"{primary} text", g, text_x, 0, width - text_x, row_h, slot, primary,
                       f"{{{slot['key']}.{primary}.display:usage_line}}", 11,
                       "medium" if mode == "5h" else "regular", tone="account" if mode == "5h" else "quiet")
        return out
    return build


def cells_slot(mode, hover="near"):
    """A vertical gauge for the main limit with a sliver for the second. On hover, the main limit's
    percentage and reset time ("near"), or those with the second limit's percentage under them
    ("both")."""
    # The slot is 32 px wide with a 1 px margin on each side, so cells sit 2 px apart.
    cell_x, cell_w, sliver_x, sliver_w, cell_y, cell_h = 9, 12, 23, 3, 3, 28

    def build(slot, g):
        key, main, second = slot["key"], slot["main"], slot["second"]
        if mode == "gauges":
            out = tracks(f"{g}-cell", main, g, cell_x, cell_y, cell_w, cell_h, 3)
            out += bar(f"{g}-cell", f"{main} gauge", g, cell_x, cell_y, cell_w, cell_h, slot, main, 3,
                       "bottom_to_top")
            if second:
                out += tracks(f"{g}-sliver", second, g, sliver_x, cell_y, sliver_w, cell_h, 1.5)
                out += bar(f"{g}-sliver", f"{second} sliver", g, sliver_x, cell_y, sliver_w, cell_h, slot, second,
                           1.5, "bottom_to_top", opacity="0.6")
            for theme, cond in THEMES:
                # "!" for a failed account, "--" while loading, over the empty gauge.
                out.append(layer(f"{g}-status-{theme}", f"{theme} status", g, cell_x - 4, cell_y + 8, cell_w + 8, 12,
                                 text(f"{{{key}.{main}.display:usage_badge}}", NEUTRAL[theme]["dim"], 8,
                                      "bold", "center"), f"({cond}) && ({key}.available == 0)"))
        elif hover == "near":
            out = readout(f"{g}-pct", f"{main} percent", g, 0, 4, 32, 13, slot, main,
                          f"{{{key}.{main}.display:usage_badge}}", 10.5, "bold", "center",
                          after_reset=("0%", "100%"))
            out += reset_time(f"{g}-when", f"{main} reset time", g, 1, 18, 30, 12, slot, main, 9.5, "center")
        else:
            # Three short lines over the name: the main limit and its reset time, then the second
            # limit's percentage, quiet unless it runs high (its reset time is left to Lanes and Pills).
            out = readout(f"{g}-pct", f"{main} percent", g, 0, 1, 32, 12, slot, main,
                          f"{{{key}.{main}.display:usage_badge}}", 10, "bold", "center",
                          after_reset=("0%", "100%"))
            out += reset_time(f"{g}-when", f"{main} reset time", g, 1, 12, 30, 10, slot, main, 8.5, "center")
            if second:
                out += readout(f"{g}-pct2", f"{second} percent", g, 0, 22, 32, 11, slot, second,
                               f"{{{key}.{second}.display:usage_badge}}", 9.5, "bold", "center",
                               tone="quiet", after_reset=("0%", "100%"))
        out += labels(f"{g}-label", "label", g, 1, 33, 30, 11, slot, 8.5, "center")
        return out
    return build


def pills_slot(mode):
    """A soft card: name, time to reset, big percentage, bars. Hover: the second limit."""
    view = "near" if mode == "5h" else "far"
    # The name and the reset time share the top row, in boxes that don't overlap, so a long name or
    # time is cut off instead of running into the other.
    pill_w, pad, label_w, when_w = 60, 5, 29, 21
    bar_w = pill_w - 2 * pad
    card = {"dark": ("#FFFFFF0E", "#FFFFFF12"), "light": ("#0000000A", "#00000014")}

    def build(slot, g):
        key = slot["key"]
        primary, secondary = windows(slot, view)
        out = [shape(f"{g}-card-{theme}", f"{theme} card", g, 0, 4, pill_w, 38, card[theme][0], 7, cond,
                     card[theme][1]) for theme, cond in THEMES]
        out += labels(f"{g}-label", "label", g, pad, 6, label_w, 11, slot, 9, "left")
        out += reset_time(f"{g}-when", f"{primary} reset time", g, pill_w - pad - when_w, 6, when_w, 11, slot,
                          primary, 8.5, "right")
        out += readout(f"{g}-big", f"{primary} percent", g, pad, 15, bar_w, 16, slot, primary,
                       f"{{{key}.{primary}.display:usage_badge}}", 13.5, "bold",
                       tone="strong" if mode == "5h" else "quiet", after_reset=("0%", "100%"))
        out += tracks(f"{g}-thick", primary, g, pad, 32, bar_w, 3, 1.5)
        out += bar(f"{g}-thick", f"{primary} bar", g, pad, 32, bar_w, 3, slot, primary, 1.5)
        if secondary:
            out += tracks(f"{g}-thin", secondary, g, pad, 37, bar_w, 2, 1)
            out += bar(f"{g}-thin", f"{secondary} hairline", g, pad, 37, bar_w, 2, slot, secondary, 1,
                       opacity="0.55")
        return out
    return build


# For each design: slot size, how slots are laid out, how many show at most, the container's
# box and the widget's width (both from n, the number of accounts shown), and the two views.
DESIGNS = {
    "lanes": {
        "title": "Lanes", "slot": (145, 13), "layout": "column", "gap": 1, "max": 3,
        "container": lambda n: (0, f"floor((47 - 14 * {n}) / 2)", 145, f"max(1, 14 * {n} - 1)"),
        "width": lambda n: "145",
        "views": [("lanes-5h", "5-hour view", "1", lanes_slot("5h")),
                  ("lanes-wk", "Weekly view (on hover)", "0", lanes_slot("wk"))],
    },
    "cells": {
        "title": "Cells", "slot": (32, 46), "layout": "row", "gap": 0, "max": 6,
        "container": lambda n: (-1, 0, f"max(1, 32 * {n})", 46),
        "width": lambda n: f"if({n} == 0, 30, 32 * {n} - 2)",
        "views": [("cells-gauges", "Gauges", "1", cells_slot("gauges")),
                  ("cells-numbers", "Numbers (on hover)", "0", cells_slot("numbers"))],
    },
    # Cells Horizon: the Cells gauges; on hover, the 5-hour numbers with the weekly percentage under them.
    "cells-horizon": {
        "title": "Cells Horizon", "slot": (32, 46), "layout": "row", "gap": 0, "max": 6,
        "container": lambda n: (-1, 0, f"max(1, 32 * {n})", 46),
        "width": lambda n: f"if({n} == 0, 30, 32 * {n} - 2)",
        "views": [("horizon-gauges", "Gauges", "1", cells_slot("gauges")),
                  ("horizon-both", "Both limits' numbers (on hover)", "0", cells_slot("numbers", "both"))],
    },
    "pills": {
        "title": "Pills", "slot": (60, 46), "layout": "row", "gap": 3, "max": 6,
        "container": lambda n: (0, 0, f"max(1, 63 * {n} - 3)", 46),
        "width": lambda n: f"if({n} == 0, 60, 63 * {n} - 3)",
        "views": [("pills-5h", "5-hour view", "1", pills_slot("5h")),
                  ("pills-wk", "Weekly view (on hover)", "0", pills_slot("wk"))],
    },
}


# ---------------------------------------------------------------- tray icon

TRAY_SURFACE = "shared-tray-icon"
TRAY_TRACK = {"dark": "#FFFFFF38", "light": "#00000030"}


def tray_children(surface_id):
    """One icon that follows a single account: whichever is closest to any of its limits. It shows
    that account's main limit as a number in the account's color (its second limit if the plan has no
    main one), over a bar for its second limit, both turning amber and red like the widget. "!" or "--" when no account has a reading yet."""
    slots = all_slots()

    def closeness(slot):
        key, main, second = slot["key"], slot["main"], slot["second"]
        value = eff_pct(key, main)
        if second:
            value = f"max({value}, {eff_pct(key, second)})"
        return f"if({slot['present']} && ({key}.available != 0), {value}, -1)"

    near = [closeness(slot) for slot in slots]
    objects = []
    for i, slot in enumerate(slots):
        # Ties go to the earlier slot, so exactly one account wins.
        wins = " && ".join([f"({near[i]} >= 0)"] + [f"({near[i]} > {near[j]})" for j in range(i)]
                           + [f"({near[i]} >= {near[j]})" for j in range(i + 1, len(slots))])
        group = f"tray-{slot['slug']}"
        objects.append(layer(group, slot["title"], surface_id, 0, 0, 64, 64, render=wins))
        key, main = slot["key"], slot["main"]
        second = slot["second"] or main
        # A plan without the main window (some Codex plans have no 5-hour limit) shows its second.
        pct = f"if({missing(key, main)}, {eff_pct(key, second)}, {eff_pct(key, main)})"
        shown = f"round(if(display.countdown, 100 - ({pct}), {pct}))"
        for theme, cond in THEMES:
            for render, level in warn_states(pct):
                color = WARN[level][1 if theme == "dark" else 2] if level else slot["text"][theme]
                number = text(f"{{{shown}:0}}", color, 36, "bold", "center", faded(key, "1", "0.45"))
                number["font_size"] = f"if({shown} >= 100, 26, 36)"  # "100" needs a smaller size to fit
                objects.append(layer(f"{group}-number-{level or 'ok'}-{theme}",
                                     f"{theme} {main} number ({level or 'normal'})", group, -6, -6, 76, 54,
                                     number, f"({cond}) && {render}"))
            objects.append(shape(f"{group}-track-{theme}", f"{theme} {second} track", group, 4, 50, 56, 11,
                                 TRAY_TRACK[theme], 5.5, cond))
        bar_pct = eff_pct(key, second)
        for render, level in warn_states(bar_pct):
            color = WARN[level][0] if level else slot["fill"]
            objects.append(layer(f"{group}-bar-{level or 'ok'}", f"{second} bar ({level or 'normal'})", group,
                                 4, 50, 56, 11, progress(eff_disp(key, second), color, 5.5,
                                                         opacity=faded(key, "1", "0.45")), render))
    # No reading anywhere: the first account's "!" (failed) or "--" (loading), or "--" with no accounts.
    none = " && ".join(f"({value} < 0)" for value in near)
    objects.append(layer("tray-status", "No reading yet", surface_id, 0, 0, 64, 64, render=none))
    present = [slot["present"] for slot in slots]
    for i, slot in enumerate(slots):
        first = " && ".join([slot["present"]] + [f"!{p}" for p in present[:i]])
        for theme, cond in THEMES:
            objects.append(layer(f"tray-{slot['slug']}-status-{theme}", f"{theme} {slot['title']} status",
                                 "tray-status", 0, -6, 64, 54,
                                 text(f"{{{slot['key']}.{slot['main']}.display:usage_badge}}", NEUTRAL[theme]["strong"],
                                      36, "bold", "center"),
                                 f"({cond}) && {first}"))
    for theme, cond in THEMES:
        objects.append(layer(f"tray-no-accounts-{theme}", f"{theme} no accounts yet", "tray-status", 0, -6, 64, 54,
                             text("--", NEUTRAL[theme]["strong"], 36, "bold", "center"),
                             f"({cond}) && !({' || '.join(present)})"))
    return objects


# ---------------------------------------------------------------- assembly

def build_theme(design, base):
    spec = DESIGNS[design]
    slots = all_slots()
    present = [slot["present"] for slot in slots]
    count = f"({' + '.join(present)})"
    n = f"min({spec['max']}, {count})"
    slot_w, slot_h = spec["slot"]
    objects = []
    for view, view_name, visible, build in spec["views"]:
        objects.append(layer(view, view_name, "main", 0, 0, "canvas.width", 46, render=visible))
        container = layer(f"{view}-slots", "Accounts", view, *spec["container"](n))
        container["layout"], container["gap"] = spec["layout"], f"{spec['gap']:g}"
        objects.append(container)
        for index, slot in enumerate(slots):
            before = f"({' + '.join(present[:index])})" if index else "0"
            group = f"{view}-{slot['slug']}"
            objects.append(layer(group, slot["title"], container["id"], 0, 0, slot_w, slot_h,
                                 render=f"{slot['present']} && ({before} < {spec['max']})"))
            objects += build(slot, group)
    for theme, cond in THEMES:
        objects.append(layer(f"no-accounts-{theme}", f"{theme} no accounts yet", "main", 0, 0, "canvas.width", 46,
                             text("--", NEUTRAL[theme]["dim"], 11, "regular", "center"),
                             f"({cond}) && ({count} == 0)"))

    theme = copy.deepcopy(base)
    theme["id"] = f"headroom-{design}"
    theme["name"] = f"Headroom {spec['title']}"
    surface = theme["surfaces"][0]
    assert surface["id"] == "main"
    surface["name"] = f"{spec['title']} widget"
    surface["width"], surface["height"] = spec["width"](n), "46"
    first, second = spec["views"][0][0], spec["views"][1][0]
    surface["mouse_events"] = {
        "double_click": "show_dashboard()",
        "right_click": 'show_context_menu("classic-v1")',
        "mouse_enter": f'set("{first}", render, 0); set("{second}", render, 1)',
        "mouse_leave": f'reset("{first}", render); reset("{second}", render)',
    }
    surface["children"] = objects
    ids = [o["id"] for o in objects]
    assert len(ids) == len(set(ids)), f"duplicate ids in {theme['id']}"
    assert all(o["parent"] in set(ids) | {"main"} for o in objects), f"dangling parent in {theme['id']}"

    # The tray icon keeps its place among the surfaces, so Windows remembers whether you pinned it.
    tray = next(s for s in theme["surfaces"] if s["id"] == TRAY_SURFACE)
    tray["name"] = "Headroom tray icon"
    tray["background"], tray["border"] = {"type": "none"}, None
    tray["mouse_events"]["double_click"] = "show_dashboard()"
    tray["children"] = tray_children(TRAY_SURFACE)
    tray_ids = [o["id"] for o in tray["children"]]
    assert len(tray_ids) == len(set(tray_ids)), f"duplicate tray ids in {theme['id']}"
    return theme


def main():
    base = json.loads(BASE_THEME.read_text(encoding="utf-8"))
    out_dir = ROOT / "themes"
    out_dir.mkdir(parents=True, exist_ok=True)
    for design in DESIGNS:
        theme = build_theme(design, base)
        path = out_dir / f"{theme['id']}.json"
        path.write_text(json.dumps(theme, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        size = path.stat().st_size // 1024
        print(f"{path.relative_to(ROOT)}  {theme['name']}  {len(theme['surfaces'][0]['children'])} objects, {size} KB")


if __name__ == "__main__":
    main()
