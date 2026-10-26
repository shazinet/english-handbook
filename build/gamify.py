#!/usr/bin/env python3
"""XP, practice level, weekly goals and badges for the dashboard.

Everything here is derived from data the practice loop already produces
(Anki's review log, the journal, `./english speak` markers, errors.md), so
nothing asks the learner to log anything extra. dashboard.py passes it the
pieces it has already gathered; this module only scores them.

The rules are deliberately weighted toward the loop, not toward Anki alone:
a review is worth 1 XP, but a written-and-checked entry on a complete day is
worth 60 or more, so grinding cards can't substitute for writing and speaking.

    XP per day
      1   per Anki review
      20  for a journal entry with real writing (status.py's minimum words)
      +1  per 10 words in it
      10  for running /check on it
      10  per minute spoken with ./english speak
      30  bonus when the day is complete (all three parts of the loop)

Badges have three tiers each. A badge's rule text is shown on the dashboard,
so it's written here once, next to its thresholds.
"""

from __future__ import annotations

from datetime import date, timedelta

from status import day_complete

XP_REVIEW = 1
XP_ENTRY = 20
XP_PER_10_WORDS = 1
XP_CHECK = 10
XP_SPEAK_MINUTE = 10
XP_COMPLETE_DAY = 30

TIERS = ("Bronze", "Silver", "Gold")

# The same table, for the dashboard's "How XP works" card.
XP_RULES = [
    {"action": "Anki review", "xp": XP_REVIEW, "per": "each"},
    {"action": "Journal entry with real writing", "xp": XP_ENTRY, "per": "entry"},
    {"action": "Words in that entry", "xp": XP_PER_10_WORDS, "per": "10 words"},
    {"action": "/check on that entry", "xp": XP_CHECK, "per": "entry"},
    {"action": "Speaking with ./english speak", "xp": XP_SPEAK_MINUTE, "per": "minute"},
    {"action": "Complete day (all three parts)", "xp": XP_COMPLETE_DAY, "per": "day"},
]

# Reference speaking rates (words per minute, timed from first word to last).
# Relaxed native conversation is commonly cited at about 150 words a minute;
# 120–180 covers most of it. The pace goal is where a learner's speech stops
# sounding halting to a listener.
NATIVE_WPM = (120, 180)
PACE_GOAL = 120
PACE_MIN_SECONDS = 60     # shorter recordings are too noisy to judge pace
PACE_RECORDINGS = 3       # pace is pooled over the last few, not the best one

WEEKLY_GOALS = [
    # id, name, unit, target, rule
    ("days", "Complete 5 days", "days", 5, "Days with Anki, a journal entry and /check all done"),
    ("words", "Write 600 words", "words", 600, "Words in this week's journal entries, spoken ones included"),
    ("speak", "Speak for 10 minutes", "min", 10, "Minutes recorded with ./english speak"),
    ("xp", "Earn 1,000 XP", "XP", 1000, "XP from every part of the loop"),
]


def level_floor(level: int) -> int:
    """XP needed to reach `level`. Each level costs a little more than the last."""
    return int(round(150 * (level - 1) ** 1.5, -1))


def level_for(xp: int) -> int:
    level = 1
    while level_floor(level + 1) <= xp:
        level += 1
    return level


def title_for(level: int) -> str:
    for floor, name in ((30, "Master"), (20, "Expert"), (15, "Adept"),
                        (10, "Practitioner"), (5, "Apprentice"), (1, "Novice")):
        if level >= floor:
            return name
    return "Novice"


def day_xp(reviews: int, words: int, checked: bool, speak_seconds: int,
           complete: bool, min_words: int) -> dict:
    writing = XP_ENTRY + XP_PER_10_WORDS * (words // 10) if words >= min_words else 0
    if checked and words >= min_words:
        writing += XP_CHECK
    out = {
        "anki": XP_REVIEW * reviews,
        "writing": writing,
        "speaking": round(XP_SPEAK_MINUTE * speak_seconds / 60),
        "bonus": XP_COMPLETE_DAY if complete else 0,
    }
    out["total"] = sum(out.values())
    return out


def pace(talks: list[dict]) -> dict:
    """Words per minute and fillers per minute, pooled over the last few
    recordings of at least a minute, so one good or bad take can't decide it."""
    long = [t for t in talks if t["seconds"] >= PACE_MIN_SECONDS][-PACE_RECORDINGS:]
    secs = sum(t["seconds"] for t in long)
    if not secs:
        return {"wpm": None, "fillers": None, "recordings": 0}
    fillers = sum(t["fillers_per_min"] * t["seconds"] / 60 for t in long)
    return {"wpm": round(60 * sum(t["words"] for t in long) / secs),
            "fillers": round(60 * fillers / secs, 1), "recordings": len(long)}


CEFR = ("A1", "A2", "B1", "B2", "C1", "C2")

# id, name, icon, unit, thresholds (Bronze, Silver, Gold), higher_is_better, rule.
# `{n}` in the rule is the next tier's threshold.
BADGES = [
    ("streak", "On a roll", "flame", "days", (3, 7, 30), True,
     "Complete every part of the loop {n} days in a row"),
    ("reviews", "Card shark", "cards", "reviews", (500, 2500, 10000), True,
     "Do {n} Anki reviews in total"),
    ("mature", "Long memory", "brain", "cards", (50, 200, 500), True,
     "Get {n} cards to mature (an interval of 21 days or more)"),
    ("retention", "Sharp recall", "target", "%", (85, 90, 95), True,
     "Pass {n}% of reviews over 30 days, with at least 200 reviews"),
    ("words", "Wordsmith", "pen", "words", (2000, 10000, 30000), True,
     "Write {n} words in your journal in total"),
    ("checked", "Self-editor", "check", "entries", (10, 30, 100), True,
     "Run /check on {n} journal entries"),
    ("clean", "Clean sheet", "star", "entries", (1, 5, 20), True,
     "Write {n} checked entries of 100+ words with zero errors"),
    ("accuracy", "Precision", "scope", "errors/100 words", (6, 4, 2), False,
     "Have a month (300+ words) at {n} errors per 100 words or fewer"),
    ("speak", "Voice", "mic", "minutes", (10, 60, 300), True,
     "Record {n} minutes with ./english speak"),
    ("pace", "Pace setter", "gauge", "words/min", (80, 100, 120), True,
     "Average {n} words a minute over your last 3 recordings of 1 minute or more"),
    ("fillers", "Smooth talker", "wave", "fillers/min", (4, 2, 1), False,
     "Keep fillers to {n} a minute over your last 3 recordings of 1 minute or more"),
    ("mined", "Error miner", "pick", "cards", (10, 30, 100), True,
     "Turn {n} of your own errors into cards with /mine"),
    ("free", "Free spirit", "feather", "entries", (3, 10, 25), True,
     "Write {n} free entries (no target structure)"),
    ("level", "Level up", "mountain", "level", (4, 5, 6), True,
     "Record a level of {n} with /level or an EF SET score"),
]


def badge(spec: tuple, value: float | None) -> dict:
    bid, name, icon, unit, thresholds, higher, rule = spec
    if value is None:
        tier = 0
    elif higher:
        tier = sum(value >= t for t in thresholds)
    else:
        tier = sum(value <= t for t in thresholds)
    nxt = thresholds[tier] if tier < len(thresholds) else None
    if nxt is None:
        progress = 1.0
    elif value is None:
        progress = 0.0
    elif higher:
        progress = max(0.0, min(1.0, value / nxt))
    else:
        progress = max(0.0, min(1.0, nxt / value)) if value else 1.0

    def show(n):
        return CEFR[int(n) - 1] if bid == "level" else f"{n:,}"

    return {
        "id": bid, "name": name, "icon": icon, "unit": unit,
        "tier": tier, "tier_name": TIERS[tier - 1] if tier else "Locked",
        "next_tier": TIERS[tier] if nxt is not None else None,
        "value": value, "value_label": "—" if value is None else show(value),
        "target": nxt, "target_label": show(nxt) if nxt is not None else None,
        "progress": round(progress, 3),
        "rule": rule.format(n=show(nxt)) if nxt is not None else
                rule.format(n=show(thresholds[-1])) + " — every tier earned",
        "bronze": show(thresholds[0]), "silver": show(thresholds[1]), "gold": show(thresholds[2]),
        "lower_is_better": not higher,
    }


def build(ctx: dict) -> dict:
    """ctx: today, status, min_words, daily (date str → reviews), entries
    (dashboard journal rows), talks (progress.speaking_sessions), months
    (errors_per_100_by_month), mature, retention_30, reviews_30, own_cards,
    free_entries, recorded_level."""
    today: date = ctx["today"]
    status, min_words, daily = ctx["status"], ctx["min_words"], ctx["daily"]
    entries = {e["date"]: e for e in ctx["entries"]}
    talks = ctx["talks"]
    review_days = set(daily)

    speak_secs: dict[str, int] = {}
    for t in talks:
        speak_secs[t["date"]] = speak_secs.get(t["date"], 0) + t["seconds"]

    starts = [date.fromisoformat(d) for d in list(daily) + list(entries) + list(speak_secs)]
    first = min(starts) if starts else today

    # --- every day since the first activity: XP and completion ---
    days = []
    best = run = 0
    d = first
    while d <= today:
        iso = d.isoformat()
        complete = status["done"] if d == today else day_complete(d, review_days, min_words)
        e = entries.get(iso) or {}
        xp = day_xp(daily.get(iso, 0), e.get("words", 0), bool(e.get("checked")),
                    speak_secs.get(iso, 0), complete, min_words)
        days.append({"date": iso, "complete": complete, **xp,
                     "words": e.get("words", 0), "speak_seconds": speak_secs.get(iso, 0)})
        run = run + 1 if complete else 0
        best = max(best, run)
        d += timedelta(days=1)

    total = sum(x["total"] for x in days)
    level = level_for(total)
    floor, ceiling = level_floor(level), level_floor(level + 1)

    week0 = today - timedelta(days=today.weekday())
    this_week = [x for x in days if x["date"] >= week0.isoformat()]
    last_week = [x for x in days if (week0 - timedelta(days=7)).isoformat() <= x["date"] < week0.isoformat()]
    week_xp = sum(x["total"] for x in this_week)
    last_week_xp = sum(x["total"] for x in last_week)
    today_row = days[-1] if days else day_xp(0, 0, False, 0, False, min_words)

    # XP still on the table today: what finishing each missing part would add.
    left = 0
    if not status["anki_done"]:
        left += XP_REVIEW * (status["due"] or 0)
    if not status["journal_done"]:
        left += XP_ENTRY + 10
    if not status["checked"]:
        left += XP_CHECK
    if not status["done"]:
        left += XP_COMPLETE_DAY

    # --- weekly goals ---
    week_values = {
        "days": sum(x["complete"] for x in this_week),
        "words": sum(x["words"] for x in this_week),
        "speak": round(sum(x["speak_seconds"] for x in this_week) / 60, 1),
        "xp": week_xp,
    }
    goals = [{"id": gid, "name": name, "unit": unit, "target": target, "rule": rule,
              "value": week_values[gid], "progress": round(min(1.0, week_values[gid] / target), 3),
              "done": week_values[gid] >= target}
             for gid, name, unit, target, rule in WEEKLY_GOALS]

    # --- badges ---
    p = pace(talks)
    month_rates = [m["rate"] for m in ctx["months"] if m["words"] >= 300]
    checked_entries = [e for e in ctx["entries"] if e["checked"]]
    rec = ctx.get("recorded_level")
    values = {
        "streak": best,
        "reviews": sum(daily.values()),
        "mature": ctx["mature"],
        "retention": ctx["retention_30"] if (ctx["reviews_30"] or 0) >= 200 else None,
        "words": sum(e["words"] for e in ctx["entries"]),
        "checked": len(checked_entries),
        "clean": sum(1 for e in checked_entries if e["words"] >= 100 and not e["errors"]),
        "accuracy": min(month_rates) if month_rates else None,
        "speak": round(sum(t["seconds"] for t in talks) / 60, 1),
        "pace": p["wpm"],
        "fillers": p["fillers"],
        "mined": ctx["own_cards"],
        "free": ctx["free_entries"],
        "level": CEFR.index(rec) + 1 if rec in CEFR else None,
    }
    badges = [badge(spec, values[spec[0]]) for spec in BADGES]
    tiers_earned = sum(b["tier"] for b in badges)

    return {
        "xp": total, "level": level, "next_level": level + 1, "title": title_for(level),
        "level_floor": floor, "next_level_xp": ceiling,
        "xp_into_level": total - floor, "xp_for_level": ceiling - floor,
        "xp_to_next": ceiling - total,
        "today_xp": today_row["total"], "xp_left_today": left,
        "week_xp": week_xp, "last_week_xp": last_week_xp, "week_change": week_xp - last_week_xp,
        "days_left_in_week": 6 - today.weekday(),
        "streak": status["streak"], "best_streak": best,
        # before today is done, status.py's streak counts only the days behind it
        "streak_at_risk": not status["done"] and status["streak"] > 0,
        "tiers_earned": tiers_earned, "tiers_total": 3 * len(badges),
        "badges_earned": sum(1 for b in badges if b["tier"]),
        "badges_total": len(badges),
        "pace_wpm": p["wpm"], "pace_fillers": p["fillers"], "pace_recordings": p["recordings"],
        "native_low": NATIVE_WPM[0], "native_high": NATIVE_WPM[1], "pace_goal": PACE_GOAL,
        "days": days[-14:],
        "rules": XP_RULES,
        "goals": goals,
        "badges": badges,
    }
