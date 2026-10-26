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

import math
import re
import sqlite3
import time
from collections import Counter, defaultdict
from datetime import date, timedelta

import yaml

from ankidb import DECK_PREFIX, LEGACY_PREFIX, snapshot
from lexicon import text_profile
from paths import CEFR, ERRORS, JOURNAL, LEVELS, content_files
from status import body_words, entry_text

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


def error_details() -> list[dict]:
    """Every logged error with its columns: date, point, wrong, right, why.

    Carries the learner's own sentences, so only the private dashboard may use
    it. Anything shareable (report.py) stays on error_rows.
    """
    if not ERRORS.exists():
        return []
    out = []
    for line in ERRORS.read_text().splitlines():
        if not ROW_RE.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        out.append({
            "date": cells[0], "point": cells[1],
            "wrong": cells[2].strip('"'), "right": cells[3].strip('"'),
            "why": " | ".join(cells[4:]).strip(),
        })
    return out


def journal_texts() -> dict[date, str]:
    texts = {}
    if JOURNAL.is_dir():
        for path in JOURNAL.glob("????-??-??.md"):
            try:
                day = date.fromisoformat(path.stem)
            except ValueError:
                continue
            texts[day] = entry_text(path.read_text())
    return texts


SPOKEN_RE = re.compile(r"<!-- spoken: (\d{4}-\d{2}-\d{2})T([\d:]+) · (\d+)m(\d+)s · (\d+) words · "
                       r"(\d+) wpm · (\d+) pauses · (\d+) fillers")


def speaking_sessions() -> list[dict]:
    """Every `./english speak` recording, from the markers it leaves in the journal:
    date, time, seconds, words, words per minute, and long pauses and fillers per minute."""
    out = []
    if JOURNAL.is_dir():
        for path in sorted(JOURNAL.glob("????-??-??.md")):
            for m in SPOKEN_RE.finditer(path.read_text()):
                secs = int(m[3]) * 60 + int(m[4])
                per_min = 60 / max(secs, 1)
                out.append({"date": m[1], "time": m[2], "seconds": secs, "words": int(m[5]),
                            "wpm": int(m[6]),
                            "pauses_per_min": round(int(m[7]) * per_min, 1),
                            "fillers_per_min": round(int(m[8]) * per_min, 1)})
    return out


def journal_words() -> dict[date, int]:
    """Words the learner wrote per entry, not counting a prompt left in."""
    return {day: body_words(text) for day, text in journal_texts().items()}


def errors_per_100_by_month() -> list[dict]:
    """Monthly error rate. Watch the trend, not the number: harder writing
    raises it, which is fine. Only errors dated on a day with a journal entry
    count: /drill logs errors too, but its words aren't in the journal."""
    words = defaultdict(int)
    entries = journal_words()
    for day, n in entries.items():
        words[day.strftime("%Y-%m")] += n
    errors = Counter(day.strftime("%Y-%m") for day, _ in error_rows() if day in entries)
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


MATURE_DAYS = 21  # Anki's own threshold for a "mature" card


def topic_cards() -> dict:
    """Card states per topic subdeck, plus reviews per local day.

    Same snapshot-and-sqlite approach as anki_stats. Due counts come from the
    anki library's deck tree when it can open the copy, as status.deck_due
    does, and are left as None when it can't.
    """
    out = {"topics": {}, "daily_reviews": {}, "error": None}
    try:
        with snapshot() as copy:
            con = sqlite3.connect(copy)
            try:
                decks = {did: name.split("\x1f") for did, name in con.execute("select id, name from decks")}
                ours = {did: p for did, p in decks.items() if p[0] in (DECK_PREFIX, LEGACY_PREFIX)}
                if not ours:
                    out["error"] = "deck not imported yet"
                    return out
                marks = ",".join("?" * len(ours))
                rows = con.execute(
                    f"select did, type, queue, ivl from cards where did in ({marks})", list(ours)
                ).fetchall()
                out["daily_reviews"] = dict(con.execute(
                    "select date(id/1000, 'unixepoch', 'localtime') as d, count() from revlog group by d"
                ).fetchall())
            finally:
                con.close()
            due = _due_by_topic(copy)
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out

    blank = {"new": 0, "learning": 0, "young": 0, "mature": 0, "suspended": 0, "due": None}
    for did, ctype, queue, ivl in rows:
        topic = ours[did][1] if len(ours[did]) > 1 else DECK_PREFIX
        t = out["topics"].setdefault(topic, dict(blank))
        if queue < 0:          # -1 suspended, -2/-3 buried
            t["suspended"] += 1
        elif ctype == 0:
            t["new"] += 1
        elif ctype in (1, 3):  # learning, relearning
            t["learning"] += 1
        elif ivl >= MATURE_DAYS:
            t["mature"] += 1
        else:
            t["young"] += 1
    for topic, n in (due or {}).items():
        out["topics"].setdefault(topic, dict(blank))["due"] = n
    return out


def _due_by_topic(copy) -> dict[str, int] | None:
    try:
        from anki.collection import Collection

        col = Collection(str(copy))
        try:
            for node in col.sched.deck_due_tree().children:
                if node.name in (DECK_PREFIX, LEGACY_PREFIX):
                    return {c.name: c.new_count + c.learn_count + c.review_count for c in node.children}
        finally:
            col.close()
    except Exception:  # library/collection version mismatch
        return None
    return {}


# --- level estimate from writing ---------------------------------------------
#
# A rough CEFR reading of the journal, for between /level placements. It is NOT
# a test: the anchors below are a judgement call about how /check counts errors
# (genuine errors only, no typos, no style notes), not a published scale.
# A recorded /level placement or EF SET score always outranks it.

# errors per 100 words → CEFR position (A1=1 … C2=6), interpolated on a log scale
ACCURACY_ANCHORS = ((14.0, 1.0), (10.0, 2.0), (7.0, 3.0), (4.5, 4.0), (2.5, 5.0), (1.0, 6.0))
# mean words per sentence → CEFR position, interpolated linearly
LENGTH_ANCHORS = ((6.0, 1.0), (9.0, 2.0), (12.0, 3.0), (15.0, 4.0), (18.0, 5.0), (21.0, 6.0))
ACCURACY_WEIGHT = 0.75  # accuracy is the stronger signal; long sentences can be run-ons
MIN_WORDS = 300
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _interp(x: float, anchors, log=False) -> float:
    f = math.log if log else (lambda v: v)
    pts = sorted(anchors, key=lambda a: a[0])
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            t = (f(x) - f(x0)) / (f(x1) - f(x0))
            return y0 + t * (y1 - y0)
    return pts[-1][1]


def band(value: float) -> str:
    return CEFR[min(len(CEFR), max(1, round(value))) - 1]


def band_label(value: float) -> str:
    """"B1", or "B1–B2" when the value sits in the middle third between two bands."""
    lo = min(len(CEFR), max(1, math.floor(value)))
    frac = value - lo
    if lo == len(CEFR) or frac < 0.35:
        return CEFR[lo - 1]
    if frac > 0.65:
        return CEFR[lo]
    return f"{CEFR[lo - 1]}–{CEFR[lo]}"


def sentence_lengths(text: str) -> list[int]:
    out = []
    for line in text.splitlines():
        for s in SENTENCE_END.split(line.lstrip("-*> ").strip()):
            n = len(s.split())
            if n >= 3:  # skip fragments like "Thanks." or list labels
                out.append(n)
    return out


def _estimate(days: list[date], texts: dict[date, str], errors: Counter) -> dict | None:
    words = sum(body_words(texts[d]) for d in days)
    if words < MIN_WORDS:
        return None
    n_err = sum(errors[d] for d in days)
    rate = 100 * n_err / words
    lengths = [n for d in days for n in sentence_lengths(texts[d])]
    mls = sum(lengths) / len(lengths) if lengths else None
    acc = _interp(max(rate, 0.1), ACCURACY_ANCHORS, log=True)
    cx = _interp(mls, LENGTH_ANCHORS) if mls else None
    value = acc if cx is None else ACCURACY_WEIGHT * acc + (1 - ACCURACY_WEIGHT) * cx
    return {"value": round(value, 2), "band": band(value), "label": band_label(value), "words": words, "errors": n_err,
            "rate": round(rate, 1), "accuracy_value": round(acc, 2), "accuracy_band": band(acc),
            "sentence_length": round(mls, 1) if mls else None,
            "length_value": round(cx, 2) if cx else None, "length_band": band(cx) if cx else None,
            "entries": len(days)}


def writing_level(days: int = 30) -> dict:
    """Estimate over the last `days` days of entries (widened to 90 when there
    is too little writing), plus one estimate per month for the trend, and three
    diagnostics that don't move the number: how many recent errors are in
    B1-or-lower topics, Anki retention by topic level, and the share of distinct
    words above B1 (when the word lists are fetched — see lexicon.py).

    The vocabulary share stays a diagnostic on purpose: there is no published
    scale mapping it to CEFR for one learner's journal, and an invented anchor
    would move the estimate on guesswork."""
    texts = journal_texts()
    errors = Counter(d for d, _ in error_rows() if d in texts)
    today = date.today()
    out = {"current": None, "window_days": days, "monthly": [], "foundation_share": None,
           "retention_by_level": [], "lexical": None, "recorded": current_level()}

    for window in (days, 90):
        recent = sorted(d for d in texts if d >= today - timedelta(days=window))
        est = _estimate(recent, texts, errors)
        if est:
            out["current"], out["window_days"] = est, window
            break

    if out["current"]:
        w = out["current"]["value"]
        n = out["current"]["words"]
        spread = 0.75 if n < 600 else 0.5 if n < 1500 else 0.35
        out["current"].update(low=round(max(1, w - spread), 2), high=round(min(6, w + spread), 2),
                              confidence="low" if n < 600 else "medium" if n < 1500 else "good")

    by_month = defaultdict(list)
    for d in texts:
        by_month[d.strftime("%Y-%m")].append(d)
    for month in sorted(by_month):
        est = _estimate(sorted(by_month[month]), texts, errors)
        if est:
            out["monthly"].append({"month": month, **est})

    # diagnostics
    levels = {}
    for _, data, personal in content_files():
        if not personal:
            levels[data["point"]] = data.get("level")
    since = today - timedelta(days=out["window_days"])
    out["lexical"] = text_profile([t for d, t in texts.items() if d >= since])
    leveled = [levels[p] for d, p in error_rows() if d >= since and d in texts and levels.get(p)]
    if leveled:
        basic = sum(1 for lv in leveled if CEFR.index(lv) <= CEFR.index("B1"))
        out["foundation_share"] = round(basic / len(leveled), 2)
        out["leveled_errors"] = len(leveled)
    passed, total = Counter(), Counter()
    for r in anki_stats(30)["by_topic"]:
        lv = levels.get(r["topic"])
        if lv:
            total[lv] += r["reviews"]
            passed[lv] += r["retention"] * r["reviews"] / 100
    out["retention_by_level"] = [
        {"level": lv, "retention": round(100 * passed[lv] / total[lv], 1), "reviews": total[lv]}
        for lv in CEFR if total[lv]
    ]
    return out
