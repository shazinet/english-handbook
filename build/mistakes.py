#!/usr/bin/env python3
"""Your own logged errors, served back for re-correction (/mistakes).

Every row of me/errors.md is a mistake. /mistakes shows the wrong version and
asks for the right one; each answer is marked here in me/mistakes.log:

    2026-10-26T19:40<TAB>3fa2c91b<TAB>ok

A mistake is **resolved** once it has been fixed on two different days: one
good answer could be short-term memory, two days apart is retrieval. A miss is
recorded here and never re-logged to errors.md, which would count the same
error twice. Rows are keyed by a hash of their date and wrong text, so editing
the correction or the explanation keeps the history.

    ./english mistakes --next 10 [--point P]   open mistakes to practise, as JSON
    ./english mistakes --mark KEY ok|miss      record one answer
    ./english mistakes --stats                 open / resolved counts, as JSON
"""

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from paths import ME
from progress import error_details

LOG = ME / "mistakes.log"
RESOLVE_DAYS = 2      # fixed on this many different days = resolved
RECENT_DAYS = 60      # how far back "this point keeps recurring" looks


def key(row: dict) -> str:
    return hashlib.sha1(f"{row['date']}|{row['wrong']}".encode()).hexdigest()[:8]


def marks() -> list[dict]:
    if not LOG.exists():
        return []
    out = []
    for line in LOG.read_text().splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[2] in ("ok", "miss"):
            out.append({"at": parts[0], "date": parts[0][:10], "key": parts[1], "ok": parts[2] == "ok"})
    return out


def state(today: date | None = None) -> dict:
    """Every mistake with its history, and the totals the path and XP use."""
    today = today or date.today()
    rows = error_details()
    logged = marks()
    history = defaultdict(list)
    for m in logged:
        history[m["key"]].append(m)
    since = (today - timedelta(days=RECENT_DAYS)).isoformat()
    recent = Counter(r["point"] for r in rows if r["date"] >= since)

    items = []
    for r in rows:
        k = key(r)
        h = history.get(k, [])
        ok_days = sorted({m["date"] for m in h if m["ok"]})
        items.append({
            "key": k, **r,
            "fixed_days": len(ok_days),
            "misses": sum(1 for m in h if not m["ok"]),
            "last_seen": h[-1]["date"] if h else None,
            "resolved": len(ok_days) >= RESOLVE_DAYS,
            "resolved_on": ok_days[RESOLVE_DAYS - 1] if len(ok_days) >= RESOLVE_DAYS else None,
            "recent_on_point": recent[r["point"]],
        })
    by_point = defaultdict(lambda: {"open": 0, "resolved": 0})
    for it in items:
        by_point[it["point"]]["resolved" if it["resolved"] else "open"] += 1
    return {
        "items": items,
        "open": sum(1 for it in items if not it["resolved"]),
        "resolved": sum(1 for it in items if it["resolved"]),
        "by_point": dict(by_point),
        "fixed_by_date": dict(Counter(m["date"] for m in logged if m["ok"])),
    }


def next_up(n: int, point: str | None = None, today: date | None = None) -> list[dict]:
    """The open mistakes most worth practising: points that keep recurring
    first, then ones missed before, then the oldest. A mistake already answered
    correctly today waits for another day, since today can't be its second."""
    today_iso = (today or date.today()).isoformat()
    pool = [it for it in state(today)["items"] if not it["resolved"]
            and (point is None or it["point"] == point)
            and not (it["last_seen"] == today_iso and it["fixed_days"])]
    pool.sort(key=lambda it: (-it["recent_on_point"], -it["misses"], it["date"]))
    return pool[:n]


def mark(k: str, ok: bool) -> None:
    known = {key(r) for r in error_details()}
    if k not in known:
        raise SystemExit(f"no mistake with key {k} in errors.md")
    ME.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%dT%H:%M')}\t{k}\t{'ok' if ok else 'miss'}\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--next", type=int, metavar="N", help="the N open mistakes to practise next")
    g.add_argument("--mark", nargs=2, metavar=("KEY", "RESULT"), help="record ok or miss for a mistake")
    g.add_argument("--stats", action="store_true", help="counts, as JSON")
    ap.add_argument("--point", help="with --next: only this grammar point")
    a = ap.parse_args()

    if a.next is not None:
        fields = ("key", "date", "point", "wrong", "right", "why", "fixed_days", "misses")
        print(json.dumps([{f: it[f] for f in fields} for it in next_up(a.next, a.point)],
                         indent=2, ensure_ascii=False))
    elif a.mark:
        k, result = a.mark
        if result not in ("ok", "miss"):
            ap.error("RESULT must be ok or miss")
        mark(k, result == "ok")
        it = next(i for i in state()["items"] if i["key"] == k)
        print(f"{k}: {result} · fixed on {it['fixed_days']} day(s)"
              + (" · resolved" if it["resolved"] else ""))
    else:
        s = state()
        print(json.dumps({k: s[k] for k in ("open", "resolved", "by_point", "fixed_by_date")},
                         indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
