#!/usr/bin/env python3
"""Compile content/**/*.yml and me/my-cards/*.yml into an Anki deck.

Card GUIDs are derived deterministically from the card `id`, so rebuilding and
re-importing updates note content in place and PRESERVES review history. This
is the single most important property of this script: a naive rebuild that
generates fresh GUIDs resets every card's scheduling.

Shared topics above the learner's `deck.max_level` (me/profile.yml), or named
in `deck.skip`, are left out of the package. Leaving a topic out never removes
cards already imported — Anki keeps them — so lowering the level only stops new
ones arriving; suspend the old ones in Anki if you want them gone.
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

import genanki

from ankidb import DECK_PREFIX, LEGACY_PREFIX

from paths import APKG as OUTPUT
from paths import CEFR, MEDIA, ROOT, content_files, display, level_index, load_profile

# Stable across runs. Changing these re-creates the deck/model rather than
# updating it, which is why they are hardcoded rather than generated.
DECK_ID = 1735820001
MODEL_ID = 1735820002
DECK_ROOT = DECK_PREFIX
# Subdeck ids stay hashed from the pre-rename root name, so a renamed collection
# matches the package by id as well as by name. Never change this string.
DECK_ID_SEED = LEGACY_PREFIX

CLOZE_RE = re.compile(r"\{\{c(\d+)::(.+?)\}\}")

CSS = """
.card {
  font-family: -apple-system, Helvetica, Arial, sans-serif;
  font-size: 21px;
  text-align: center;
  color: #1a1a1a;
  background: #fdfdfb;
  padding: 18px;
}
.cloze { font-weight: 700; color: #1565c0; }
.note {
  font-size: 15px; color: #444; margin-top: 20px;
  padding-top: 14px; border-top: 1px solid #ddd;
  text-align: left; line-height: 1.5;
}
.trap {
  font-size: 15px; color: #b3261e; margin-top: 10px;
  text-align: left; line-height: 1.5;
}
.point { font-size: 12px; color: #999; margin-top: 16px; letter-spacing: .04em; }
.audio { margin-top: 14px; }
nightMode .card { color: #eee; background: #2a2a2a; }
nightMode .note { color: #bbb; border-top-color: #444; }
nightMode .cloze { color: #82b1ff; }
nightMode .trap { color: #f2b8b5; }
"""

MODEL = genanki.Model(
    MODEL_ID,
    "English C1 Cloze",
    fields=[
        {"name": "Text"},
        {"name": "Note"},
        {"name": "Trap"},
        {"name": "Point"},
        {"name": "Audio"},
    ],
    templates=[
        {
            "name": "Cloze",
            "qfmt": "{{cloze:Text}}",
            "afmt": (
                "{{cloze:Text}}\n"
                '{{#Audio}}<div class="audio">{{Audio}}</div>{{/Audio}}\n'
                '{{#Note}}<div class="note">{{Note}}</div>{{/Note}}\n'
                '{{#Trap}}<div class="trap">⚠ {{Trap}}</div>{{/Trap}}\n'
                '<div class="point">{{Point}}</div>'
            ),
        }
    ],
    css=CSS,
    model_type=genanki.Model.CLOZE,
)


def guid_for(card_id: str) -> str:
    """Deterministic GUID from the card id. See module docstring."""
    return hashlib.sha1(f"english-c1::{card_id}".encode()).hexdigest()[:16]


def validate(path: Path, data: dict, personal: bool, handle: str,
             seen: dict[str, Path]) -> list[str]:
    errors = []
    rel = display(path)

    if not data.get("point"):
        errors.append(f"{rel}: missing 'point'")
    # Shared topics need a level so each learner's deck can be cut to fit.
    # Own cards are always included, so for them it's optional.
    if not personal and data.get("level") not in CEFR:
        errors.append(f"{rel}: 'level' must be one of {', '.join(CEFR)}")
    if personal and not handle:
        errors.append(f"{rel}: set 'handle' in me/profile.yml before adding own cards")
    cards = data.get("cards")
    if not cards:
        errors.append(f"{rel}: no cards")
        return errors

    for card in cards:
        cid = card.get("id")
        if not cid:
            errors.append(f"{rel}: a card is missing 'id'")
            continue
        # A learner's ids carry their handle, so a card one person writes can be
        # shared with another without colliding with cards they wrote themselves.
        if personal and handle and not str(cid).startswith(f"{handle}-"):
            errors.append(f"{rel}[{cid}]: own card ids must start with '{handle}-'")
        if cid in seen:
            errors.append(f"{rel}: duplicate id '{cid}' (also in {seen[cid]})")
        else:
            seen[cid] = rel

        text = card.get("text", "")
        if not text:
            errors.append(f"{rel}[{cid}]: missing 'text'")
            continue
        if not CLOZE_RE.search(text):
            errors.append(f"{rel}[{cid}]: no {{{{c1::...}}}} cloze deletion")
        if text.count("{{") != text.count("}}"):
            errors.append(f"{rel}[{cid}]: unbalanced cloze braces")
        # IPA slipping in from the source PDFs — see CLAUDE.md rule 2.
        # Non-ASCII phonetic symbols only; ASCII letters would match ordinary words.
        if re.search(r"[ɪəʃːæɒʌθðŋʒɜɑɔˈˌ]", text):
            errors.append(f"{rel}[{cid}]: looks like IPA; use audio: true instead")
    return errors


RAW = ROOT / "build" / "raw"
WORD_RE = re.compile(r"[a-z0-9']+")


def coursebook_overlap(every: list[tuple[Path, dict, bool]]) -> list[str]:
    """Shared cards that share a six-word run with the source coursebook.

    The repo is public, so content/ must be original writing — rule 3 in
    CLAUDE.md. build/raw/ (the extracted book) only exists on a machine that
    has the PDFs, so elsewhere this is a silent no-op. Own cards in me/ are
    private and exempt.
    """
    if not RAW.is_dir():
        return []
    words = WORD_RE.findall(" ".join(
        p.read_text(errors="ignore") for p in RAW.glob("*.txt")).lower())
    book = {" ".join(words[i:i + 6]) for i in range(len(words) - 5)}
    problems = []
    for path, data, personal in every:
        if personal:
            continue
        for card in data.get("cards", []):
            for field in ("text", "note", "trap"):
                plain = CLOZE_RE.sub(lambda m: m.group(2).split("::")[0], card.get(field) or "")
                toks = WORD_RE.findall(plain.lower())
                if any(" ".join(toks[i:i + 6]) in book for i in range(len(toks) - 5)):
                    problems.append(f"{display(path)}[{card.get('id')}]: {field} repeats "
                                    f"coursebook wording; rewrite it in your own words")
    return problems


def included(data: dict, personal: bool, profile: dict) -> bool:
    """Whether a file belongs in this learner's deck."""
    if personal:
        return True
    deck = profile["deck"]
    if data["point"] in (deck.get("skip") or []):
        return False
    return level_index(data["level"]) <= level_index(deck.get("max_level") or "C2")


def build(files: list[tuple[Path, dict]]) -> tuple[genanki.Package, int]:
    decks = {}
    media_files = []
    count = 0

    for path, data in files:
        point = data["point"]
        base_tags = data.get("tags", [])
        deck_name = f"{DECK_ROOT}::{point}"
        if deck_name not in decks:
            # Derive a stable per-subdeck id so subdecks survive rebuilds too.
            seed = f"{DECK_ID_SEED}::{point}"
            sub_id = DECK_ID + int(hashlib.sha1(seed.encode()).hexdigest()[:6], 16) % 100000
            decks[deck_name] = genanki.Deck(sub_id, deck_name)
        deck = decks[deck_name]

        for card in data["cards"]:
            audio_field = ""
            if card.get("audio"):
                clip = MEDIA / f"{card['id']}.m4a"
                if clip.exists():
                    audio_field = f"[sound:{clip.name}]"
                    media_files.append(str(clip))
            note = genanki.Note(
                model=MODEL,
                fields=[
                    card["text"],
                    card.get("note", ""),
                    card.get("trap", ""),
                    point,
                    audio_field,
                ],
                tags=[t.replace(" ", "-") for t in base_tags + card.get("tags", [])],
                guid=guid_for(card["id"]),
            )
            deck.add_note(note)
            count += 1

    package = genanki.Package(list(decks.values()))
    package.media_files = media_files
    return package, count


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    ap.add_argument("--stats", action="store_true", help="print card counts per topic")
    args = ap.parse_args()

    every = content_files()
    if not every:
        sys.exit("no content files found under content/")

    profile = load_profile()
    handle = str(profile.get("handle") or "")
    seen: dict[str, Path] = {}
    errors = []
    for path, data, personal in every:
        errors.extend(validate(path, data, personal, handle, seen))
    errors.extend(coursebook_overlap(every))

    if errors:
        for err in errors:
            print(f"ERROR {err}", file=sys.stderr)
        sys.exit(f"\n{len(errors)} problem(s) found.")

    files = [(p, d) for p, d, personal in every if included(d, personal, profile)]
    left_out = len(every) - len(files)

    if args.stats:
        total = 0
        for path, data, personal in every:
            n = len(data["cards"])
            mark = "own" if personal else data["level"]
            if not included(data, personal, profile):
                mark += " (left out)"
            else:
                total += n
            print(f"{n:>4}  {mark:<15} {data['point']}")
        print(f"{total:>4}  TOTAL in your deck")
        return

    if args.check:
        total = sum(len(d["cards"]) for _, d, _ in every)
        print(f"OK — {len(every)} files, {total} cards, no problems.")
        return

    package, count = build(files)
    package.write_to_file(OUTPUT)
    audio = sum(1 for _, d in files for c in d["cards"] if c.get("audio"))
    missing = audio - len(package.media_files)
    print(f"Wrote {OUTPUT.relative_to(ROOT)} — {count} cards, {len(files)} topics.")
    if left_out:
        print(f"Left out {left_out} topic file(s) above your level or in deck.skip "
              f"(me/profile.yml); --stats lists them.")
    if missing > 0:
        print(f"Note: {missing} card(s) request audio but have no mp3. "
              f"Run: python3 build/audio.py")


if __name__ == "__main__":
    main()
