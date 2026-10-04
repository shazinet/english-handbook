#!/usr/bin/env python3
"""./english — one command for everything. Run it with no arguments for the list.

Most commands hand off to the script that already does the job (build_anki.py,
install_deck.py, status.py, ...), so each of those still works on its own. What
lives here is what only makes sense as one flow: first-run onboarding (`setup`),
pulling a new app version (`update`), and checking the whole install (`doctor`).
"""

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from paths import (
    CEFR, CONFIG, ERRORS, JOURNAL, ME, MY_CARDS, PROFILE, ROOT, display, load_profile,
)

BUILD = ROOT / "build"
ANKI_APP = Path("/Applications/Anki.app")
REMINDER_LABEL = "com.english-handbook.reminder"

ERRORS_HEADER = """# Error log

Every correction from `/check` and `/drill` lands here. This is the highest-signal
diagnostic in the system — count the tags monthly and the recurring ones are your
real weak areas, which are often not the ones you *feel* weak on.

`/mine` reads this file and turns repeated errors into cards.

| Date | Grammar point | I wrote | Correct | Why |
|---|---|---|---|---|
"""

LEVEL_CHOICES = [
    ("A2", "simple everyday exchanges in short sentences"),
    ("B1", "can talk about familiar topics, often searching for words"),
    ("B2", "comfortable in most conversations; mistakes don't block meaning"),
    ("C1", "fluent and flexible; working on precision and sounding natural"),
]

PROFILE_TEMPLATE = """\
# Your learner profile. Claude reads this (CLAUDE.md imports it) to aim journal
# prompts, drills and corrections at you; the build reads `deck` to cut the deck
# to your level. Edit freely — except `handle`, which is baked into your own
# card ids and must never change once you have cards in me/my-cards/.

name: {name}
handle: {handle}
native_language: {native}     # lets /check explain first-language interference
goal: {goal}

# Current CEFR estimate (A1–C2). /level and `./english level` keep it updated.
level: {level}

deck:
  max_level: {max_level}            # shared topics above this stay out of your deck
  skip: []                 # `point:` names to leave out entirely
  new_per_day: {new_per_day}

# What content should prioritise. /check and /level revise this from evidence.
weak_areas: []

# Real situations to write about, so prompts use your life, not a textbook's.
life_context: {life}
"""


# --- helpers -----------------------------------------------------------------


def run_script(name: str, *args: str) -> int:
    """Run one of the build scripts with this same interpreter."""
    return subprocess.call([sys.executable, str(BUILD / name), *args], cwd=ROOT)


def ask(prompt: str, default: str = "") -> str:
    shown = f" [{default}]" if default else ""
    answer = input(f"  {prompt}{shown}: ").strip()
    return answer or default


def yes(prompt: str, default: bool = False) -> bool:
    answer = ask(f"{prompt} (y/n)", "y" if default else "n").lower()
    return answer.startswith("y")


def anki_running() -> bool:
    return subprocess.run(["pgrep", "-x", "Anki"], capture_output=True).returncode == 0


def anki_app_version() -> str | None:
    if not ANKI_APP.exists():
        return None
    out = subprocess.run(
        ["defaults", "read", str(ANKI_APP / "Contents/Info"), "CFBundleShortVersionString"],
        capture_output=True, text=True,
    )
    return out.stdout.strip() or None


def heading(text: str) -> None:
    print(f"\n\033[1m{text}\033[0m", flush=True)


# --- setup -------------------------------------------------------------------


def onboard() -> None:
    """Ask the handful of questions that make the app this learner's."""
    heading("Welcome! A few questions to set this up for you.")
    print("  (Enter accepts the suggestion in brackets. Everything can be changed")
    print("   later in me/profile.yml.)\n")

    name = ask("Your first name")
    suggested = re.sub(r"[^a-z0-9]", "", name.lower()) or "me"
    while True:
        handle = ask("A short handle for your own card ids — never changes", suggested).lower()
        if re.fullmatch(r"[a-z][a-z0-9]{1,19}", handle):
            break
        print("    lowercase letters and digits, starting with a letter, 2–20 long")

    native = ask("Your first language (e.g. Persian, Spanish)")
    goal = ask("What do you want English for", "everyday conversational English")
    life = ask("A few things from your life to write about (work, plans, hobbies)")

    print("\n  Which sounds most like you right now?")
    for i, (code, text) in enumerate(LEVEL_CHOICES, 1):
        print(f"    {i}  {code}  {text}")
    print(f"    {len(LEVEL_CHOICES) + 1}  not sure — /level will find out")
    pick = ask("Number", str(len(LEVEL_CHOICES) + 1))
    level = None
    if pick.isdigit() and 1 <= int(pick) <= len(LEVEL_CHOICES):
        level = LEVEL_CHOICES[int(pick) - 1][0]

    # One step above the current level: the "i+1" a learner can actually reach.
    # The shared content tops out at C1, and an unknown level gets everything —
    # the 00 foundation decks are served first anyway, and /level trims it.
    if level:
        max_level = CEFR[min(CEFR.index(level) + 1, CEFR.index("C1"))]
    else:
        max_level = "C1"

    new_per_day = ask("New cards per day (6 is a calm pace)", "6")
    if not new_per_day.isdigit():
        new_per_day = "6"

    q = json.dumps  # a JSON string is a valid, safely quoted YAML scalar
    ME.mkdir(parents=True, exist_ok=True)
    PROFILE.write_text(PROFILE_TEMPLATE.format(
        name=q(name), handle=handle, native=q(native), goal=q(goal),
        level=level or "null", max_level=max_level, new_per_day=new_per_day,
        life=q(life),
    ))
    print(f"\n  Saved {display(PROFILE)}. Your deck covers topics up to {max_level}.")


def ensure_data_dir() -> None:
    """me/ with its journal, card folder, error log, and its own git repo."""
    JOURNAL.mkdir(parents=True, exist_ok=True)
    MY_CARDS.mkdir(parents=True, exist_ok=True)
    if not ERRORS.exists():
        ERRORS.write_text(ERRORS_HEADER)
    ignore = ME / ".gitignore"
    if not ignore.exists():
        ignore.write_text(".state/\n.reminders.json\n.DS_Store\n")
    # A separate repo, so the learner's history is backed up without ever
    # entering the shared app's.
    if shutil.which("git") and not (ME / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=ME, check=True)
        subprocess.run(["git", "add", "-A"], cwd=ME, check=True)
        subprocess.run(["git", "commit", "-qm", "Start my English data"], cwd=ME,
                       check=False, capture_output=True)
        print("  me/ is its own git repo — push it to a PRIVATE remote to back it up.")


def install_deck_if_possible() -> bool:
    """Import the deck now if Anki allows it; otherwise say exactly what to do."""
    if anki_running():
        print("  Anki is open, so the deck wasn't imported. When ready:")
        print("    sync in Anki → quit Anki → ./english deck → reopen Anki → sync")
        return False
    from ankidb import COLLECTION
    if not COLLECTION.exists():
        print("  No Anki collection yet. Open Anki once (sign in to AnkiWeb with the")
        print("  Sync button if you use a phone), quit it, then run: ./english deck")
        return False
    # Importing into a collection that's behind AnkiWeb can force a one-way sync
    # that throws away reviews done on the phone. Only the learner knows whether
    # they synced before quitting, so ask rather than guess.
    if not sys.stdin.isatty() or not yes(
            "Did you sync Anki before closing it? (no phone = yes)", default=False):
        print("  Skipped the import. Sync in Anki, quit it, then run: ./english deck")
        return False
    return run_script("install_deck.py") == 0


def cmd_setup(args: list[str]) -> int:
    first_run = not PROFILE.exists()
    if first_run:
        if not sys.stdin.isatty():
            print("Onboarding needs a terminal — run ./english setup interactively.")
            return 1
        onboard()
    ensure_data_dir()

    heading("Building your deck")
    if run_script("build_anki.py", "--check") != 0:
        return 1
    run_script("audio.py")
    if run_script("build_anki.py") != 0:
        return 1
    if "--no-deck" not in args:
        install_deck_if_possible()

    if first_run and sys.stdin.isatty():
        heading("Evening reminders (optional)")
        print("  Pushes to your phone through the evening while today's practice is")
        print("  unfinished. Needs a GitHub account and the free ntfy phone app.")
        if yes("Set them up now?"):
            for tool in ("jq", "gh"):
                if not shutil.which(tool) and shutil.which("brew"):
                    subprocess.call(["brew", "install", tool])
            if shutil.which("gh") and subprocess.call(["gh", "auth", "status"],
                                                      stdout=subprocess.DEVNULL,
                                                      stderr=subprocess.DEVNULL):
                subprocess.call(["gh", "auth", "login"])
            subprocess.call([str(ROOT / "automation/install_reminders.sh")])
        else:
            print("  Later: ./english reminders")

    if first_run:
        heading("You're set. Start here:")
        print("  1. Open Claude Code in this folder:   claude")
        print("  2. Find your level (~15 min):         /level")
        print("  3. Every day: Anki reps → /journal → write → /check")
        print("  Anytime: ./english status · ./english doctor · ./english help")
    return 0


# --- update ------------------------------------------------------------------


def cmd_update(args: list[str]) -> int:
    """Pull the newest app version, then re-run the installer to apply it.

    me/ is gitignored, so the pull can't touch learner data. Local edits to the
    app itself would make the pull fail half-way, so refuse up front instead.
    """
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        print("You have local changes to the app (not to me/):\n")
        print(dirty)
        print("\nCommit them, or `git stash`, then run ./english update again.")
        return 1
    before = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    if subprocess.call(["git", "pull", "--ff-only"], cwd=ROOT) != 0:
        return 1
    after = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    if before != after:
        heading("What's new")
        subprocess.call(["git", "--no-pager", "log", "--oneline", f"{before}..{after}"], cwd=ROOT)
    # install.sh is idempotent: it refreshes Python packages (re-pinning anki if
    # the app was upgraded), then rebuilds and re-imports through `setup`.
    return subprocess.call([str(ROOT / "install.sh")], cwd=ROOT)


# --- doctor ------------------------------------------------------------------


def cmd_doctor(args: list[str]) -> int:
    """Check every moving part and say how to fix what's broken."""
    results: list[tuple[bool, str, str]] = []

    def check(ok: bool, label: str, fix: str = "") -> None:
        results.append((bool(ok), label, fix))

    check(sys.platform == "darwin", "macOS", "audio (say) and reminders (launchd) need a Mac")
    in_venv = Path(sys.executable).parent.parent == ROOT / ".venv"
    check(in_venv, f"isolated Python ({sys.executable})", "run ./install.sh")
    for module in ("yaml", "genanki", "anki"):
        try:
            __import__(module)
            check(True, f"python package {module}")
        except ImportError:
            check(False, f"python package {module}", "run ./install.sh")

    app = anki_app_version()
    check(app is not None, f"Anki app {app or ''}".strip(), "brew install --cask anki")
    try:
        from importlib.metadata import version
        lib = version("anki")
        check(app is None or lib == app, f"anki library {lib} matches the app",
              "run ./install.sh to re-pin it (the app was probably upgraded)")
    except Exception:
        pass

    from ankidb import COLLECTION, LEGACY_PREFIX, ours, snapshot
    check(COLLECTION.exists(), f"Anki collection ({COLLECTION.parent.name})",
          "open Anki once; set ANKI_PROFILE if you have several profiles")
    if COLLECTION.exists():
        try:
            with snapshot() as copy:
                con = sqlite3.connect(copy)
                names = [r[0] for r in con.execute("select name from decks")]
                con.close()
            # Names are stored with \x1f between levels; the root is enough.
            roots = {n.split("\x1f")[0] for n in names}
            check(any(ours(r) for r in roots) or LEGACY_PREFIX in roots,
                  "deck imported into Anki", "quit Anki, then ./english deck")
            check(LEGACY_PREFIX not in roots, f"deck named {LEGACY_PREFIX!r} renamed",
                  "sync Anki → quit Anki → ./english deck (renames it, history kept)")
        except Exception as exc:
            check(False, "deck imported into Anki", f"couldn't read collection: {exc}")

    profile = load_profile()
    check(PROFILE.exists(), "learner profile (me/profile.yml)", "run ./english setup")
    check(bool(profile.get("handle")), "profile has a handle", "set handle: in me/profile.yml")
    check((ME / ".git").exists(), "me/ backed by its own git repo",
          "cd me && git init && git add -A && git commit -m 'my data'")
    check(shutil.which("claude") is not None, "Claude Code installed",
          "brew install --cask claude-code")

    ok = subprocess.run([sys.executable, str(BUILD / "build_anki.py"), "--check"],
                        capture_output=True, text=True)
    check(ok.returncode == 0, "card files valid", (ok.stderr or ok.stdout).strip()[-300:])

    loaded = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{REMINDER_LABEL}"],
                            capture_output=True).returncode == 0
    has_topic = CONFIG.exists() and bool(json.loads(CONFIG.read_text()).get("ntfy", {}).get("topic"))
    check(loaded and has_topic, "evening reminders (optional)", "./english reminders")

    for ok_, label, fix in results:
        mark = "\033[32m✓\033[0m" if ok_ else "\033[31m✗\033[0m"
        print(f"  {mark} {label}")
        if not ok_ and fix:
            print(f"      → {fix}")
    # The reminders are optional, so they alone don't fail the check.
    required = [r for r in results if r[1] != "evening reminders (optional)"]
    return 0 if all(r[0] for r in required) else 1


# --- dispatch ----------------------------------------------------------------

PASSTHROUGH = {
    "check": ("build_anki.py", ["--check"], "validate every card file"),
    "stats": ("build_anki.py", ["--stats"], "cards per topic, and what your level leaves out"),
    "deck": ("install_deck.py", [], "import the deck into Anki (Anki must be closed)"),
    "status": ("status.py", [], "today's three checkboxes and your streak"),
    "remind": ("remind.py", [], "run the reminder once (--dry-run to preview)"),
    "level": ("level.py", [], "your level history; --efset N records a test score"),
    "report": ("report.py", [], "a shareable progress page (no journal text)"),
}


def cmd_build(args: list[str]) -> int:
    return run_script("audio.py") or run_script("build_anki.py", *args)


def cmd_reminders(args: list[str]) -> int:
    return subprocess.call([str(ROOT / "automation/install_reminders.sh"), *args])


COMMANDS = {
    "setup": (cmd_setup, "first run: profile, deck, reminders (safe to re-run)"),
    "update": (cmd_update, "get the newest app version and apply it"),
    "doctor": (cmd_doctor, "check the whole install and how to fix it"),
    "build": (cmd_build, "generate audio and build english.apkg"),
    "reminders": (cmd_reminders, "install evening reminders (--uninstall)"),
}


def usage() -> None:
    print("usage: ./english <command> [options]\n")
    rows = [(n, d) for n, (_, d) in COMMANDS.items()]
    rows += [(n, d) for n, (_, _, d) in PASSTHROUGH.items()]
    for name, desc in rows:
        print(f"  {name:<10} {desc}")
    print("\nIn Claude Code (run `claude` here): /level /journal /check /drill /mine")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("help", "-h", "--help"):
        usage()
        return 0
    name, args = sys.argv[1], sys.argv[2:]
    if name in COMMANDS:
        return COMMANDS[name][0](args)
    if name in PASSTHROUGH:
        script, fixed, _ = PASSTHROUGH[name]
        return run_script(script, *fixed, *args)
    print(f"unknown command: {name}\n")
    usage()
    return 2


if __name__ == "__main__":
    sys.exit(main())
