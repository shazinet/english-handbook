#!/usr/bin/env python3
"""The learning path: one unit per grammar or vocab topic, four lessons each.

Like a course path, but ordered by evidence rather than by the book: units you
have finished stay where you finished them, and the rest are ranked by how
often their point shows up in me/errors.md lately, then by level. The path
therefore leads to the same place /journal's target choice does.

Once a unit becomes current it stays current until its four lessons are done
(the caller keeps it in `pinned`), so a day's new errors can reorder what comes
after it but never swap out the unit you're halfway through.

Each lesson is ticked from evidence that already exists, never from a
"lesson done" button:

    cards     a day's batch of the topic's cards studied in Anki (deck.new_per_day,
              or all of them if the topic is smaller); `./english deck` puts
              the current unit's new cards first, so the daily session brings them
    drill     a /drill on this point in me/activity.log
    write     a /journal entry targeted at this point (.prompts.log), checked
    mistakes  a /mistakes round on this point, or none of its mistakes open

Finishing all four opens the unit's chest. Stars go further: ★ the four
lessons, ★★ 85% retention on the topic's cards, ★★★ no error on the point in
30 days and 80% of its cards mature.

Locks are only for show. Every activity can be run at any time; the path just
says what's next.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, timedelta

from paths import level_index

RANK_DAYS = 60          # errors this recent decide the order of unfinished units
STAR2_RETENTION = 85
STAR3_CLEAN_DAYS = 30
STAR3_MATURE = 0.8
UPCOMING = 3            # locked units shown after the current one

LESSONS = (
    # id, name, icon, how to do it ({point} is filled in)
    ("cards", "Learn the cards", "cards", "Anki: your daily session"),
    ("drill", "Conversation drill", "chat", '/drill "{point}"'),
    ("write", "Write about it", "pen", '/journal "{point}", then /check'),
    ("mistakes", "Fix your mistakes", "repeat", '/mistakes "{point}"'),
)


def next_step(today: dict, route: dict) -> dict:
    """The one thing to do next. The daily loop comes first (reps, then the
    journal, then /check), because a day only counts when all three are done;
    after that, the path's next lesson."""
    if not today["anki_done"]:
        due = today["due"]
        return {"kind": "loop", "text": f"Clear your Anki reviews ({due} due)" if due else
                "Do your Anki reviews", "command": "Anki"}
    if not today["journal_done"]:
        return {"kind": "loop", "text": "Get today's prompt, then write your entry or speak it",
                "command": "/journal, then write below it or run ./english speak"}
    if not today["checked"]:
        return {"kind": "loop", "text": "Correct today's entry", "command": "/check"}
    lesson = route["next_lesson"]
    if lesson:
        text = f"Unit {route['current']['number']} · {lesson['name']}"
        if lesson["detail"]:
            text += f" ({lesson['detail']})"
        return {"kind": "lesson", "text": text, "command": lesson["how"]}
    return {"kind": "free", "text": "Today's loop and the path are done: pick anything to practise",
            "command": "/practice"}


def matches(point: str, target: str) -> bool:
    """Does a free-text .prompts.log target name this point? Older lines say
    "conditionals & hypotheticals (6B + 5B)", newer ones start with the point."""
    t, p = target.lower(), point.lower()
    if p in t:
        return True
    code, _, name = point.partition(" ")
    if code == "00":
        return name.lower() in t
    return bool(re.search(rf"(?<![\w/]){re.escape(code)}(?![\w])", target))


def build(today: date, lib: dict, anki_topics: dict, retention: dict, errors: list[dict],
          prompts: list[dict], checked_days: set[str], activities: list[dict],
          mistakes: dict, first_seen: dict, batch: int, pinned: str | None = None) -> dict:
    """lib: dashboard.library(); anki_topics: progress.topic_cards()["topics"];
    first_seen: topic_cards()["first_seen"]; batch: the profile's new cards a day;
    retention: point → {retention, reviews}; errors: progress.error_details();
    prompts: dashboard.prompt_log(); checked_days: dates whose entry has the
    /check marker; activities: activity.read(); mistakes: mistakes.state();
    pinned: the point that was current last time, kept until it's finished."""
    since_rank = (today - timedelta(days=RANK_DAYS)).isoformat()
    since_clean = (today - timedelta(days=STAR3_CLEAN_DAYS)).isoformat()
    recent = Counter(e["point"] for e in errors if e["date"] >= since_rank)
    last_error = {}
    for e in errors:
        last_error[e["point"]] = max(last_error.get(e["point"], ""), e["date"])

    units = []
    for order, (point, row) in enumerate(lib.items()):
        if not row["in_deck"]:
            continue
        anki = anki_topics.get(point)
        total = sum(anki[k] for k in ("new", "learning", "young", "mature")) if anki else 0
        done: dict[str, str | bool] = {}   # lesson id → date done, or True when undated
        seen = first_seen.get(point, [])
        need = min(batch, total)
        if total and len(seen) >= need:
            done["cards"] = seen[need - 1]
        elif anki and total and not anki["new"]:
            done["cards"] = True       # studied before the review log goes back
        cards_detail = (f"{min(len(seen), need)} of {need} learned · {anki['new']} new left"
                        if anki and total else "not in Anki yet: run ./english deck")
        drills = [a["date"] for a in activities if a["kind"] == "drill" and a["point"] == point]
        if drills:
            done["drill"] = drills[0]
        writes = [p["date"] for p in prompts if matches(point, p["target"]) and p["date"] in checked_days]
        if writes:
            done["write"] = writes[0]
        rounds = [a["date"] for a in activities if a["kind"] == "mistakes" and a["point"] == point]
        if rounds:
            done["mistakes"] = rounds[0]
        elif not mistakes["by_point"].get(point, {}).get("open"):
            done["mistakes"] = True

        dated = [v for v in done.values() if isinstance(v, str)]
        complete = len(done) == len(LESSONS)
        r = retention.get(point) or {}
        stars = 0
        if complete:
            stars = 1
            if (r.get("retention") or 0) >= STAR2_RETENTION:
                stars = 2
                mature_share = anki["mature"] / total if total else 0
                if last_error.get(point, "") < since_clean and mature_share >= STAR3_MATURE:
                    stars = 3
        units.append({
            "point": point, "level": row["level"] or "own", "kind": row["kind"],
            "file_order": order, "errors_recent": recent[point],
            "lessons_done": len(done), "lessons_total": len(LESSONS),
            "complete": complete,
            # the chest opens on the day of the last dated lesson
            "completed_on": max(dated) if complete and dated else None,
            "stars": stars, "retention_30": r.get("retention"),
            "lessons": [{"id": lid, "name": name, "icon": icon, "how": how.format(point=point),
                         "detail": cards_detail if lid == "cards" else None,
                         "done": lid in done,
                         "done_on": done[lid] if isinstance(done.get(lid), str) else None}
                        for lid, name, icon, how in LESSONS],
        })

    finished = sorted((u for u in units if u["complete"]),
                      key=lambda u: (u["completed_on"] or "", u["file_order"]))
    ahead = sorted((u for u in units if not u["complete"]),
                   key=lambda u: (-u["errors_recent"], -u["lessons_done"],
                                  level_index(u["level"]), u["file_order"]))
    ahead.sort(key=lambda u: u["point"] != pinned)   # stable: the rest keep their rank
    ordered = finished + ahead
    for i, u in enumerate(ordered, 1):
        u["number"] = i
        u["state"] = "done" if u["complete"] else "current" if u is (ahead[0] if ahead else None) else "locked"

    current = ahead[0] if ahead else None
    next_lesson = next((l for l in current["lessons"] if not l["done"]), None) if current else None
    lessons_by_date = Counter(l["done_on"] for u in units for l in u["lessons"] if l["done_on"])
    return {
        "units": ordered,
        "current": current,
        "next_lesson": next_lesson,
        "upcoming": ahead[1:1 + UPCOMING],
        "units_done": len(finished),
        "units_total": len(ordered),
        "stars": sum(u["stars"] for u in ordered),
        "stars_total": 3 * len(ordered),
        "chests_by_date": dict(Counter(u["completed_on"] for u in finished if u["completed_on"])),
        "lessons_by_date": dict(lessons_by_date),
    }
