#!/usr/bin/env python3
"""A log of practice sessions that leave no other trace.

Anki reviews, journal entries, /check and `./english speak` are all read from
their own evidence (the revlog, the journal files and their markers), so they
are never logged here. Everything else — a /drill, a /roleplay, a /mistakes
round, a /story, a /call, a stretch of listening — appends one line to
me/activity.log, which is what lets those sessions earn XP, fill quests and
move the path (see gamify.py and learning_path.py).

    2026-10-26T19:40<TAB>drill<TAB>6B Conditionals<TAB>items=9 correct=7<TAB>note

Logging never decides whether a day is done: that stays reps + journal + /check
(status.py), so none of these can stand in for the daily loop.

    ./english log drill --point "6B Conditionals" --items 9 --correct 7
    ./english log roleplay --minutes 15 --goal yes
    ./english log story --items 4 --correct 3 --goal yes   (goal = retold)
    ./english listen 25 --what "a podcast episode"
"""

import argparse
import sys
from datetime import datetime

from paths import ME

LOG = ME / "activity.log"
KINDS = ("drill", "roleplay", "mistakes", "story", "listen", "call")
NUMBERS = ("items", "correct", "minutes")


def record(kind: str, point: str | None = None, note: str = "", **nums) -> str:
    """Append one session and return the line written."""
    if kind not in KINDS:
        raise ValueError(f"unknown activity {kind!r}; expected one of {', '.join(KINDS)}")
    fields = " ".join(f"{k}={v}" for k, v in nums.items() if v is not None)
    line = "\t".join([datetime.now().strftime("%Y-%m-%dT%H:%M"), kind, point or "", fields,
                      " ".join(note.split())])
    ME.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(line + "\n")
    return line


def read() -> list[dict]:
    """Every logged session, oldest first. Malformed lines are skipped."""
    if not LOG.exists():
        return []
    out = []
    for raw in LOG.read_text().splitlines():
        parts = raw.split("\t")
        if len(parts) < 2 or parts[1] not in KINDS:
            continue
        parts += [""] * (5 - len(parts))
        stamp, kind, point, fields, note = parts[:5]
        row = {"at": stamp, "date": stamp[:10], "kind": kind, "point": point or None, "note": note}
        for pair in fields.split():
            key, _, value = pair.partition("=")
            if key == "goal":
                row["goal"] = value == "yes"
            else:
                try:
                    row[key] = int(value)
                except ValueError:
                    pass
        out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=KINDS)
    ap.add_argument("--point", help="the grammar point practised, as in its card file's point:")
    for name in NUMBERS:
        ap.add_argument(f"--{name}", type=int)
    ap.add_argument("--goal", choices=("yes", "no"),
                    help="roleplay or call: was the goal won? story: was it retold?")
    ap.add_argument("--note", default="", help="a few words about the session")
    a = ap.parse_args()
    if a.kind in ("listen", "call") and not a.minutes:
        ap.error(f"{a.kind} needs --minutes")
    print(record(a.kind, a.point, a.note, goal=a.goal,
                 **{n: getattr(a, n) for n in NUMBERS}).replace("\t", "  "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
