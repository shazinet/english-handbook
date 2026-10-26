#!/usr/bin/env python3
"""XP, practice level, weekly goals and badges for the dashboard.

Everything here is derived from data the practice loop already produces
(Anki's review log, the journal, `./english speak` markers, errors.md), plus
me/activity.log for the sessions that leave no other trace (activity.py).
dashboard.py passes it the pieces it has already gathered; this module only
scores them.

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
      practice sessions, daily quests and path chests: see ACTIVITIES, QUESTS

None of it decides whether a day is done; that stays status.py's three parts.

Badges have three tiers each. A badge's rule text is shown on the dashboard,
so it's written here once, next to its thresholds.
"""

from __future__ import annotations

import random
from collections import Counter
from datetime import date, timedelta

from status import day_complete

XP_REVIEW = 1
XP_ENTRY = 20
XP_PER_10_WORDS = 1
XP_CHECK = 10
XP_SPEAK_MINUTE = 10
XP_COMPLETE_DAY = 30
XP_CALL, XP_CALL_MINUTE = 20, 10
XP_ROLEPLAY, XP_ROLEPLAY_WON = 30, 20
XP_DRILL, XP_DRILL_CORRECT = 30, 2
XP_MISTAKE_FIXED, XP_MISTAKES_PERFECT = 3, 10
XP_STORY, XP_STORY_RETELL = 25, 10
XP_LISTEN_MINUTE, XP_LISTEN_CAP = 1, 60
XP_QUEST, XP_QUEST_CHEST = 10, 20
XP_UNIT_CHEST = 50

TIERS = ("Bronze", "Silver", "Gold")

# The same table, for the dashboard's "How XP works" card.
XP_RULES = [
    {"action": "Anki review", "xp": XP_REVIEW, "per": "each"},
    {"action": "Journal entry with real writing", "xp": XP_ENTRY, "per": "entry"},
    {"action": "Words in that entry", "xp": XP_PER_10_WORDS, "per": "10 words"},
    {"action": "/check on that entry", "xp": XP_CHECK, "per": "entry"},
    {"action": "Speaking with ./english speak", "xp": XP_SPEAK_MINUTE, "per": "minute"},
    {"action": "Complete day (all three parts)", "xp": XP_COMPLETE_DAY, "per": "day"},
    {"action": "Video call (/call)", "xp": XP_CALL, "per": f"call, +{XP_CALL_MINUTE} a minute"},
    {"action": "Roleplay (/roleplay)", "xp": XP_ROLEPLAY, "per": f"session, +{XP_ROLEPLAY_WON} if you win"},
    {"action": "Drill (/drill)", "xp": XP_DRILL, "per": f"session, +{XP_DRILL_CORRECT} per correct form"},
    {"action": "Mistake fixed (/mistakes)", "xp": XP_MISTAKE_FIXED, "per": f"each, +{XP_MISTAKES_PERFECT} for a perfect round"},
    {"action": "Story (/story)", "xp": XP_STORY, "per": f"story, +{XP_STORY_RETELL} for the retell"},
    {"action": "Listening (./english listen)", "xp": XP_LISTEN_MINUTE, "per": f"minute, up to {XP_LISTEN_CAP} a day"},
    {"action": "Daily quest", "xp": XP_QUEST, "per": f"quest, +{XP_QUEST_CHEST} for all three"},
    {"action": "Path unit finished (chest)", "xp": XP_UNIT_CHEST, "per": "unit"},
]

# The practice hub. id, name, group, command, icon, XP label, what it is.
ACTIVITIES = [
    ("call", "Video call", "Conversation", "/call", "video",
     f"+{XP_CALL} XP, +{XP_CALL_MINUTE}/min", "Talk out loud with a character: Claude speaks, you answer by voice"),
    ("roleplay", "Roleplay", "Conversation", "/roleplay", "chat",
     f"+{XP_ROLEPLAY} XP, +{XP_ROLEPLAY_WON} if you win", "A real situation from your life, with a goal to win"),
    ("drill", "Drill", "Conversation", "/drill", "target",
     f"+{XP_DRILL} XP, +{XP_DRILL_CORRECT} per correct form", "Eight to ten turns that pull out one grammar point"),
    ("mistakes", "Mistakes", "Skill practice", "/mistakes", "repeat",
     f"+{XP_MISTAKE_FIXED} XP per fix", "Re-correct your own logged errors; two good days resolves one"),
    ("words", "Words", "Skill practice", "Anki", "cards",
     f"+{XP_REVIEW} XP per review", "Your cloze cards, spaced by FSRS"),
    ("story", "Story", "Skill practice", "/story", "book",
     f"+{XP_STORY} XP, +{XP_STORY_RETELL} retell", "A short story read aloud, questions, then retell it"),
    ("speak", "Speak", "Skill practice", "./english speak", "mic",
     f"+{XP_SPEAK_MINUTE} XP per minute", "Talk about your day; the transcript becomes your entry"),
    ("radio", "Radio", "Skill practice", "./english listen MINUTES", "headphones",
     f"+{XP_LISTEN_MINUTE} XP per minute", "Log podcasts and series from your input plan"),
]

# Daily quests: id, text, target, unit. Three a day, picked from the date.
QUESTS = [
    ("anki", "Clear today's Anki reviews", 1, ""),
    ("xp", "Earn 80 XP", 80, "XP"),
    ("words", "Write 150 words", 150, "words"),
    ("speak", "Speak for 3 minutes", 3, "min"),
    ("mistakes", "Fix 5 mistakes", 5, "fixed"),
    ("lesson", "Finish a lesson on the path", 1, ""),
    ("listen", "Listen for 15 minutes", 15, "min"),
    ("talk", "Do a call or a roleplay", 1, ""),
]
QUESTS_PER_DAY = 3

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
    ("speak", "Speak for 10 minutes", "min", 10, "Minutes spoken with ./english speak and /call"),
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
        "practice": 0,
        "bonus": XP_COMPLETE_DAY if complete else 0,
    }
    out["total"] = sum(out.values())
    return out


def session_xp(a: dict) -> int:
    """XP for one activity.log line. Mistakes fixed are scored from
    mistakes.log instead (each fix once), so only the perfect-round bonus is here."""
    kind = a["kind"]
    if kind == "call":
        return XP_CALL + XP_CALL_MINUTE * a.get("minutes", 0)
    if kind == "roleplay":
        return XP_ROLEPLAY + (XP_ROLEPLAY_WON if a.get("goal") else 0)
    if kind == "drill":
        return XP_DRILL + XP_DRILL_CORRECT * a.get("correct", 0)
    if kind == "mistakes":
        items = a.get("items", 0)
        return XP_MISTAKES_PERFECT if items and a.get("correct", 0) >= items else 0
    if kind == "story":
        return XP_STORY + (XP_STORY_RETELL if a.get("goal") else 0)
    return 0   # listening is capped per day, so it's scored in practice_xp


def practice_xp(sessions: list[dict], fixed: int) -> int:
    listen = sum(a.get("minutes", 0) for a in sessions if a["kind"] == "listen")
    return (sum(session_xp(a) for a in sessions) + XP_MISTAKE_FIXED * fixed
            + min(XP_LISTEN_CAP, XP_LISTEN_MINUTE * listen))


def quests_for(day: date, available: set[str]) -> list[tuple]:
    """The day's three quests: the same every time the day is scored, and only
    ones that can be done (no "fix 5 mistakes" with fewer than 5 open)."""
    pool = [q for q in QUESTS if q[0] in available]
    return sorted(random.Random(day.toordinal()).sample(pool, min(QUESTS_PER_DAY, len(pool))),
                  key=pool.index)


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
     "Speak for {n} minutes with ./english speak and /call"),
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
    ("talk", "Conversationalist", "chat", "sessions", (5, 20, 60), True,
     "Hold {n} conversations with /call or /roleplay"),
    ("fixer", "Fixer", "repeat", "mistakes", (10, 50, 150), True,
     "Resolve {n} of your mistakes (fixed on two different days) with /mistakes"),
    ("story", "Storyteller", "book", "stories", (3, 10, 30), True,
     "Finish {n} stories with /story"),
    ("ears", "All ears", "headphones", "hours", (5, 25, 100), True,
     "Log {n} hours of listening with ./english listen"),
    ("path", "Pathfinder", "map", "units", (1, 5, 15), True,
     "Finish {n} units on the path"),
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
    free_entries, recorded_level, activities (activity.read()), mistakes
    (mistakes.state()), path (path.build())."""
    today: date = ctx["today"]
    status, min_words, daily = ctx["status"], ctx["min_words"], ctx["daily"]
    entries = {e["date"]: e for e in ctx["entries"]}
    talks, sessions = ctx["talks"], ctx["activities"]
    mist, route = ctx["mistakes"], ctx["path"]
    review_days = set(daily)

    speak_secs: Counter = Counter()
    for t in talks:
        speak_secs[t["date"]] += t["seconds"]
    for a in sessions:
        if a["kind"] == "call":   # a call's answers are spoken too
            speak_secs[a["date"]] += 60 * a.get("minutes", 0)
    by_day: dict[str, list[dict]] = {}
    for a in sessions:
        by_day.setdefault(a["date"], []).append(a)
    fixed = mist["fixed_by_date"]

    def available(day: str) -> set[str]:
        """Quests that could be done on `day`, judged from how things stood when
        it began, so the day's three never change as it goes on."""
        out = {"anki", "xp", "words", "speak", "listen", "talk"}
        open_then = sum(1 for it in mist["items"] if it["date"] < day
                        and not (it["resolved_on"] and it["resolved_on"] < day))
        if open_then >= 5:
            out.add("mistakes")
        if route["current"]:
            out.add("lesson")
        return out

    starts = [date.fromisoformat(d) for d in
              list(daily) + list(entries) + list(speak_secs) + list(by_day) + list(fixed)]
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
        did = by_day.get(iso, [])
        xp["practice"] = practice_xp(did, fixed.get(iso, 0))
        anki_done = status["anki_done"] if d == today else iso in review_days
        progress = {
            "anki": int(anki_done),
            "xp": sum(xp[k] for k in ("anki", "writing", "speaking", "practice", "bonus")),
            "words": e.get("words", 0),
            "speak": round(speak_secs.get(iso, 0) / 60, 1),
            "mistakes": fixed.get(iso, 0),
            "lesson": route["lessons_by_date"].get(iso, 0),
            "listen": sum(a.get("minutes", 0) for a in did if a["kind"] == "listen"),
            "talk": sum(1 for a in did if a["kind"] in ("call", "roleplay")),
        }
        quests = [{"id": qid, "name": name, "target": target, "unit": unit,
                   "value": progress[qid], "progress": round(min(1.0, progress[qid] / target), 3),
                   "done": progress[qid] >= target}
                  for qid, name, target, unit in quests_for(d, available(iso))]
        quests_done = sum(q["done"] for q in quests)
        xp["bonus"] += (XP_QUEST * quests_done
                        + (XP_QUEST_CHEST if quests and quests_done == len(quests) else 0)
                        + XP_UNIT_CHEST * route["chests_by_date"].get(iso, 0))
        xp["total"] = sum(xp[k] for k in ("anki", "writing", "speaking", "practice", "bonus"))
        days.append({"date": iso, "complete": complete, **xp, "quests_done": quests_done,
                     "words": e.get("words", 0), "speak_seconds": speak_secs.get(iso, 0)})
        run = run + 1 if complete else 0
        best = max(best, run)
        d += timedelta(days=1)

    today_quests = quests if days else []
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
    open_quests = [q for q in today_quests if not q["done"]]
    left += XP_QUEST * len(open_quests) + (XP_QUEST_CHEST if open_quests else 0)

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
    counts = Counter(a["kind"] for a in sessions)
    values = {
        "streak": best,
        "reviews": sum(daily.values()),
        "mature": ctx["mature"],
        "retention": ctx["retention_30"] if (ctx["reviews_30"] or 0) >= 200 else None,
        "words": sum(e["words"] for e in ctx["entries"]),
        "checked": len(checked_entries),
        "clean": sum(1 for e in checked_entries if e["words"] >= 100 and not e["errors"]),
        "accuracy": min(month_rates) if month_rates else None,
        "speak": round(sum(speak_secs.values()) / 60, 1),
        "pace": p["wpm"],
        "fillers": p["fillers"],
        "mined": ctx["own_cards"],
        "free": ctx["free_entries"],
        "level": CEFR.index(rec) + 1 if rec in CEFR else None,
        "talk": counts["call"] + counts["roleplay"],
        "fixer": mist["resolved"],
        "story": counts["story"],
        "ears": round(sum(a.get("minutes", 0) for a in sessions if a["kind"] == "listen") / 60, 1),
        "path": route["units_done"],
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
        "quests": today_quests,
        "quests_done": sum(q["done"] for q in today_quests),
        "activities": hub(ctx, by_day.get(today.isoformat(), []), speak_secs.get(today.isoformat(), 0)),
    }


def hub(ctx: dict, today_sessions: list[dict], today_speak: int) -> list[dict]:
    """The practice menu: each activity with a count to pull you in and
    whether you've done it today."""
    status, mist = ctx["status"], ctx["mistakes"]
    kinds = {a["kind"] for a in today_sessions}
    counts = {
        "mistakes": (mist["open"], "open"),
        "words": (status["due"], "due") if status["due"] is not None else (None, ""),
    }
    done = {
        "call": "call" in kinds, "roleplay": "roleplay" in kinds, "drill": "drill" in kinds,
        "mistakes": "mistakes" in kinds or bool(mist["fixed_by_date"].get(ctx["today"].isoformat())),
        "words": bool(status["anki_done"]), "story": "story" in kinds,
        "speak": today_speak > 0, "radio": "listen" in kinds,
    }
    return [{"id": aid, "name": name, "group": group, "command": command, "icon": icon,
             "xp_label": xp_label, "blurb": blurb,
             "count": counts.get(aid, (None, ""))[0], "count_label": counts.get(aid, (None, ""))[1],
             "done_today": done[aid]}
            for aid, name, group, command, icon, xp_label, blurb in ACTIVITIES]
