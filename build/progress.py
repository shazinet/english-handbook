#!/usr/bin/env python3
"""Measurements of progress, all derived from data the loop already produces.

Nothing here asks the learner to log anything. The level estimate itself comes
from /level or an EF SET score (level-history.yml); everything else is computed:

    errors per 100 words   me/errors.md rows against words written in me/journal/
    retention              share of Anki reviews passed, per topic (FSRS aims ~90%)
    cards learned          cards in the deck that are no longer new
    recurring errors       which grammar points keep coming back

Shared by level.py (terminal) and report.py (the shareable page).
"""

import re
import sqlite3
import time
from collections import Counter, defaultdict
from datetime import date, timedelta

import yaml

from ankidb import DECK_PREFIX, LEGACY_PREFIX, snapshot
from paths import CEFR, ERRORS, JOURNAL, LEVELS
from status import body_words

ROW_RE = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([^|]+?)\s*\|")

# EF SET's published score bands (0–100 scale).
EFSET_BANDS = ((30, "A1"), (40, "A2"), (50, "B1"), (60, "B2"), (70, "C1"), (100, "C2"))


def efset_to_cefr(score: int) -> str:
    for ceiling, level in EFSET_BANDS:
        if score <= ceiling:
            return level
    return "C2"


# --- level history -----------------------------------------------------------


def load_history() -> list[dict]:
    if not LEVELS.exists():
        return []
    entries = yaml.safe_load(LEVELS.read_text()) or []
    return sorted(entries, key=lambda e: str(e.get("date")))


def save_history(entries: list[dict]) -> None:
    LEVELS.parent.mkdir(parents=True, exist_ok=True)
    header = ("# Level over time. Written by `./english level` (and /level through it).\n"
              "# source: placement = Claude's estimate, efset = a real test score.\n")
    LEVELS.write_text(header + yaml.safe_dump(entries, sort_keys=False, allow_unicode=True))


def current_level() -> dict | None:
    """Latest entry, preferring a real test over an estimate on the same day."""
    entries = load_history()
    if not entries:
        return None
    last_day = str(entries[-1]["date"])
    same_day = [e for e in entries if str(e["date"]) == last_day]
    return next((e for e in same_day if e.get("source") == "efset"), same_day[-1])


# --- writing -----------------------------------------------------------------


def error_rows() -> list[tuple[date, str]]:
    """(date, grammar point) for every logged error."""
    if not ERRORS.exists():
        return []
    rows = []
    for line in ERRORS.read_text().splitlines():
        m = ROW_RE.match(line)
        if m:
            rows.append((date.fromisoformat(m.group(1)), m.group(2)))
    return rows


def journal_words() -> dict[date, int]:
    words = {}
    if JOURNAL.is_dir():
        for path in JOURNAL.glob("????-??-??.md"):
            try:
                day = date.fromisoformat(path.stem)
            except ValueError:
                continue
            words[day] = body_words(path.read_text())
    return words


def errors_per_100_by_month() -> list[dict]:
    """Monthly error rate. Watch the trend, not the number: harder writing
    raises it, which is fine."""
    words = defaultdict(int)
    for day, n in journal_words().items():
        words[day.strftime("%Y-%m")] += n
    errors = Counter(day.strftime("%Y-%m") for day, _ in error_rows())
    return [
        {"month": m, "words": words[m], "errors": errors[m],
         "rate": round(100 * errors[m] / words[m], 1)}
        for m in sorted(words) if words[m] >= 100
    ]


def top_error_points(days: int = 60, n: int = 6) -> list[tuple[str, int]]:
    since = date.today() - timedelta(days=days)
    return Counter(p for d, p in error_rows() if d >= since).most_common(n)


# --- anki --------------------------------------------------------------------


def anki_stats(days: int = 30) -> dict:
    """Retention per topic over the last `days`, and how much of the deck is
    learned. Plain sqlite on a snapshot, like status.revlog, so Anki can stay
    open and a library mismatch can't hide the numbers."""
    out = {"retention": None, "reviews": 0, "by_topic": [], "learned": 0, "total": 0,
           "error": None}
    since_ms = int((time.time() - days * 86400) * 1000)
    try:
        with snapshot() as copy:
            con = sqlite3.connect(copy)
            try:
                decks = {
                    did: name.split("\x1f")
                    for did, name in con.execute("select id, name from decks")
                }
                ours = {did: parts for did, parts in decks.items() if parts[0] in (DECK_PREFIX, LEGACY_PREFIX)}
                if not ours:
                    out["error"] = "deck not imported yet"
                    return out
                marks = ",".join("?" * len(ours))
                ids = list(ours)
                out["total"], out["learned"] = con.execute(
                    f"select count(), sum(type != 0) from cards where did in ({marks})", ids
                ).fetchone()
                out["learned"] = out["learned"] or 0
                # type 1 = a review of a learned card; ease 1 = "Again" (a lapse).
                rows = con.execute(
                    f"select c.did, r.ease from revlog r join cards c on c.id = r.cid "
                    f"where r.id >= ? and r.type = 1 and c.did in ({marks})",
                    [since_ms, *ids],
                ).fetchall()
            finally:
                con.close()
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out

    passed, total = Counter(), Counter()
    for did, ease in rows:
        topic = ours[did][1] if len(ours[did]) > 1 else DECK_PREFIX
        total[topic] += 1
        passed[topic] += ease > 1
    out["reviews"] = sum(total.values())
    if out["reviews"]:
        out["retention"] = round(100 * sum(passed.values()) / out["reviews"], 1)
    out["by_topic"] = sorted(
        ({"topic": t, "retention": round(100 * passed[t] / total[t], 1), "reviews": total[t]}
         for t in total),
        key=lambda r: r["retention"],
    )
    return out


def level_value(level: str) -> int:
    """CEFR as a number for charts: A1=1 … C2=6."""
    return CEFR.index(level) + 1
