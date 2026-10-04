#!/usr/bin/env python3
"""Where everything lives: the shared app, and one learner's data in me/.

The repo is an app several people clone. Everything that belongs to a single
learner — journal, error log, own cards, profile, reminder config — lives under
me/, which is gitignored, so `english update` (a git pull) can never conflict
with anyone's data. Every script resolves paths here rather than on its own.

ENGLISH_ME points the scripts at another data directory, which is how you try
a change against a throwaway profile without touching your real one.
"""

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
MEDIA = ROOT / "media"
APKG = ROOT / "english.apkg"

ME = Path(os.environ.get("ENGLISH_ME") or ROOT / "me").resolve()
PROFILE = ME / "profile.yml"
JOURNAL = ME / "journal"
ERRORS = ME / "errors.md"
MY_CARDS = ME / "my-cards"
LEVELS = ME / "level-history.yml"
REPORTS = ME / "reports"
CONFIG = ME / ".reminders.json"
STATE = ME / ".state"

CEFR = ("A1", "A2", "B1", "B2", "C1", "C2")

DEFAULT_PROFILE = {
    "name": "",
    "handle": "",
    "native_language": "",
    "goal": "everyday conversational English",
    "level": None,
    "deck": {"max_level": "C1", "skip": [], "new_per_day": 6},
    "weak_areas": [],
    "life_context": "",
}


def load_profile() -> dict:
    """me/profile.yml over DEFAULT_PROFILE. A missing file yields the defaults,
    so building and checking work before onboarding has run."""
    profile = {**DEFAULT_PROFILE, "deck": dict(DEFAULT_PROFILE["deck"])}
    if PROFILE.exists():
        user = yaml.safe_load(PROFILE.read_text()) or {}
        for key, value in user.items():
            if key == "deck" and isinstance(value, dict):
                profile["deck"].update(value)
            else:
                profile[key] = value
    return profile


def content_files() -> list[tuple[Path, dict, bool]]:
    """(path, data, personal) for every card file: shared content/ first, then
    the learner's own me/my-cards/. Empty files are skipped."""
    out = []
    for base, personal in ((CONTENT, False), (MY_CARDS, True)):
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.yml")):
            data = yaml.safe_load(path.read_text())
            if data:
                out.append((path, data, personal))
    return out


def display(path: Path) -> Path:
    """Repo-relative where possible; ENGLISH_ME can sit outside the repo."""
    return path.relative_to(ROOT) if path.is_relative_to(ROOT) else path


def level_index(level: str | None) -> int:
    """Position on the CEFR scale; unknown or missing sorts above C2."""
    return CEFR.index(level) if level in CEFR else len(CEFR)
