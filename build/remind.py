#!/usr/bin/env python3
"""Nudge the phone if today's practice isn't done, and publish status for the widget.

Run by launchd every 30 minutes through the evening (see automation/). Each run:

  1. asks status.py whether the day is complete
  2. if not, sends *one* push — the latest tier whose time has passed and that
     hasn't fired yet, so a Mac that wakes at 23:10 sends the 23:00 nudge rather
     than three stale ones at once
  3. publishes a small JSON blob to a secret gist, which the lock-screen widget
     reads

Notifications go through ntfy.sh: free, no account, and a topic name is the only
credential. That also means the topic is a capability — anyone who knows it can
read your pushes — so it lives in me/.reminders.json, which is gitignored.

    python3 build/remind.py --dry-run --force-tier 22:00   # see the payload
    python3 build/remind.py                                # for real
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import date, datetime, time
from pathlib import Path

from paths import STATE
from status import compute, humanize, load_config

LOG = STATE / "remind.log"
LOG_MAX_BYTES = 256 * 1024
KEEP_STATE_DAYS = 14

# ntfy takes 1-5; these names are what .reminders.json uses.
PRIORITIES = {"min": 1, "low": 2, "default": 3, "high": 4, "urgent": 5}

# Fields the widget actually renders. Deliberately excludes anything clock-based:
# the widget computes the countdown itself, so its numbers stay right even when
# this Mac has been asleep for hours and the payload is stale.
PUBLISHED = ("date", "done", "streak", "due", "remaining", "anki_error")
REPUBLISH_AFTER_MINUTES = 120


def log(message: str) -> None:
    STATE.mkdir(exist_ok=True)
    if LOG.exists() and LOG.stat().st_size > LOG_MAX_BYTES:
        LOG.write_text(LOG.read_text()[-LOG_MAX_BYTES // 2 :])
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG.open("a") as fh:
        fh.write(f"{stamp}  {message}\n")


def state_path(day: date) -> Path:
    return STATE / f"reminders-{day.isoformat()}.json"


def read_state(day: date) -> dict:
    path = state_path(day)
    if path.exists():
        return json.loads(path.read_text())
    return {"sent": [], "celebrated": False}


def write_state(day: date, data: dict) -> None:
    STATE.mkdir(exist_ok=True)
    state_path(day).write_text(json.dumps(data, indent=2) + "\n")
    stale = sorted(STATE.glob("reminders-*.json"))[:-KEEP_STATE_DAYS]
    for old in stale:
        old.unlink()


# --- what to say -------------------------------------------------------------


def pick_tier(conf: dict, now: datetime, sent: list[str]) -> dict | None:
    """The latest tier that is due and hasn't fired today."""
    tiers = sorted(conf["tiers"], key=lambda t: t["at"])
    passed = [t for t in tiers if time.fromisoformat(t["at"]) <= now.time()]
    if not passed or passed[-1]["at"] in sent:
        return None
    return passed[-1]


def compose(status: dict, tier: dict) -> dict:
    """The ntfy payload. Always names what is actually missing — a reminder that
    can't tell you what it wants is just noise you learn to swipe away."""
    left = status["minutes_left"]
    title = "English — today's practice" if left > 240 else f"{humanize(left)} left"

    message = "Still to do: " + ", ".join(status["remaining"])
    if status["streak"]:
        message += f"\n🔥 {status['streak']} on the line."
    if status["anki_error"]:
        message += "\n(Anki couldn't be read — open it on this Mac and sync.)"

    priority = PRIORITIES.get(tier.get("priority", "default"), 3)
    return {
        "title": title,
        "message": message,
        "priority": priority,
        "tags": ["rotating_light"] if priority >= 5 else ["books"],
    }


def compose_celebration(status: dict) -> dict:
    return {
        "title": f"🔥 {status['streak']}",
        "message": "Done for today — reps, journal, check.",
        "priority": PRIORITIES["low"],
        "tags": ["fire"],
    }


# --- delivery ----------------------------------------------------------------


def send(conf: dict, payload: dict) -> None:
    """Publish to ntfy over its JSON API.

    The JSON endpoint rather than the X-Title header form: HTTP headers are
    latin-1, so an emoji in a title would raise before it ever left the machine.
    """
    ntfy = conf["ntfy"]
    if not ntfy.get("topic"):
        raise RuntimeError("no ntfy topic configured — run automation/install_reminders.sh")

    body = json.dumps({"topic": ntfy["topic"], **payload}).encode()
    request = urllib.request.Request(
        ntfy.get("server", "https://ntfy.sh").rstrip("/"),
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        response.read()


def gh_binary(conf: dict) -> str:
    """Absolute path to gh.

    launchd gives the job a bare PATH — no /opt/homebrew/bin — so a plain "gh"
    resolves interactively and then fails at 22:00, which is the worst possible
    time to find out. install_reminders.sh records the resolved path; the search
    below is the fallback for a hand-written config.
    """
    configured = conf.get("gh_bin")
    if configured:
        return configured
    search = os.environ.get("PATH", "") + ":/opt/homebrew/bin:/usr/local/bin"
    found = shutil.which("gh", path=search)
    if not found:
        raise RuntimeError("gh not found — brew install gh, or set gh_bin in me/.reminders.json")
    return found


def publish(conf: dict, status: dict, force: bool = False) -> bool:
    """Push the widget's JSON to the secret gist. Returns whether it wrote.

    Skips unchanged payloads so the gist doesn't collect 24 revisions a day, but
    republishes periodically regardless so `generated_at` proves the Mac is alive.
    """
    gist_id = conf.get("gist_id")
    if not gist_id:
        return False

    payload = {key: status[key] for key in PUBLISHED}
    payload["generated_at"] = status["generated_at"]

    marker = STATE / "published.json"
    if not force and marker.exists():
        previous = json.loads(marker.read_text())
        unchanged = all(previous.get(key) == payload[key] for key in PUBLISHED)
        age = datetime.now() - datetime.fromtimestamp(marker.stat().st_mtime)
        if unchanged and age.total_seconds() < REPUBLISH_AFTER_MINUTES * 60:
            return False

    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / "status.json"
        local.write_text(json.dumps(payload, indent=2) + "\n")
        subprocess.run(
            [gh_binary(conf), "gist", "edit", gist_id, "--filename", "status.json", str(local)],
            check=True,
            capture_output=True,
        )
    STATE.mkdir(exist_ok=True)
    marker.write_text(json.dumps(payload, indent=2) + "\n")
    return True


# --- main --------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="print, send nothing, save nothing")
    ap.add_argument("--force-tier", metavar="HH:MM", help="fire this tier regardless of the clock")
    args = ap.parse_args()

    conf = load_config()
    status = compute(conf=conf)
    today = date.fromisoformat(status["date"])
    state = read_state(today)
    now = datetime.now()

    if args.force_tier:
        tier = next(
            (t for t in conf["tiers"] if t["at"] == args.force_tier),
            {"at": args.force_tier, "priority": "default"},
        )
    else:
        tier = pick_tier(conf, now, state["sent"])

    if status["done"]:
        payload = compose_celebration(status) if conf["celebrate"] else None
        already = state["celebrated"] or not conf["celebrate"]
        action = "done" if already else "celebrate"
        if already:
            payload = None
    else:
        payload = compose(status, tier) if tier else None
        action = "nudge" if payload else "quiet"

    if args.dry_run:
        print(json.dumps({"status": status, "tier": tier, "payload": payload}, indent=2))
        return 0

    try:
        if payload:
            send(conf, payload)
            if action == "celebrate":
                state["celebrated"] = True
            else:
                # Everything earlier than the tier we just fired is moot; marking
                # it sent stops a late wake-up from replaying the whole evening.
                for earlier in conf["tiers"]:
                    if earlier["at"] <= tier["at"]:
                        state["sent"].append(earlier["at"])
                state["sent"] = sorted(set(state["sent"]))
            write_state(today, state)
        log(f"{action}: {', '.join(status['remaining']) or 'nothing left'} "
            f"(streak {status['streak']}, {humanize(status['minutes_left'])} left)")
    except Exception as exc:
        log(f"send failed: {type(exc).__name__}: {exc}")

    try:
        if publish(conf, status):
            log("published status.json to gist")
    except Exception as exc:
        log(f"publish failed: {type(exc).__name__}: {exc}")

    # Always 0. A launchd job that exits nonzero gets throttled, and then the
    # reminders quietly stop working — the exact failure this is meant to prevent.
    return 0


if __name__ == "__main__":
    sys.exit(main())
