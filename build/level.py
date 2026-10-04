#!/usr/bin/env python3
"""Your English level: history, evidence, and recording new results.

    ./english level                         current level, history, and the signals
    ./english level --efset 62              record an EF SET score (efset.org, free)
    ./english level --record B2 --areas "tenses=B2,articles=B1" --weak "articles"
                                            record a /level placement (Claude runs this)

Recording a level also updates me/profile.yml: `level`, `deck.max_level` (one
step above, so new topics stay reachable — capped at C1, where the content ends)
and, if given, `weak_areas`. Comments in the profile are preserved.
"""

import argparse
import re
import sys
from datetime import date

from paths import CEFR, PROFILE
from progress import (
    anki_stats, current_level, efset_to_cefr, errors_per_100_by_month, load_history,
    save_history, top_error_points,
)


def update_profile(level: str, weak: list[str] | None, keep_deck: bool) -> list[str]:
    """Rewrite just the affected lines of profile.yml; return what changed."""
    if not PROFILE.exists():
        return ["(no me/profile.yml yet — run ./english setup)"]
    text = PROFILE.read_text()
    changes = []

    def sub(pattern: str, value: str, label: str) -> None:
        nonlocal text
        new, n = re.subn(pattern, lambda m: f"{m.group(1)} {value}{m.group(2) or ''}",
                         text, count=1, flags=re.M)
        if n and new != text:
            changes.append(f"{label} → {value}")
        text = new

    sub(r"^(level:)[ \t]*[^#\n]*?([ \t]+#.*)?$", level, "level")
    if not keep_deck:
        cap = CEFR[min(CEFR.index(level) + 1, CEFR.index("C1"))]
        sub(r"^([ \t]+max_level:)[ \t]*[^#\n]*?([ \t]+#.*)?$", cap, "deck.max_level")
    if weak:
        flow = "[" + ", ".join(weak) + "]"
        new, n = re.subn(r"^weak_areas:.*(?:\n[ \t]+-.*)*", f"weak_areas: {flow}",
                         text, count=1, flags=re.M)
        if n:
            text = new
            changes.append(f"weak_areas → {flow}")
    PROFILE.write_text(text)
    return changes


def record(entry: dict, keep_deck: bool, weak: list[str] | None) -> None:
    entries = [e for e in load_history()
               if not (str(e["date"]) == entry["date"] and e["source"] == entry["source"])]
    entries.append(entry)
    save_history(sorted(entries, key=lambda e: str(e["date"])))
    print(f"Recorded {entry['overall']} ({entry['source']}) for {entry['date']}.")
    for change in update_profile(entry["overall"], weak, keep_deck):
        print(f"  profile: {change}")
    if not keep_deck:
        print("Apply it to your deck: sync Anki → quit Anki → ./english build → ./english deck")


def show() -> None:
    now = current_level()
    if now:
        how = f"EF SET {now['score']}" if now["source"] == "efset" else "estimate from /level"
        print(f"Level: {now['overall']}  ({how}, {now['date']})")
    else:
        print("Level: not measured yet — run /level in Claude Code, or take the free")
        print("EF SET test (efset.org) and record it: ./english level --efset <score>")

    history = load_history()
    if history:
        print("\nHistory")
        for e in history:
            extra = f"score {e['score']}" if e.get("score") is not None else ""
            areas = ", ".join(f"{k} {v}" for k, v in (e.get("areas") or {}).items())
            print(f"  {e['date']}  {e['overall']:<3} {e['source']:<10} {extra or areas}")

    months = errors_per_100_by_month()[-4:]
    if months:
        print("\nErrors per 100 words written (lower is better; harder writing raises it)")
        for m in months:
            print(f"  {m['month']}  {m['rate']:>5}   ({m['errors']} errors / {m['words']} words)")

    anki = anki_stats()
    if anki["error"]:
        print(f"\nAnki: {anki['error']}")
    elif anki["reviews"]:
        print(f"\nAnki, last 30 days: {anki['retention']}% of {anki['reviews']} reviews passed"
              f" · {anki['learned']}/{anki['total']} cards learned")
        weakest = [t for t in anki["by_topic"] if t["reviews"] >= 10][:3]
        if weakest:
            print("  weakest topics: " + ", ".join(
                f"{t['topic']} {t['retention']}%" for t in weakest))

    top = top_error_points()
    if top:
        print("\nMost frequent errors, last 60 days: "
              + ", ".join(f"{p} ×{n}" for p, n in top[:4]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--efset", type=int, metavar="SCORE", help="record an EF SET score (0–100)")
    ap.add_argument("--record", choices=CEFR, metavar="LEVEL", help="record a placement result")
    ap.add_argument("--source", default="placement", help="where --record came from")
    ap.add_argument("--areas", default="", help='per-area levels, "tenses=B2,articles=B1"')
    ap.add_argument("--weak", default="", help='comma-separated weak areas for the profile')
    ap.add_argument("--note", default="", help="one line of evidence or caveat")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--keep-deck", action="store_true", help="don't change deck.max_level")
    args = ap.parse_args()

    weak = [w.strip() for w in args.weak.split(",") if w.strip()] or None

    if args.efset is not None:
        if not 0 <= args.efset <= 100:
            sys.exit("EF SET scores run from 0 to 100")
        entry = {"date": args.date, "source": "efset", "overall": efset_to_cefr(args.efset),
                 "score": args.efset}
        if args.note:
            entry["note"] = args.note
        record(entry, args.keep_deck, weak)
        return 0

    if args.record:
        areas = {}
        for pair in filter(None, (p.strip() for p in args.areas.split(","))):
            key, _, value = pair.partition("=")
            if value.strip().upper() not in CEFR:
                sys.exit(f"area level must be one of {', '.join(CEFR)}: {pair!r}")
            areas[key.strip()] = value.strip().upper()
        entry = {"date": args.date, "source": args.source, "overall": args.record}
        if areas:
            entry["areas"] = areas
        if args.note:
            entry["note"] = args.note
        record(entry, args.keep_deck, weak)
        return 0

    show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
