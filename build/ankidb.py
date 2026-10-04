#!/usr/bin/env python3
"""Shared access to the local Anki collection.

install_deck.py opens the real collection to *write* to it, which is why it
refuses to run while Anki is up — two SQLite writers corrupt it. status.py and
remind.py only read, and they must be able to read *while Anki is open*, or an
evening reminder could never fire during a review session.

Reading a live Anki collection is fussier than it looks. It is WAL-mode SQLite:

  * `file:...?mode=ro` fails outright — WAL needs write access to the `-shm`
    file, which read-only mode won't grant.
  * `file:...?immutable=1` opens fine but ignores the WAL, so reviews done in
    the last few minutes are invisible. Silently wrong is worse than failing.

Copying the database and its sidecars to a temp dir and reading the copy is the
one approach that is both safe (never touches the original) and current.
"""

import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

ANKI_BASE = Path.home() / "Library/Application Support/Anki2"


def _profile() -> str:
    """ANKI_PROFILE if set, else Anki's default "User 1", else the only profile.

    The default name differs when Anki runs in another language or the profile
    was renamed, so a lone profile directory is taken to be the one meant.
    """
    if name := os.environ.get("ANKI_PROFILE"):
        return name
    if (ANKI_BASE / "User 1").is_dir():
        return "User 1"
    found = [p.name for p in ANKI_BASE.glob("*") if (p / "collection.anki2").exists()]
    return found[0] if len(found) == 1 else "User 1"


COLLECTION = ANKI_BASE / _profile() / "collection.anki2"
DECK_PREFIX = "English Practice"
# The root deck's name before the app was shared. install_deck.py renames it to
# DECK_PREFIX before importing; review history lives on the cards, so a rename
# loses nothing — but an import alone would leave old cards behind in it.
LEGACY_PREFIX = "English C1"


def ours(name: str) -> bool:
    """Whether a deck name is the app's root or one of its subdecks. Exact, so a
    learner's unrelated "English Practice Extra" deck is never touched."""
    return name == DECK_PREFIX or name.startswith(f"{DECK_PREFIX}::")


# WAL sidecars. Copy order matters: the main db first, then the log that
# supersedes parts of it, which is the order SQLite itself expects to find them.
SIDECARS = ("-wal", "-shm")


@contextmanager
def snapshot():
    """Yield a Path to a throwaway copy of the collection, sidecars included.

    The copy can be torn if Anki happens to be mid-write, in which case opening
    it raises and the caller degrades — that beats blocking on a lock.
    """
    if not COLLECTION.exists():
        raise FileNotFoundError(f"no Anki collection at {COLLECTION}")

    with tempfile.TemporaryDirectory(prefix="english-status-") as tmp:
        dest = Path(tmp) / COLLECTION.name
        shutil.copy2(COLLECTION, dest)
        for suffix in SIDECARS:
            side = COLLECTION.with_name(COLLECTION.name + suffix)
            if side.exists():
                shutil.copy2(side, dest.with_name(dest.name + suffix))
        yield dest
