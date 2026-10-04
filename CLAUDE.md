# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An English practice app for everyday conversational English, used by several
learners from one public repo. Plain-text YAML in git is the
source of truth; `build/build_anki.py` compiles it into an Anki deck, and Anki's
FSRS scheduler handles spacing. The repo owns authorship; Anki owns scheduling.

**App and learner data are split.** Everything in the repo is the shared app:
code, slash commands, and the card library in `content/`. Everything belonging
to one learner lives in `me/`, which is gitignored and usually its own private
git repo: `profile.yml`, `journal/`, `errors.md`, `my-cards/`,
`level-history.yml`, reminder config and state. `./english update` is a git pull,
and it can only stay conflict-free if learner data never lands in app files —
so never write a learner's journal, errors or own cards outside `me/`, and never
put one learner's specifics (name, weak areas, life details) into app code,
commands or this file. All paths resolve through `build/paths.py`;
`ENGLISH_ME=/some/dir` points every script at another data directory, which is
how to test against a throwaway learner without touching the real one.

The current learner's level, weak areas and life context — what to prioritise
and what to write about — are in their profile:

@me/profile.yml

## Commands

```bash
./install.sh                    # fresh clone -> working setup; idempotent (--no-deck)
./english setup                 # onboarding + me/ + deck; re-runnable
./english update                # git pull, then install.sh to apply it
./english doctor                # check every part of the install
./english check                 # validate all card files (content/ + me/my-cards/)
./english stats                 # cards per topic, and what the learner's level leaves out
./english build                 # audio + english.apkg
./english deck                  # import into Anki, FSRS, new/day from the profile
./english status                # today's three checkboxes + streak (status.py --json)
./english level                 # level history and signals; --efset N / --record LVL
./english report                # shareable progress page in me/reports/
./english remind --dry-run      # the push that would fire now; sends nothing
./english reminders             # install the evening launchd job (--uninstall)
python3 build/extract.py        # PDFs -> build/raw/*.txt (one-time reference)
```

Each `./english` command wraps a script in `build/` that still runs on its own.
The wrapper prefers `.venv/bin/python`, where install.sh pins the `anki` library
to the installed Anki app's version (PyPI uses the app's version numbers); a
mismatch is the most common breakage, and `doctor` reports it.

`install_deck.py` writes to the live Anki collection and refuses to run while
Anki is open. The collection syncs to AnkiWeb and a phone, so the safe order is:
sync desktop → quit Anki → build → install → reopen → sync. Skipping the first
sync can force a one-way sync and discard reviews done on the phone. That's why
`setup` (and so `update`) asks whether Anki was synced before importing, and
skips the import when it can't ask. Never import on the learner's behalf
without that confirmation.

There is no test suite. `./english check` is the validation step; run it after
editing any content file. For anything touching learner data, try it under
`ENGLISH_ME=$(mktemp -d)/me` first.

## Card authoring rules

These are the rules that matter — violating them silently degrades the system.

1. **Cloze, never recognition.** A card must make you *produce* the target.
   `We're on a tight {{c1::budget}}` is correct; a `budget` → "money available
   for a purpose" front/back pair is not. Recognition cards build recognition,
   which is not the goal.
2. **Never author IPA.** The source PDFs have no `ToUnicode` maps, so their
   phonetics extract as garbage (`/braɪt/` → `/bra1t/`). Use `audio: true`
   instead, which generates real speech via macOS `say`.
3. **Original writing only — the repo is public.** `build/raw/` (the extracted
   coursebook, only on the original author's machine) may tell you *which*
   structure a topic covers; card sentences, notes and traps must be written
   fresh. `--check` rejects any shared card sharing a six-word run with the
   book whenever `build/raw/` exists. Every book-derived card was rewritten
   for the public release, keeping ids and cloze numbers. The raw text is also
   OCR-damaged (`5A`→`SA`, `inversion`→`1nvers1on`), so even as a syllabus
   read it against the grammar point's intent.
4. **Card `id` is permanent.** GUIDs are derived from it, so renaming an `id`
   destroys that card's review history in Anki. Add new ids freely; never
   rewrite an existing one.
   Renaming a **`point:`** is a different trap: the import updates note content
   in place but leaves already-imported cards in the deck they first landed in,
   so the topic silently splits across an old and a new subdeck. `install_deck.py`
   warns about decks with no matching `point:`; move the cards in the Anki
   browser (scheduling survives a move) and delete the empty deck.
   It also splits `errors.md`: `/check` and `/drill` tag each row with the
   `point:` value, and `/journal`, `/drill` and `/mine` pick targets by counting
   rows per point, so a renamed point resets its error history too.
   `DECK_ROOT` and `DECK_ID` in `build_anki.py` are equally permanent, because
   every subdeck id is hashed from them.
5. **Sentences must be everyday register.** Contexts should be ones a learner
   would plausibly say — work, travel, money, friends. Coursebook-flavoured
   examples about weaponry or farm animals were deliberately cut from scope.
6. **One grammar point per card.** If a sentence needs two unrelated
   explanations, it should be two cards.
7. **No learner's data in shared content.** Cards in `content/` are read by
   everyone, so traps say "NOT 'X'", never "Your error: 'X' (08-15)". Quotes
   from a learner's journal belong only in their own `me/my-cards/`. Place
   names stay generic for the same reason.

Licensing: code is MIT (`LICENSE`), cards in `content/` are CC BY-SA 4.0
(`content/LICENSE`). Anything added to `content/` is published under CC BY-SA,
so it must be original or compatibly licensed; never import cards from
another deck or book without checking its license.

## Content schema

```yaml
point: 6B conditionals          # human-readable topic name, becomes the Anki subdeck
level: B2                       # CEFR; required in content/, decides who gets the topic
tags: [grammar, conditionals]   # applied to every card in the file
cards:
  - id: 6b-03                   # permanent, unique repo-wide
    text: "If I {{c1::had known}}, I {{c2::would have made}} dinner."
    note: "Third conditional — unreal past."   # shown on the answer side
    trap: "NOT 'If I would have known'."       # optional; common-error warning
    audio: true                                # optional; vocab cards mostly
```

The build picks up every `content/**/*.yml` plus the learner's
`me/my-cards/*.yml`; file names and directories have no effect on the deck.
Only `point:` decides where cards land (`English Practice::<point>`), so an own card
with a shared topic's exact `point:` joins that subdeck.

Shared topics above the profile's `deck.max_level`, or listed in `deck.skip`,
are left out of the package. Leaving a topic out never deletes cards already
imported, so lowering a level only stops new ones arriving. The `level:` tags
are judgement calls by topic; correcting one is a one-line edit.

**Own cards** (`me/my-cards/`, written by `/mine`) must have ids starting with
the profile's `handle` plus a dash (`hoomaan-6b-m01`). The prefix makes a card
safe to promote into `content/` for everyone without colliding with another
learner's own ids, so `handle` is as permanent as an id. Cards mined before the
split (`<topic>-m01`) stay in `content/` as shared cards.

`--check` catches a missing `point`/`id`/`text`/`level`, duplicate ids, a
missing handle prefix, missing or unbalanced clozes, and IPA characters. It
cannot catch violations of rules 1, 5 or 6.

## Scope

Deliberately excluded from the source PDFs, for the everyday-usage goal:
grammar 4B (inversion) and 5A (distancing) as formal/written register; vocab
04 Conflict & warfare, 05 Sounds & the human voice, 11 Animal matters as
low-frequency topic vocab. The PDFs remain in `resources/` if this is revisited.
`resources/` is gitignored (the PDFs are copyrighted scans) and exists only on
the original author's machine. Only `extract.py` needs it.

The public repo (`shazinet/english-handbook`) started with fresh history, because
the original private repo's history holds coursebook text and one learner's
journal. Never push that old history to the public remote.

`content/grammar/00-tense-system/` is **authored, not extracted** — the source
book is a C1 reference summary that assumes the core tense system and never
teaches it. That gap is the whole reason this module exists.

## The practice loop

Cards alone teach rules you can recite but not use. The loop that closes the
gap: Anki reps → daily writing in `me/journal/` → `/check` corrects it and logs
to `me/errors.md` → `/mine` turns recurring errors into new cards in
`me/my-cards/`. When adding features, preserve that loop.

**Level** sits beside the loop, not in it. `/level` runs a short adaptive
placement and records it through `./english level --record`, which also updates
the profile's `level`, `deck.max_level` (one step above, capped at C1 where the
content ends) and `weak_areas`; an EF SET score is the objective anchor. Everything else in
`build/progress.py` is derived from data the loop already produces (errors per
100 words, retention by topic), so nothing asks the learner to log anything.
`./english report` must keep carrying numbers and topic names only. Learners
share it, so journal text and the sentences in `errors.md` must never reach it.

## The reminder layer

`build/status.py` decides whether a day counts, and `build/remind.py` pushes the
phone through the evening if it doesn't (see `automation/README.md`). Two
invariants hold it together:

1. **A day is done only when all three happened** — reps cleared *and* a journal
   entry with real writing in it *and* `/check` run. Loosening this to "any one
   of them" makes the streak meaningless, which makes the reminders ignorable.
2. **`/check` must keep appending `<!-- checked: … -->`** to the journal file it
   corrects, on every entry including flawless ones. That marker is the only
   evidence `/check` ran — error rows can't substitute, since a clean entry logs
   none. Changing or dropping the string silently zeroes every past streak.

The root deck is `English Practice` (`ankidb.DECK_PREFIX`). Collections from
before the rename have `English C1`; `install_deck.py` renames that tree and its
preset before importing, and subdeck ids stay hashed from the old name
(`DECK_ID_SEED`), so a renamed collection matches the package by both name and
id. Both constants are as permanent as card ids. The notetype is still called
"English C1 Cloze", because renaming a notetype risks forcing a full sync.

The launchd job is `com.english-handbook.reminder`; `install_reminders.sh`
removes the pre-split `dev.hoomaan.english-reminder` so no Mac runs both.

Reads of the Anki collection go through `build/ankidb.snapshot()`, which copies
the database before opening it. Never point a read at the live file: it's
WAL-mode SQLite, so `mode=ro` fails outright and `immutable=1` quietly returns
stale data. `install_deck.py` is the only thing that opens the real collection,
and only with Anki closed.
