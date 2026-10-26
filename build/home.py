#!/usr/bin/env python3
"""The home screen: where you are on the path, what's next, today's quests,
and everything you can practise with what it earns.

    ./english              (no command) the same as ./english home
    ./english home --json  the same data, for /practice, /journal and /drill

It shows dashboard.gather()'s numbers, so the terminal and the dashboard can
never disagree. The next step (learning_path.next_step) always puts the daily
loop first, because a day only counts when reps, journal and /check are done.
"""

import argparse
import json
import os
import sys

from dashboard import gather

ZIGZAG = (6, 10, 12, 10, 6, 2, 0, 2)   # indents that make the path wind


def summary(d: dict) -> dict:
    g, route = d["game"], d["path"]
    cur = route["current"]
    return {
        "next": d["next"],
        "streak": g["streak"], "streak_at_risk": g["streak_at_risk"],
        "xp": g["xp"], "level": g["level"], "title": g["title"], "xp_to_next": g["xp_to_next"],
        "today_xp": g["today_xp"], "xp_left_today": g["xp_left_today"],
        "unit": {k: cur[k] for k in ("number", "point", "level", "lessons_done", "lessons_total",
                                     "stars", "lessons")} if cur else None,
        "upcoming": [{"number": u["number"], "point": u["point"]} for u in route["upcoming"]],
        "units_done": route["units_done"], "units_total": route["units_total"],
        "quests": g["quests"],
        "activities": g["activities"],
        "mistakes_open": d["mistakes"]["open"],
    }


class Ink:
    def __init__(self, on: bool):
        self.on = on

    def __call__(self, text, code):
        return f"\033[{code}m{text}\033[0m" if self.on else str(text)

    def bold(self, t): return self("" if t is None else t, "1")
    def dim(self, t): return self(t, "2")
    def green(self, t): return self(t, "32")
    def yellow(self, t): return self(t, "33")
    def blue(self, t): return self(t, "34")
    def magenta(self, t): return self(t, "35")
    def cyan(self, t): return self(t, "36")


def bar(progress: float, width: int = 10) -> str:
    full = round(progress * width)
    return "▰" * full + "▱" * (width - full)


def render(s: dict, ink: Ink) -> str:
    out = []
    flame = ink.yellow(f"🔥 {s['streak']}") if not s["streak_at_risk"] else ink.dim(f"🔥 {s['streak']}")
    xp = ink.blue("⚡ {:,} XP".format(s["xp"]))
    today = ink.green("+{} today".format(s["today_xp"]))
    out.append(f" {flame}   {xp} · Level {s['level']} {s['title']}"
               f" · {s['xp_to_next']:,} to go   {today}"
               + ink.dim(f" ({s['xp_left_today']} more on offer)"))
    if s["streak_at_risk"]:
        out.append(ink.yellow(f" Finish today to make your streak {s['streak'] + 1}."))
    out.append("")

    u = s["unit"]
    rule = "━" * 60
    if u:
        stars = "★" * u["stars"] + "☆" * (3 - u["stars"])
        out.append(ink.green(rule))
        out.append(ink.bold(f"  UNIT {u['number']} · {u['point']}") + ink.dim(f"  ({u['level']})"))
        out.append(f"  {stars}  {u['lessons_done']}/{u['lessons_total']} lessons"
                   + ink.dim(f"  ·  {s['units_done']} of {s['units_total']} units finished"))
        out.append(ink.green(rule))
        out.append("")
        first_open = True
        for i, lesson in enumerate(u["lessons"]):
            pad = " " * (4 + ZIGZAG[i % len(ZIGZAG)])
            if lesson["done"]:
                out.append(pad + ink.green("( ✓ )") + f"  {lesson['name']}")
            elif first_open:
                out.append(pad + ink.yellow(ink.bold("( ▶ )")) + ink.bold(f"  {lesson['name']}")
                           + ink.yellow("   ← start here"))
                out.append(pad + "       " + ink.dim(lesson["how"]))
                if lesson["detail"]:
                    out.append(pad + "       " + ink.dim(lesson["detail"]))
                first_open = False
            else:
                out.append(pad + ink.dim("( · )") + f"  {lesson['name']}")
        pad = " " * (4 + ZIGZAG[len(u["lessons"]) % len(ZIGZAG)])
        out.append(pad + ink.yellow("[▣]") + ink.dim("   chest: +50 XP when all four are done"))
        if s["upcoming"]:
            out.append("")
            out.append(ink.dim("  Then: " + "  ›  ".join(f"{x['number']}. {x['point']}" for x in s["upcoming"])))
    else:
        out.append(ink.green(f"  Every unit on the path is finished ({s['units_total']})."))
    out.append("")

    n = s["next"]
    out.append(ink.bold(ink.magenta(" NEXT ▸ ")) + ink.bold(n["text"]))
    out.append("         " + ink.cyan(n["command"]))
    out.append("")

    q = s["quests"]
    if q:
        out.append(ink.bold(" DAILY QUESTS") + ink.dim(f"   {sum(x['done'] for x in q)}/{len(q)} · +10 XP each, +20 for all three"))
        for x in q:
            val = f"{x['value']:g}/{x['target']} {x['unit']}".strip()
            mark = ink.green("✓") if x["done"] else " "
            out.append(f"  {mark} {(ink.green if x['done'] else ink.yellow)(bar(x['progress']))}  "
                       f"{x['name']:<30}{ink.dim(val)}")
        out.append("")

    out.append(ink.bold(" PRACTICE"))
    group = None
    for a in s["activities"]:
        if a["group"] != group:
            group = a["group"]
            out.append(ink.dim(f"  {group}"))
        count = f"{a['count']} {a['count_label']}" if a["count"] else ""
        tick = ink.green("✓") if a["done_today"] else " "
        command, count = ink.cyan(a["command"].ljust(26)), ink.yellow(count.ljust(10))
        out.append(f"  {tick} {a['name']:<11} {command}{count}{ink.dim(a['xp_label'])}")
    out.append("")
    out.append(ink.dim(" In Claude Code: /practice picks one for you. The dashboard shows the same."))
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="print the data instead")
    a = ap.parse_args()
    s = summary(gather())
    if a.json:
        print(json.dumps(s, indent=2, ensure_ascii=False, default=str))
    else:
        color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
        print(render(s, Ink(color)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
