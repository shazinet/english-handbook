#!/usr/bin/env python3
"""Is today's practice done, and how long is the streak?

The daily loop is reps -> journal -> /check, and a day only counts when all
three happened. Each leaves a durable trace, so this can be answered from disk
without anyone remembering to log anything:

    reps     rows in Anki's revlog dated today, and nothing left due
    journal  me/journal/<today>.md exists with real writing in it
    check    /check appends a `<!-- checked: ... -->` marker to that file

Everything is keyed to the local *calendar* day, because the thing being counted
down to is midnight. Note that Anki's own day rolls over at 4am, so between
midnight and 4am Anki still calls it yesterday while this script has moved on.
That only matters if you review after midnight, and in that case the reviews
land on the new day here — which is what the countdown implies anyway.

    python3 build/status.py           # human-readable
    python3 build/status.py --json    # for remind.py and the phone widget
"""

import argparse
import json
import sqlite3
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

from ankidb import COLLECTION, DECK_PREFIX, LEGACY_PREFIX, snapshot
from paths import CONFIG, JOURNAL

# Written by /check. Changing this string breaks every past day's streak, since
# the marker is the only record that /check ever ran.
CHECK_MARKER = "<!-- checked:"

DEFAULTS = {
    "journal_min_words": 30,
    "gist_id": "",
    "gh_bin": "",
    "celebrate": True,
    "ntfy": {"server": "https://ntfy.sh", "topic": ""},
    "tiers": [
        {"at": "20:00", "priority": "default"},
        {"at": "22:00", "priority": "high"},
        {"at": "23:00", "priority": "high"},
        {"at": "23:30", "priority": "urgent"},
    ],
}


def load_config() -> dict:
    """Merge me/.reminders.json over DEFAULTS. Missing file is fine — status
    works standalone; only the notifier needs the ntfy and gist settings."""
    conf = json.loads(json.dumps(DEFAULTS))  # deep copy of plain JSON data
    if CONFIG.exists():
        user = json.loads(CONFIG.read_text())
        for key, value in user.items():
            if isinstance(value, dict) and isinstance(conf.get(key), dict):
                conf[key].update(value)
            else:
                conf[key] = value
    return conf


# --- journal -----------------------------------------------------------------


def body_words(text: str) -> int:
    """Words of actual writing: no heading, no bullet markers, no markers."""
    words = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("<!--"):
            continue
        words += len(line.lstrip("-*>").split())
    return words


def journal_state(day: date, min_words: int) -> tuple[bool, bool, int]:
    """(written, checked, words) for one day's entry."""
    path = JOURNAL / f"{day.isoformat()}.md"
    if not path.exists():
        return False, False, 0
    text = path.read_text()
    words = body_words(text)
    # /journal seeds the file with a prompt the writer is meant to delete, so
    # "the file exists" is not evidence that anything was written.
    return words >= min_words, CHECK_MARKER in text, words


# --- anki --------------------------------------------------------------------


def deck_due(col) -> int:
    """Cards waiting in the app's deck tree.

    Read the root node, not the sum of its children: install_deck.py gives every
    subdeck the same 6-new/day preset, so the children add up to far more than
    the parent will actually serve.
    """
    for node in col.sched.deck_due_tree().children:
        if node.name in (DECK_PREFIX, LEGACY_PREFIX):  # before/after the rename
            return node.new_count + node.learn_count + node.review_count
    return 0


def revlog(db_path: Path, today: date) -> tuple[set[str], int]:
    """(every local date with a review, reviews logged today).

    Plain sqlite3, no anki lib: the streak needs this history even on a day when
    the collection is too new or too old for the installed library to open.
    """
    start = int(datetime.combine(today, time.min).timestamp() * 1000)
    end = int(datetime.combine(today + timedelta(days=1), time.min).timestamp() * 1000)
    con = sqlite3.connect(db_path)
    try:
        days = {
            row[0]
            for row in con.execute(
                "select distinct date(id/1000, 'unixepoch', 'localtime') from revlog"
            )
        }
        # Bounded at both ends so --date on a past day reports that day, not
        # every review since.
        count = con.execute(
            "select count() from revlog where id >= ? and id < ?", (start, end)
        ).fetchone()[0]
    finally:
        con.close()
    return days, count


def anki_state(today: date) -> dict:
    """Due count and review history, read from a copy so Anki can stay open.

    Degrades rather than raises, in two stages: a reminder that says "couldn't
    read Anki" is more useful than a launchd job that dies, and losing the due
    count shouldn't also cost you the streak.
    """
    state = {"due": None, "reviews_today": 0, "review_days": set(), "error": None}
    try:
        with snapshot() as copy:
            state["review_days"], state["reviews_today"] = revlog(copy, today)
            try:
                from anki.collection import Collection

                col = Collection(str(copy))
                try:
                    state["due"] = deck_due(col)
                finally:
                    col.close()
            except Exception as exc:  # library/collection version mismatch
                state["error"] = f"no due count ({type(exc).__name__}: {exc})"
    except Exception as exc:  # torn copy, missing collection, unreadable revlog
        state["error"] = f"{type(exc).__name__}: {exc}"
    return state


# --- status ------------------------------------------------------------------


def day_complete(day: date, days_reviewed: set[str], min_words: int) -> bool:
    """Did all three parts of the loop happen on this past day?"""
    if day.isoformat() not in days_reviewed:
        return False
    written, checked, _ = journal_state(day, min_words)
    return written and checked


def compute(today: date | None = None, conf: dict | None = None) -> dict:
    conf = conf or load_config()
    today = today or date.today()
    min_words = conf["journal_min_words"]

    anki = anki_state(today)
    written, checked, words = journal_state(today, min_words)

    # Reps count only if cards actually got answered. `due == 0` alone would
    # hand you a free day whenever nothing happened to be scheduled.
    anki_done = anki["due"] == 0 and anki["reviews_today"] > 0

    streak = 0
    day = today - timedelta(days=1)
    while day_complete(day, anki["review_days"], min_words):
        streak += 1
        day -= timedelta(days=1)
    done = anki_done and written and checked
    if done:
        streak += 1

    remaining = []
    if not anki_done:
        if anki["error"]:
            remaining.append("Anki (unreadable)")
        elif anki["due"]:
            remaining.append(f"{anki['due']} cards")
        else:
            remaining.append("reps")
    if not written:
        remaining.append("journal")
    if not checked:
        remaining.append("check")

    now = datetime.now()
    midnight = datetime.combine(today + timedelta(days=1), time.min)
    stale = None
    if COLLECTION.exists():
        age = now - datetime.fromtimestamp(COLLECTION.stat().st_mtime)
        stale = int(age.total_seconds() // 60)

    return {
        "generated_at": now.astimezone().isoformat(timespec="seconds"),
        "date": today.isoformat(),
        "done": done,
        "streak": streak,
        "minutes_left": max(0, int((midnight - now).total_seconds() // 60)),
        "due": anki["due"],
        "reviews_today": anki["reviews_today"],
        "anki_done": anki_done,
        "journal_done": written,
        "journal_words": words,
        "checked": checked,
        "remaining": remaining,
        "collection_stale_minutes": stale,
        "anki_error": anki["error"],
    }


def humanize(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins:02d}m" if hours else f"{mins}m"


def render(s: dict) -> str:
    mark = lambda ok: "\033[32m✓\033[0m" if ok else "\033[31m✗\033[0m"
    day = date.fromisoformat(s["date"]).strftime("%a %-d %b")

    if s["anki_error"]:
        anki = f"couldn't read the collection — {s['anki_error']}"
    else:
        anki = f"{s['due']} due · {s['reviews_today']} reviewed today"
    journal = (
        f"me/journal/{s['date']}.md ({s['journal_words']} words)"
        if s["journal_done"]
        else "nothing written yet"
    )
    check = "logged to errors.md" if s["checked"] else "/check hasn't run yet"

    lines = [
        f"English — {day}, {humanize(s['minutes_left'])} left today",
        "",
        f"  {mark(s['anki_done'])} Anki     {anki}",
        f"  {mark(s['journal_done'])} Journal  {journal}",
        f"  {mark(s['checked'])} Check    {check}",
        "",
    ]
    if s["done"]:
        lines.append(f"  🔥 {s['streak']} — done for today.")
    else:
        at_risk = " — today would break it" if s["streak"] else ""
        lines.append(f"  🔥 {s['streak']}{at_risk}. Still to do: {', '.join(s['remaining'])}.")

    stale = s["collection_stale_minutes"]
    if stale is not None and stale > 60 * 12:
        lines += [
            "",
            f"  Note: the desktop collection hasn't changed in {humanize(stale)}.",
            "  Reps done on the phone stay invisible here until you sync Anki on this Mac.",
        ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--date", help="pretend it is this YYYY-MM-DD (for testing)")
    args = ap.parse_args()

    day = date.fromisoformat(args.date) if args.date else None
    status = compute(today=day)
    print(json.dumps(status, indent=2) if args.json else render(status))


if __name__ == "__main__":
    sys.exit(main())
