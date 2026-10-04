# English Practice Handbook

A system for making English usable in **everyday conversation**: Anki flashcards
that make you *produce* English, daily writing that Claude corrects, and a loop
that turns your own repeated mistakes into new cards. It adapts to your level,
from about B1 to C1.

It started as one learner's C1 handbook, following the syllabus of the *American
English File 5* grammar and vocabulary banks, plus a foundation (tenses,
articles, prepositions) the book never teaches. Every card is original writing.
Anyone can install it and keep it updated, and each person's data stays on
their own machine.

## Install — one command

On a Mac:

```bash
git clone https://github.com/shazinet/english-handbook.git ~/english
~/english/install.sh
```

That installs whatever is missing (Apple's Command Line Tools, Homebrew, Anki,
Claude Code, an isolated Python), then asks a few questions — name, first
language, roughly how good your English is — and builds a deck cut to your
level. Re-running it is always safe.

It stops and tells you when it needs you, for the parts it can't do for you:

- **AnkiWeb:** when Anki opens for the first time, click Sync and create a free
  account if you'll also review on a phone. On the phone, AnkiDroid (Android)
  is free; on iPhone, [ankiweb.net](https://ankiweb.net) in Safari → *Add to
  Home Screen* works for free.
- **Claude:** run `claude` once in the folder and sign in.

Then, in Claude Code (`cd ~/english && claude`), run **`/level`**: a 15-minute
placement that estimates your CEFR level and adjusts your deck.

Something not working? `./english doctor` checks every part and says how to fix it.

## Your data vs. the app

```
~/english/          the app — the same for everyone, updated with ./english update
  content/          the shared card library
  me/               YOURS: profile, journal, error log, own cards, level history
```

`me/` is never part of the app's git history, so updates can't touch it, and
nobody else sees it. Setup makes `me/` its own git repo. Push it to a
**private** remote of your own if you want a backup.

`me/profile.yml` is where you tell the app about yourself: your level, what to
prioritise, what's going on in your life (so writing prompts are about *your*
week, not a textbook's). Edit it any time.

## Updating

```bash
./english update
```

Pulls the newest version, shows what changed, refreshes Python packages, and
rebuilds your deck. Before it imports into Anki it asks whether you synced
first — see below for why that matters.

**Sharing with someone new:** send them the two install lines above. Their
progress, journal and Anki history are theirs alone; the only thing you share
is the app.

### Importing into Anki when you also use a phone

Order matters, or AnkiWeb can demand a one-way sync and you lose reviews:

1. **Sync the desktop first** (⟳ or `Y`) so it has the reviews from your phone.
2. **Quit Anki.** The import refuses to run while it's open, because two
   programs writing the collection at once would corrupt it.
3. `./english build && ./english deck`
4. **Reopen Anki and sync again** to push the updated cards out.

Card GUIDs are derived from each card's `id`, so re-importing updates cards in
place and **keeps your review history**. The collection is backed up before
every import.

## Your level

| | |
|---|---|
| `/level` (Claude Code) | Adaptive placement, ~15 min: grammar items you fill in yourself, plus a short piece of writing. A CEFR estimate overall and per area, saved to your history. `/level quick` is a monthly 5-minute re-check. |
| `./english level --efset 62` | Records a score from the free [EF SET](https://www.efset.org/) test (~50 min). Take it once a quarter as an objective anchor, since `/level` is an estimate (about ±half a band). |
| `./english level` | Your history, plus signals that update by themselves: errors per 100 words written, Anki success rate by topic, the mistakes that keep coming back. |
| `./english report` | A one-page progress report to share: level over time, practice, hardest topics. **Numbers and topic names only.** No journal text and no corrected sentences, so it's safe to send. |

Recording a new level updates your profile, and the next `./english build`
fits your deck to it. Topics more than one step above your level are left
out until you get closer.

## What's in it

**628 cards across 36 topics**, each tagged with a CEFR level, in an Anki deck
called **English Practice**:

| | |
|---|---|
| `00 …` (10 topics) | Tenses, articles, prepositions, collocations: the foundation, **authored, not from the book** |
| `1A`–`10B` (17 topics) | The AEF 5 grammar bank |
| `V01`–`V12` (9 topics) | The AEF 5 vocabulary bank, with audio |

Plus your own cards in `me/my-cards/`, which `/mine` writes from your
repeated mistakes.

The `00` modules exist because AEF 5 is a C1 *reference summary*. It assumes
you already know the tense system, articles and prepositions, and never teaches
any of them.

Deliberately cut as poor value for everyday speech: grammar 4B (inversion) and
5A (distancing), both formal written register; vocab *Conflict & warfare*,
*Sounds & the human voice*, and *Animal matters*.

## Two kinds of command — where to type what

**Slash commands are typed in Claude Code** (run `claude` in this folder). They
are defined in `.claude/commands/` and don't exist anywhere else. Typing
`/check` in a normal terminal does nothing.

**`./english …` commands are typed in Terminal**, in this folder. In practice
you rarely need them, because you can ask Claude to rebuild and it will.

## The routine

### Every day — 20–30 min

| When | Where | What |
|---|---|---|
| ~15 min | **Anki** (phone or desktop) | Do your reps. Say answers **out loud** before revealing. |
| — | **Claude Code** | `/journal` creates today's file with a prompt aimed at your weakest point |
| ~10 min | **Editor** | Write 5–8 sentences in the file it made. Delete the prompts first. |
| — | **Claude Code** | `/check` corrects it, explains each error, and logs it to `me/errors.md` |
| — | **Anki** | Press `Y` to sync, so your phone matches |
| 20:00 → | **Your phone** | If any of the above is still undone, a reminder arrives (optional, see below) |

Write about your **real life**. Never try to reproduce the sentences from your
Anki cards, because the cards already test those. The journal exists to attach
each structure to content it wasn't learned with, which is what makes it
transfer to speech.

```
reps  →  journal  →  /check  →  me/errors.md  →  /mine  →  new cards
```

That loop is the whole point. Flashcards alone teach rules you can recite but
can't use; the writing and drilling are what convert them into speech.

### Not forgetting

`./english reminders` installs an evening job that checks whether today's loop
is actually done, and pushes your phone if it isn't: gently at 20:00,
insistently at 23:30. It also adds a lock-screen widget showing your streak.
It needs a GitHub account and the free ntfy app; setup offers it, and you can
add it any time.

A day counts only when **all three** parts happened: reps cleared, journal
written, `/check` run. Two out of three breaks the streak on purpose, because
the missing step is usually the one that mattered.

Setup, escalation tiers, and troubleshooting: [`automation/README.md`](automation/README.md).

### Weekly

- `/drill`: a conversation drill on your weakest point. Takes 10–15 min.
- One **free journal entry** with no target. `/journal` does this automatically
  once a week; it's the only way to catch structures you silently avoid.

### Every 2–4 weeks

- `/mine` turns repeated errors in `me/errors.md` into new cards. Running it
  more often is pointless: it needs several entries before a pattern is real.

### Monthly and quarterly

- `/level quick` once a month; `./english report` to see or share the trend.
- [EF SET](https://www.efset.org/) once a quarter, recorded with `./english level --efset <score>`.

## Command reference

### In Claude Code

| Command | Arguments | When |
|---|---|---|
| `/level` | none, or `quick` | First day, then monthly |
| `/journal` | none, a topic (`/journal conditionals`), or `free` | Start of your writing session |
| `/check` | none (uses today's), or a path | Right after you finish writing |
| `/drill` | none (picks from your errors), or a topic | Once a week |
| `/mine` | none, or a topic to limit to | Every 2–4 weeks, **not** daily |

### In Terminal

| Command | What it does |
|---|---|
| `./install.sh` | Installs everything and sets you up; safe to re-run |
| `./english update` | Gets the newest app version and applies it |
| `./english doctor` | Checks the whole install and says how to fix problems |
| `./english status` | Today's three checkboxes, the streak, and time left |
| `./english build` | Generates audio and builds the deck file |
| `./english deck` | Imports it into Anki. **Anki must be closed**, and synced first |
| `./english level` | Level history and progress signals; `--efset N` records a test |
| `./english report` | Writes and opens your shareable progress page |
| `./english check` / `stats` | Validates card files / counts cards per topic |
| `./english reminders` | Installs evening reminders; `--uninstall` removes them |

## Notes on sources

Every card sentence, note and warning is original writing. The coursebook
only decided which structures and words each topic covers, and nothing in this
repo is copied from it. The source PDFs stay on the original author's machine
(`resources/`, never committed), and `./english check` there rejects any card
that repeats the book's wording.

The PDFs' text layer has no `ToUnicode` maps, so their IPA transcriptions are
unrecoverable garbage (`/braɪt/` extracts as `/bra1t/`). That's why cards carry
generated audio instead of phonetics.

For graded exercises with answer keys alongside this: Murphy, *English Grammar
in Use* (intermediate) for the B1–B2 foundation, and Hewings, *Advanced Grammar
in Use* for C1. Beyond that, the biggest lever for everyday English is input
volume: podcasts and shows you'd watch anyway, mined for sentences that become
cards.

## License

- **Code** (everything outside `content/`): [MIT](LICENSE).
- **Cards** (`content/`): [CC BY-SA 4.0](content/LICENSE). Copy, adapt and share
  them, commercially too, as long as you credit this repo and share your
  adapted cards under the same license.

Your own data in `me/`, including cards you write in `me/my-cards/`, belongs
to you and isn't covered by either license.
