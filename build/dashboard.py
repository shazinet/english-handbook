#!/usr/bin/env python3
"""Every number for the learner's private dashboard, in one JSON file.

    ./english dashboard          writes me/dashboard/{data,practice}.json, prints what changed
    ./english dashboard --json   the same, printed to stdout as well

/dashboard publishes the file to the learner's private claude.ai artifact, and
the loop commands refresh it as their last step. Unlike report.py this carries
the learner's own corrected sentences (wrong → right), so it must never be the
source of anything shareable. It stays in me/, and the artifact stays private.

Degrades rather than raises: with no Anki, no journal or no errors yet, the
matching fields are null or empty and everything else still fills in.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

import gamify
from build_anki import included
from paths import JOURNAL, ME, content_files, load_profile
from progress import (
    anki_stats, current_level, error_details, errors_per_100_by_month, journal_words,
    load_history, speaking_sessions, topic_cards, writing_level,
)
from status import CHECK_MARKER, compute, day_complete, load_config

OUT_DIR = ME / "dashboard"
DATA = OUT_DIR / "data.json"
ROWS = OUT_DIR / "practice.json"  # what the artifact loads
PROMPTS_LOG = JOURNAL / ".prompts.log"
HEATMAP_DAYS = 84
EXAMPLES_PER_POINT = 3
TALKS_SHOWN = 20


def library(profile: dict) -> dict[str, dict]:
    """One row per `point:`, shared and own cards combined."""
    deck = profile["deck"]
    rows: dict[str, dict] = {}
    for path, data, personal in content_files():
        point = data["point"]
        row = rows.setdefault(point, {
            "point": point, "level": None, "kind": "grammar",
            "shared": 0, "own": 0, "in_deck": False, "left_out": None,
        })
        if personal:
            row["own"] += len(data["cards"])
        else:
            row["shared"] += len(data["cards"])
            row["level"] = data.get("level")
            if "vocab" in path.parts:
                row["kind"] = "vocab"
        if included(data, personal, profile):
            row["in_deck"] = True
        elif not personal:
            row["left_out"] = "skip" if point in (deck.get("skip") or []) else "above max_level"
    for row in rows.values():
        if row["in_deck"]:
            row["left_out"] = None
    return rows


def prompt_log() -> list[dict]:
    if not PROMPTS_LOG.exists():
        return []
    out = []
    for line in PROMPTS_LOG.read_text().splitlines():
        if line.startswith("#") or "\t" not in line:
            continue
        day, target = line.split("\t", 1)
        out.append({"date": day.strip(), "target": target.strip()})
    return out


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def gather() -> dict:
    profile = load_profile()
    conf = load_config()
    today = date.today()
    status = compute(today, conf)
    min_words = conf["journal_min_words"]

    # --- anki ---
    cards = topic_cards()
    stats = anki_stats(30)
    retention = {r["topic"]: r for r in stats["by_topic"]}
    daily = cards["daily_reviews"]
    review_days = set(daily)

    # --- journal ---
    words = journal_words()
    errors = error_details()
    errors_by_day = Counter(e["date"] for e in errors)
    entries = []
    for day in sorted(words):
        text = (JOURNAL / f"{day.isoformat()}.md").read_text()
        n = words[day]
        e = errors_by_day.get(day.isoformat(), 0)
        entries.append({
            "date": day.isoformat(), "words": n, "checked": CHECK_MARKER in text,
            "errors": e, "rate": round(100 * e / n, 1) if n else None,
        })
    prompts = prompt_log()
    free = [p["date"] for p in prompts if p["target"].startswith("free")]

    # --- speaking ---
    talks = speaking_sessions()
    recent_talks = talks[-5:]
    talk_secs = sum(t["seconds"] for t in recent_talks)
    speaking = {
        "sessions": len(talks),
        "minutes": round(sum(t["seconds"] for t in talks) / 60, 1),
        # pooled rather than averaged, so a 10-second test can't swing it
        "wpm_last_5": round(60 * sum(t["words"] for t in recent_talks) / talk_secs) if talk_secs else None,
        "latest": talks[-1] if talks else None,
        "wpm_change": talks[-1]["wpm"] - talks[-2]["wpm"] if len(talks) > 1 else None,
        "recent": talks[-TALKS_SHOWN:],
    }

    # --- heatmap ---
    heat = []
    for i in range(HEATMAP_DAYS - 1, -1, -1):
        day = today - timedelta(days=i)
        path = JOURNAL / f"{day.isoformat()}.md"
        text = path.read_text() if path.exists() else ""
        heat.append({
            "date": day.isoformat(),
            "reviews": daily.get(day.isoformat(), 0),
            "wrote": words.get(day, 0) >= min_words,
            "checked": CHECK_MARKER in text,
            "complete": status["done"] if day == today else day_complete(day, review_days, min_words),
        })

    # --- errors ---
    lib = library(profile)
    known_points = set(lib)
    since14, since30 = (today - timedelta(days=14)).isoformat(), (today - timedelta(days=30)).isoformat()
    all_time = Counter(e["point"] for e in errors)
    last30 = Counter(e["point"] for e in errors if e["date"] >= since30)
    last14 = Counter(e["point"] for e in errors if e["date"] >= since14)
    ranked = [p for p, _ in (last30 or all_time).most_common(6)]
    weeks = [week_start(today) - timedelta(weeks=i) for i in range(7, -1, -1)]
    weekly = defaultdict(Counter)
    for e in errors:
        weekly[e["point"]][week_start(date.fromisoformat(e["date"])).isoformat()] += 1
    latest = sorted(errors, key=lambda e: e["date"], reverse=True)
    top_points = [{
        "point": p, "all_time": all_time[p], "last_30": last30[p], "last_14": last14[p],
        "in_deck": p in known_points,
        "weekly": [weekly[p][w.isoformat()] for w in weeks],
        "examples": [{k: e[k] for k in ("date", "wrong", "right", "why")}
                     for e in latest if e["point"] == p][:EXAMPLES_PER_POINT],
    } for p in ranked]
    gaps = sorted(({"point": p, "all_time": n, "last_30": last30[p]}
                   for p, n in all_time.items() if p not in known_points),
                  key=lambda g: -g["all_time"])

    # --- topics: library joined with Anki and errors ---
    topics = []
    for point, row in sorted(lib.items(), key=lambda kv: kv[0]):
        anki = cards["topics"].get(point)
        r = retention.get(point)
        topics.append({
            **row,
            "anki": anki,
            "retention_30": r["retention"] if r else None,
            "reviews_30": r["reviews"] if r else 0,
            "errors_all": all_time[point], "errors_30": last30[point],
        })
    totals = Counter()
    for t in cards["topics"].values():
        for k in ("new", "learning", "young", "mature", "suspended"):
            totals[k] += t[k]

    meter = writing_level()
    game = gamify.build({
        "today": today, "status": status, "min_words": min_words, "daily": daily,
        "entries": entries, "talks": talks, "months": errors_per_100_by_month(),
        "mature": totals["mature"], "retention_30": stats["retention"],
        "reviews_30": stats["reviews"], "own_cards": sum(r["own"] for r in lib.values()),
        "free_entries": len(free), "recorded_level": (meter["recorded"] or {}).get("overall"),
    })

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "date": today.isoformat(),
        "profile": {
            "name": profile.get("name") or "",
            "level": profile.get("level"),
            "max_level": profile["deck"].get("max_level"),
            "new_per_day": profile["deck"].get("new_per_day"),
            "weak_areas": profile.get("weak_areas") or [],
        },
        "level": current_level(),
        "level_history": [{**e, "date": str(e["date"])} for e in load_history()],
        "today": {k: status[k] for k in (
            "done", "streak", "due", "reviews_today", "anki_done", "journal_done",
            "journal_words", "checked", "remaining", "minutes_left",
            "collection_stale_minutes", "anki_error")},
        "anki": {
            "error": cards["error"] or stats["error"],
            "cards": dict(totals),
            "total": sum(totals.values()),
            "retention_30": stats["retention"],
            "reviews_30": stats["reviews"],
            "retention_target": 90,
            "daily_reviews_30": [
                {"date": (today - timedelta(days=i)).isoformat(),
                 "reviews": daily.get((today - timedelta(days=i)).isoformat(), 0)}
                for i in range(29, -1, -1)],
            "reviews_all_time": sum(daily.values()),
        },
        "level_meter": meter,
        "game": game,
        "heatmap": heat,
        "topics": topics,
        "journal": {
            "entries": len(entries),
            "words": sum(e["words"] for e in entries),
            "checked": sum(e["checked"] for e in entries),
            "recent": entries[-14:],
            "errors_per_100_by_month": errors_per_100_by_month(),
            "targets": prompts[-10:],
            "last_free": free[-1] if free else None,
            "days_since_free": (today - date.fromisoformat(free[-1])).days if free else None,
        },
        "speaking": speaking,
        "errors": {
            "total": len(errors),
            "last_30": sum(last30.values()),
            "weeks": [w.isoformat() for w in weeks],
            "top": top_points,
            "recurring": [p for p, n in last14.most_common() if n >= 2],
            "gaps": gaps,
        },
    }


def rows(d: dict) -> list[dict]:
    """The same data as one flat table, a `section` column per kind of row.

    This is the file the artifact loads. One file means one upload per refresh;
    the page splits it back into sections.
    """
    p, t, a, j, e = d["profile"], d["today"], d["anki"], d["journal"], d["errors"]
    out = [{
        "section": "today", "generated_at": d["generated_at"], "name": p["name"],
        "level": p["level"], "max_level": p["max_level"], "new_per_day": p["new_per_day"],
        "weak_areas": ", ".join(map(str, p["weak_areas"])),
        **{k: t[k] for k in ("done", "streak", "due", "reviews_today", "anki_done",
                             "journal_done", "journal_words", "checked", "minutes_left")},
        "remaining": ", ".join(t["remaining"]), "stale_minutes": t["collection_stale_minutes"],
    }, {
        "section": "anki", "total": a["total"], **a["cards"],
        "learned": a["cards"].get("young", 0) + a["cards"].get("mature", 0),
        "retention_30": a["retention_30"], "reviews_30": a["reviews_30"],
        "reviews_all_time": a["reviews_all_time"], "retention_target": a["retention_target"],
        "error": a["error"],
    }, {
        "section": "journal", "entries": j["entries"], "words": j["words"], "checked": j["checked"],
        "last_free": j["last_free"], "days_since_free": j["days_since_free"],
        "errors_total": e["total"], "errors_30": e["last_30"],
    }]
    sp = d["speaking"]
    last = sp["latest"] or {}
    out.append({
        "section": "speaking", "sessions": sp["sessions"], "minutes": sp["minutes"],
        "wpm_last_5": sp["wpm_last_5"], "wpm_change": sp["wpm_change"],
        "latest_date": last.get("date"), "latest_wpm": last.get("wpm"),
        "latest_pauses": last.get("pauses_per_min"), "latest_fillers": last.get("fillers_per_min"),
    })
    out += [{"section": "talk", "at": f"{t['date']} {t['time']}", **t} for t in sp["recent"]]
    g = d["game"]
    out.append({"section": "game", **{k: v for k, v in g.items()
                                       if k not in ("days", "goals", "badges", "rules")}})
    out += [{"section": "xp_rule", **x} for x in g["rules"]]
    out += [{"section": "xp_day", **x} for x in g["days"]]
    out += [{"section": "goal", **x} for x in g["goals"]]
    out += [{"section": "badge", **x} for x in g["badges"]]
    lm = d["level_meter"]
    cur, rec = lm["current"] or {}, lm["recorded"] or {}
    out.append({
        "section": "level", "label": cur.get("label"), "value": cur.get("value"),
        "low": cur.get("low"), "high": cur.get("high"), "confidence": cur.get("confidence"),
        "words": cur.get("words"), "errors": cur.get("errors"), "entries": cur.get("entries"),
        "window_days": lm["window_days"], "rate": cur.get("rate"),
        "accuracy_band": cur.get("accuracy_band"), "accuracy_value": cur.get("accuracy_value"),
        "sentence_length": cur.get("sentence_length"), "length_band": cur.get("length_band"),
        "length_value": cur.get("length_value"),
        "foundation_share": lm["foundation_share"], "leveled_errors": lm.get("leveled_errors"),
        "above_b1": (lm.get("lexical") or {}).get("above_b1"),
        "lexical_types": (lm.get("lexical") or {}).get("types"),
        "recorded_level": rec.get("overall"), "recorded_source": rec.get("source"),
        "recorded_date": str(rec["date"]) if rec.get("date") else None,
    })
    out += [{"section": "level_month", **{k: m[k] for k in (
        "month", "value", "label", "rate", "sentence_length", "words")}} for m in lm["monthly"]]
    out += [{"section": "level_retention", **r} for r in lm["retention_by_level"]]
    out += [{"section": "daily", **r} for r in a["daily_reviews_30"]]
    out += [{"section": "heat", **r} for r in d["heatmap"]]
    for tp in d["topics"]:
        anki = tp["anki"] or {}
        out.append({
            "section": "topic", "point": tp["point"], "level": tp["level"] or "own",
            "kind": tp["kind"], "sentences": tp["shared"] + tp["own"], "own": tp["own"],
            "in_deck": tp["in_deck"], "status": "in deck" if tp["in_deck"] else f"left out ({tp['left_out']})",
            "new": anki.get("new"), "learning": anki.get("learning"), "young": anki.get("young"),
            "mature": anki.get("mature"), "suspended": anki.get("suspended"), "due": anki.get("due"),
            "retention_30": tp["retention_30"], "reviews_30": tp["reviews_30"],
            "errors_all": tp["errors_all"], "errors_30": tp["errors_30"],
        })
    out += [{"section": "entry", **r} for r in j["recent"]]
    out += [{"section": "month", **r} for r in j["errors_per_100_by_month"]]
    out += [{"section": "target", **r} for r in j["targets"]]
    for tp in e["top"]:
        out.append({"section": "error_point", "point": tp["point"], "all_time": tp["all_time"],
                    "last_30": tp["last_30"], "last_14": tp["last_14"], "in_deck": tp["in_deck"],
                    "recurring": tp["point"] in e["recurring"]})
        out += [{"section": "error_week", "point": tp["point"], "week": w, "n": n}
                for w, n in zip(e["weeks"], tp["weekly"])]
        out += [{"section": "example", "point": tp["point"], **x} for x in tp["examples"]]
    out += [{"section": "gap", **g} for g in e["gaps"]]
    return out


def changes(old: dict | None, new: dict) -> str:
    """One line on what moved since the last refresh."""
    if not old:
        return "first dashboard data"
    parts = []

    def delta(label, a, b):
        if a is not None and b is not None and a != b:
            parts.append(f"{label} {a} → {b}")

    oa, na = old.get("anki", {}), new["anki"]
    delta("reviews", oa.get("reviews_all_time"), na["reviews_all_time"])
    delta("mature cards", oa.get("cards", {}).get("mature"), na["cards"].get("mature"))
    delta("cards", oa.get("total"), na["total"])
    delta("entries", old.get("journal", {}).get("entries"), new["journal"]["entries"])
    delta("errors", old.get("errors", {}).get("total"), new["errors"]["total"])
    delta("speaking sessions", (old.get("speaking") or {}).get("sessions"), new["speaking"]["sessions"])
    delta("streak", old.get("today", {}).get("streak"), new["today"]["streak"])
    delta("XP", (old.get("game") or {}).get("xp"), new["game"]["xp"])
    old_tiers = {b["id"]: b["tier"] for b in (old.get("game") or {}).get("badges", [])}
    if old_tiers:
        for b in new["game"]["badges"]:
            if b["tier"] > old_tiers.get(b["id"], 0):
                parts.append(f"badge earned: {b['name']} {b['tier_name']}")
    delta("level estimate", ((old.get("level_meter") or {}).get("current") or {}).get("label"),
          (new["level_meter"]["current"] or {}).get("label"))

    def recorded(d):
        r = (d.get("level_meter") or {}).get("recorded") or {}
        return f"{r['overall']} ({r.get('source', '?')}, {r.get('date')})" if r.get("overall") else "none"

    if (old.get("level_meter") or {}) and recorded(old) != recorded(new):
        parts.append(f"recorded level {recorded(old)} → {recorded(new)}")
    return ", ".join(parts) or "no change since the last refresh"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="also print the data")
    args = ap.parse_args()

    old = None
    if DATA.exists():
        try:
            old = json.loads(DATA.read_text())
        except ValueError:
            old = None
    data = gather()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    ROWS.write_text(json.dumps(rows(data), ensure_ascii=False, default=str))
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    else:
        print(f"Wrote {DATA}")
        print(f"Changed: {changes(old, data)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
