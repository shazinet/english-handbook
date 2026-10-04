#!/usr/bin/env python3
"""Import english.apkg into the local Anki collection and configure scheduling.

Does what you would otherwise do by hand in the Anki GUI: import the package,
turn on FSRS, and cap new cards per day (deck.new_per_day in me/profile.yml). Safe to re-run — the import updates
notes in place (GUIDs are stable, see build_anki.py) rather than duplicating.

ANKI MUST BE CLOSED when this runs; the collection is a SQLite database and
opening it from two processes will corrupt it.
"""

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from anki.collection import Collection
from anki.import_export_pb2 import (
    IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_ALWAYS,
    ImportAnkiPackageOptions,
    ImportAnkiPackageRequest,
)

from ankidb import COLLECTION, DECK_PREFIX, LEGACY_PREFIX, ours
from paths import APKG, content_files, load_profile

CONFIG_NAME = DECK_PREFIX
UPDATE_ALWAYS = IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_ALWAYS


def ensure_anki_closed() -> None:
    if subprocess.run(["pgrep", "-x", "Anki"], capture_output=True).returncode == 0:
        sys.exit(
            "Anki is running — quit it first, then re-run this script.\n"
            "If you review on a phone: sync the desktop BEFORE quitting, so this\n"
            "import doesn't diverge from AnkiWeb and force a one-way sync."
        )


def migrate_deck_name(col: Collection) -> None:
    """Rename the pre-sharing "English C1" tree (and its preset) to DECK_PREFIX.

    Must run BEFORE the import. Anki never moves existing cards on import, so
    importing under a new name first would split every topic between the old
    tree and the new one. Renaming keeps deck ids, cards and history intact,
    and syncs to the phone as an ordinary change.
    """
    legacy = col.decks.id_for_name(LEGACY_PREFIX)
    if not legacy:
        return
    if col.decks.id_for_name(DECK_PREFIX):
        sys.exit(f"Both {LEGACY_PREFIX!r} and {DECK_PREFIX!r} decks exist. Move the cards "
                 f"from one to the other in the Anki browser, delete the empty one, "
                 f"and re-run.")
    col.decks.rename(legacy, DECK_PREFIX)
    for conf in col.decks.all_config():
        if conf["name"] == LEGACY_PREFIX:
            conf["name"] = DECK_PREFIX
            col.decks.update_config(conf)
    print(f"Renamed deck {LEGACY_PREFIX!r} → {DECK_PREFIX!r} (history kept)")


def backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(f"collection-backup-{stamp}.anki2")
    shutil.copy2(path, dest)
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--collection", type=Path, default=COLLECTION,
                    help="another collection file, e.g. a copy to try an import on")
    ap.add_argument("--new-per-day", type=int,
                    default=load_profile()["deck"].get("new_per_day") or 6)
    args = ap.parse_args()

    target = args.collection.resolve()
    if target == COLLECTION.resolve():
        ensure_anki_closed()  # a copy can be imported into with Anki open
    if not APKG.exists():
        sys.exit(f"{APKG.name} not found — run build/build_anki.py first.")
    if not target.exists():
        sys.exit(f"no Anki collection at {target}\nLaunch Anki once to create it.")

    print(f"Backup: {backup(target).name}")

    col = Collection(str(target))
    try:
        migrate_deck_name(col)
        req = ImportAnkiPackageRequest(
            package_path=str(APKG),
            # ALWAYS (=1), not the default IF_NEWER (=0): IF_NEWER relies on the
            # generated package's mod times beating the collection's, so edited
            # cards can silently fail to update.
            # with_scheduling=False keeps YOUR review history authoritative — the
            # .apkg carries no scheduling worth importing.
            options=ImportAnkiPackageOptions(
                merge_notetypes=True,
                update_notes=UPDATE_ALWAYS,
                update_notetypes=UPDATE_ALWAYS,
                with_scheduling=False,
                with_deck_configs=False,
            ),
        )
        out = col.import_anki_package(req)
        log = out.log
        print(f"Imported: {len(log.new)} new, {len(log.updated)} updated, "
              f"{len(log.duplicate)} duplicate, {len(log.conflicting)} conflicting")

        # FSRS is a collection-wide setting.
        col.set_config("fsrs", True)

        # Use a DEDICATED preset rather than editing "Default" — otherwise the
        # new-card limit would silently apply to every other deck you ever add.
        conf = next((c for c in col.decks.all_config() if c["name"] == CONFIG_NAME), None)
        if conf is None:
            conf = col.decks.add_config(CONFIG_NAME)
        conf["new"]["perDay"] = args.new_per_day
        col.decks.update_config(conf)

        n = 0
        for deck_info in col.decks.all_names_and_ids():
            if not ours(deck_info.name):
                continue
            deck = col.decks.get(deck_info.id)
            col.decks.set_config_id_for_deck_dict(deck, conf["id"])
            n += 1

        print(f"FSRS enabled; preset {CONFIG_NAME!r} set to "
              f"{args.new_per_day} new cards/day, applied to {n} deck(s)")

        # Renaming a `point:` does NOT move cards that were already imported —
        # Anki updates note content in place but leaves each card in the deck it
        # first landed in. The result is a silently split topic: old cards in the
        # old deck, new ones in the new. Warn so it can't go unnoticed.
        # Every known point, including topics left out above the learner's
        # level: those decks are deliberate, not renamed.
        points = {f"{DECK_PREFIX}::{data['point']}" for _, data, _ in content_files()}
        stray = [
            d.name for d in col.decks.all_names_and_ids()
            if d.name.startswith(f"{DECK_PREFIX}::") and d.name not in points
        ]
        if stray:
            print("\nWARNING: deck(s) with no matching `point:` in content/ or me/my-cards/ —")
            print("probably a renamed topic, leaving cards stranded in the old deck:")
            for s in stray:
                print(f"  {s!r}  ({len(col.find_cards(chr(34) + 'deck:' + s + chr(34)))} cards)")
            print("Move the cards in the Anki browser, then delete the empty deck.")
    finally:
        col.close()


if __name__ == "__main__":
    main()
