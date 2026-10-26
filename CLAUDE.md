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
./english deck                  # import into Anki, FSRS, new/day from the profile; refuses a stale build
./english                       # home screen: path, next step, quests, practice (home.py; --json)
./english status                # today's three checkboxes + streak (status.py --json)
./english log KIND ...          # record a practice session in me/activity.log
./english mistakes --next 10    # open errors for /mistakes (--mark KEY ok|miss, --stats)
./english listen MIN / say TEXT # log listening; read text aloud in the card voice
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
   It also splits `errors.md`: `/check`, `/drill` and `/roleplay` tag each row with the
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
8. **Every gap must be answerable.** Someone who knows the rule should be able
   to tell what goes in the gap from the front alone. When the sentence still
   works with the gap empty (*Cycling is [...] the quickest way*), when several
   different words fit, or when the verb itself can't be guessed, add a hint
   after a second `::`, which Anki shows in place of `[...]`:
   `{{c1::by far::emphasis: easily}}`, `{{c1::had known::know}}`. A hint names
   the base verb for a tense or form gap, and the meaning or function for a
   word-choice gap. It never gives away what the card tests: no base verb when
   the card tests which verb (*make* vs *do*), no meaning when it tests a
   meaning. Gaps that grammar already pins down (*It depends [...] the price*)
   need none. `--check` can't judge this, so read each front as a learner would.

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
teaches it. That gap is the whole reason this module exists. The other `00-*`
topics fill the same kind of gap (articles, prepositions, the passive, reported
speech, questions, quantifiers, comparatives, too/enough/so/such, agreement, word form),
chosen by checking the CEFR-J Grammar Profile's A1–B2 items against the
deck and against the topic-less rows in learners' error logs.

## Open data

`./english vocab --fetch` (and `install.sh`) downloads open word lists into
`data/lexicon/` (gitignored, because the CEFR-J terms allow use with citation
but don't grant redistribution): NGSL 1.2 and NGSL-Spoken for frequency,
CEFR-J 1.5 and Octanove C1/C2 for levels, and the CEFR-J Grammar Profile
(`cefrj-grammar.csv`, a reference for which structures exist at which level).
`build/lexicon.py` joins them into `words.tsv`. They decide **which** words or
structures to target, never what a card says: rule 3 still holds, and nothing
from them is copied into `content/`. Everything degrades to "not fetched yet"
without them, so the build never needs the network. The vocabulary share in
`progress.writing_level()` stays a diagnostic, because there's no calibrated
scale to turn it into a CEFR estimate.

The speech tools live in `.venv-speech/` (`install.sh --speech`): Kokoro TTS
(`build/tts_kokoro.py`, called by `audio.py`) and mlx-whisper (`build/speak.py`).
They pull in torch, which must never be installed into `.venv`. `cli.py`
runs `speak.py` with that interpreter. Audio clips from any voice other than
`say` Samantha are named `<id>-<voice>.m4a`, so changing voice gives Anki a new
file rather than a same-named file with different content.

## The practice loop

Cards alone teach rules you can recite but not use. The loop that closes the
gap: Anki reps → daily writing in `me/journal/` → `/check` corrects it and logs
to `me/errors.md` → `/mine` turns recurring errors into new cards in
`me/my-cards/`. When adding features, preserve that loop.

**Practice and the path** sit on top of the loop and never redefine a day.
`/drill`, `/roleplay`, `/call`, `/mistakes`, `/story` and `./english listen`
each append one line to `me/activity.log` (`build/activity.py`), because they
leave no other trace; everything else is still read from its own evidence.
`build/gamify.py` turns that into XP, three daily quests and badges.
`build/learning_path.py` makes one unit per topic, ordered by recent errors
(the current unit is pinned in `me/.state/path-unit` until it's finished, so a
day's new errors never swap it out mid-way), and ticks four lessons per unit from evidence: a day's batch of the topic's
cards studied (first-review dates from the revlog), a logged
drill, a checked journal entry whose `.prompts.log` target names the point,
and a mistakes round. So `/journal` must start each target with the exact
`point:`. `/mistakes` marks answers in `me/mistakes.log` (`build/mistakes.py`):
a row of `errors.md` counts as resolved after it's fixed on two different days,
and misses are never re-logged to `errors.md`. `./english` with no arguments
(`build/home.py`) and the dashboard both render `dashboard.gather()`, so they
can't disagree.

**Level** sits beside the loop, not in it. `/level` runs a short adaptive
placement and records it through `./english level --record`, which also updates
the profile's `level`, `deck.max_level` (one step above, capped at C1 where the
content ends) and `weak_areas`; an EF SET score is the objective anchor. Everything else in
`build/progress.py` is derived from data the loop already produces (errors per
100 words, retention by topic), so nothing asks the learner to log anything.
`./english report` must keep carrying numbers and topic names only. Learners
share it, so journal text and the sentences in `errors.md` must never reach it.

## The dashboard

`/dashboard` keeps a private claude.ai dashboard (Dashboard artifact type) in
step with the learner's data. `./english dashboard` (`build/dashboard.py`)
writes `me/dashboard/data.json` and the flat `practice.json` the page loads;
the page itself is `build/dashboard.html`, app code with no learner data in it.
The artifact's link, the current data file's id and the page's hash live in
`me/dashboard/`, and the loop commands (`/journal`, `/check`, `/drill`, `/roleplay`, `/call`, `/mistakes`, `/story`, `/mine`, `/level`) refresh it as their last step when
`me/dashboard/artifact-url` exists. Anki reviews alone can't trigger a refresh;
they appear on the next one.

Unlike `./english report`, the dashboard carries `errors.md` sentences (the
learner's recent corrections). That's acceptable only because the artifact is
private. Never move those sentences into the report or anything else meant to
be shared, and never point `report.py` at `progress.error_details()`.

## The reminder layer

`build/status.py` decides whether a day counts, and `build/remind.py` pushes the
phone through the evening if it doesn't (see `automation/README.md`). Two
invariants hold it together:

1. **A day is done only when all three happened** — reps cleared *and* a journal
   entry with real writing in it *and* `/check` run. A `## spoken` transcript
   from `./english speak` counts as the writing: it's the same production,
   spoken. Loosening this to "any one
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
and only with Anki closed. Besides importing, it sets the preset to gather new
cards by position and renumbers our new cards in learning-path order, so the
daily session from the top deck starts on the current unit. The order only
changes on an import; `--no-path-order` leaves deck order.
