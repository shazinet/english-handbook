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

**744 cards across 44 topics**, each tagged with a CEFR level, in an Anki deck
called **English Practice**:

| | |
|---|---|
| `00 …` (18 topics) | Tenses, articles, prepositions, collocations, the passive, reported speech, questions, quantifiers, comparatives, too/enough/so/such, agreement, word form: the foundation, **authored, not from the book** |
| `1A`–`10B` (17 topics) | The AEF 5 grammar bank |
| `V01`–`V12` (9 topics) | The AEF 5 vocabulary bank, with audio |

Plus your own cards in `me/my-cards/`, which `/mine` writes from your
repeated mistakes.

The `00` modules exist because AEF 5 is a C1 *reference summary*. It assumes
you already know the tense system, articles and prepositions, and never teaches
any of them. The same goes for the passive, reported speech, questions,
quantifiers and comparatives; those topics were picked by checking the open
CEFR-J Grammar Profile against the deck.

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

On days you'd rather talk, `./english speak` replaces the writing step. Run
`/journal` first if you want a prompt, then speak for two or three minutes
about it or about your day, and the transcript lands in today's
journal for `/check`, with words per minute, long pauses and fillers tracked in
`./english level`. It needs `./install.sh --speech` once. It records from the
Mac's current input unless `speech.microphone` in your profile names one
(`./english speak --list-mics` shows the names).

Write about your **real life**. Never try to reproduce the sentences from your
Anki cards, because the cards already test those. The journal exists to attach
each structure to content it wasn't learned with, which is what makes it
transfer to speech.

```
reps  →  journal  →  /check  →  me/errors.md  →  /mine  →  new cards
```

That loop is the whole point. Flashcards alone teach rules you can recite but
can't use; the writing and drilling are what convert them into speech.

### Home, path and practice

Run `./english` on its own (or `/practice` in Claude Code) for the home screen:

- **Next step.** The daily loop always comes first; after that, the next lesson
  on your path.
- **The path.** One unit per topic, ordered by how often each shows up in your
  error log lately. The unit you're on stays current until you finish it; new
  errors only reorder the units after it. Each unit has four lessons: learn a day's batch of its cards
  (`./english deck` puts the current unit's new cards first in your normal
  Anki session, so there's no subdeck to open), a `/drill`, a
  journal entry about it, and a `/mistakes` round. Every lesson is ticked from
  what you actually did. Finishing a unit opens a chest worth 50 XP, and stars
  come from retention and from staying error-free.
- **Daily quests.** Three a day, fixed for the whole day, worth 10 XP each,
  plus 20 for all three.
- **Practice menu:**

  | Activity | Command | XP |
  |---|---|---|
  | Video call | `/call` | 20, +10 a minute |
  | Roleplay | `/roleplay` | 30, +20 if you win |
  | Drill | `/drill` | 30, +2 per correct form |
  | Mistakes | `/mistakes` | 3 per fix |
  | Words | Anki | 1 per review |
  | Story | `/story` | 25, +10 for the retell |
  | Speak | `./english speak` | 10 a minute |
  | Radio | `./english listen 20` | 1 a minute, up to 60 a day |

The dashboard shows the same path, quests and practice menu. None of it changes
what counts as a day: that's still reps, a journal entry and `/check`.

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
  `/drill speak` asks out loud and you answer into the mic: better for speed,
  while typed drills catch more errors, because speech-to-text tends to tidy
  up grammar.
- `/roleplay`: a real situation from your life (viewing a flat, an office
  appointment, a work meeting) with a goal to win, like a lower deposit or an
  earlier date. No corrections until the end, then a debrief with the phrases
  you could have used.
- One **free journal entry** with no target. `/journal` does this automatically
  once a week; it's the only way to catch structures you silently avoid.

### Every 2–4 weeks

- `/mine` turns repeated errors in `me/errors.md` into new cards. Running it
  more often is pointless: it needs several entries before a pattern is real.

### Monthly and quarterly

- `/level quick` once a month; `./english report` to see or share the trend.
- [EF SET](https://www.efset.org/) once a quarter, recorded with `./english level --efset <score>`.

## How it works

Nothing in the app has a "mark as done" button. Every tick, streak, XP point
and badge is worked out from evidence you leave anyway: Anki's review log,
the files in `me/journal/`, `me/errors.md`, and one line per practice session
in `me/activity.log`. So the home screen, the dashboard and the reminders
can't disagree, and none of them can be gamed by clicking.

### The cards

- **Cloze only.** Every card hides part of a sentence you have to *produce*,
  never a word to recognise. A hint in place of `[...]` tells you what kind of
  answer goes there (the base verb for a tense gap, the meaning for a word
  gap) whenever the sentence alone wouldn't.
- **Your deck is cut to you.** `./english build` collects the shared cards in
  `content/` up to your profile's `deck.max_level` (minus anything in
  `deck.skip`), plus your own cards in `me/my-cards/`, generates the audio,
  and writes `english.apkg`.
- **Importing keeps your history.** `./english deck` backs up your collection,
  then imports. Each card's identity comes from its permanent `id`, so an
  edited card updates in place and keeps its reviews. It refuses to run while
  Anki is open, or when a card file is newer than the last build.
- **Scheduling is Anki's.** The import turns on FSRS and sets the "English
  Practice" preset to your `deck.new_per_day` (6 by default). It also puts new
  cards in path order, so your normal daily session brings the current unit's
  cards first; there's no subdeck to pick.

### A day, and the streak

A day counts only when all three happened:

1. **Reps:** you answered cards today *and* nothing is left due.
2. **Writing:** today's journal has at least 30 words of your own. Only text
   after the prompt's last line ("…then run `/check`") counts, so a kept
   prompt is never mistaken for writing. A spoken section counts the same.
3. **`/check`:** the entry carries the `<!-- checked: … -->` marker `/check`
   writes, even for a perfect entry.

The streak is the number of complete days in a row. If reminders are
installed, a job checks every half hour through the evening and sends one
push per tier, getting more insistent (20:00, 22:00, 23:00, 23:30), only while
the day is still incomplete.

### `/journal`: today's prompt

It picks one target structure and writes a prompt about your real life
(`life_context` in your profile) with 4–6 situations that each need a
different form of it, without naming the form. How it picks:

1. The current unit on your path. If you've already written about that unit,
   the grammar point with the most errors in the last two weeks.
2. A structure you have *never* produced in recent entries beats both,
   because avoidance never shows up in the error log.
3. Once a week it gives a free entry with no target instead, which is the only
   way to see what you avoid when nothing steers you.

It also offers three frequent words at your level that you haven't used yet,
and records its choice in `me/journal/.prompts.log`. That record is how the
path knows which unit an entry belongs to.

### `./english speak`: the entry, out loud

It records from your profile's microphone until you press Enter (5 minutes at
most), then transcribes on this Mac with Whisper; nothing is uploaded.
Whisper is asked for a verbatim transcript, so it keeps "um"s and restarts,
but it still tends to tidy grammar. The text goes under a `## spoken` heading
in today's entry, with a marker carrying the numbers: speaking time, words
per minute, pauses over a second, and fillers. The recording is kept in
`me/recordings/`.

### `/check`: corrections

Every error gets a row: what you wrote, the correction, the grammar point
(named exactly like the deck topic it belongs to), and the rule in one
sentence. Style notes are listed separately and never logged. In a spoken
section, punctuation, spelling, fillers and self-corrections are never errors.
Grammar, word choice and prepositions count as they would in writing. Each
error is appended to `me/errors.md`, which everything else reads: the path's
order, the next `/journal` target, `/mine`, `/mistakes` and your level
signals. If one point clearly dominates and isn't in your profile's
`weak_areas`, it's added there.

For a spoken entry, `/check` also gives two or three of your sentences the way
a native speaker would say them, and saves them in `me/say-aloud.md`. `/call`
adds its "Say it like this" lines there, and `/roleplay` adds its "Phrases you
could have used". Each sentence sits under a comment holding what you actually
said, and `./english say me/say-aloud.md` reads only the natural versions, so
you can listen and repeat them.

### `/mine`: errors become cards

It reads all of `me/errors.md` and keeps only errors that are worth a card:
ones you've made two or more times, or one that shows you don't know the
rule. It skips anything an existing card already tests. Each new card is built
from your own sentence, corrected, and goes into `me/my-cards/` under the same
topic as the shared cards, so it joins that subdeck. Then
`./english build && ./english deck` brings them into Anki.

### The path

- **Units:** one per topic in your deck, ordered by how often each shows up in
  your errors over the last 60 days. Once a unit becomes current, it stays
  current until you finish it (it's kept in `me/.state/path-unit`).
- **Lessons:** each is ticked from evidence, never by hand:
  - **Learn the cards:** one day's batch of the unit's new cards studied in
    Anki
  - **Conversation drill:** a `/drill` on that point
  - **Write about it:** a checked journal entry whose target was that point
  - **Fix your mistakes:** a `/mistakes` round on that point, or no open
    mistakes on it
- **Finishing a unit** opens a chest (50 XP) and earns ★. ★★ needs 85% recall
  on the unit's cards; ★★★ needs no error on the point for 30 days and 80% of
  its cards mature.

Lessons aren't daily tasks: a unit can take several days.

### Home and the next step

`./english` (or `/practice`) shows one next step. While today isn't complete,
it's the missing part of the day, in order: Anki, then the journal, then
`/check`. After that, it's the next lesson of the current unit, with the
exact command to run.

### XP, levels, quests and badges

- **XP** rewards production over clicking: 1 per Anki review, but 20 for a
  journal entry, +1 per 10 words, 10 for `/check`, 10 per minute spoken, and 30
  for a complete day. Practice sessions, quests and chests add more (the
  practice menu above lists each).
- **Levels** get slowly more expensive (level *n* needs 150 × (*n*−1)^1.5 XP).
  Titles change at levels 5, 10, 15, 20 and 30.
- **Quests:** three a day, picked from the date, so they stay the same all day.
  A quest is offered only if it can be done, judged from how things stood when
  the day began.
- **Weekly goals:** 5 complete days, 600 words, 10 minutes spoken, 1,000 XP.
- **Badges:** 19 badges, each with Bronze, Silver and Gold. An unlocked badge
  shows what earned it, and every badge below Gold shows the rule for its next
  tier and how far you are.

None of this changes what counts as a day.

### Practice activities

Each one writes a line to `me/activity.log` when it ends, which is what earns
its XP and ticks path lessons. Errors are logged to `me/errors.md` exactly as
`/check` logs them.

- **`/drill`:** 8–10 questions whose natural answers need one structure,
  without naming it, getting harder as you get them right. You get one line of
  feedback after each answer. `/drill speak` asks out loud and records your
  answers. Because Whisper can tidy grammar, a spoken answer that looks
  suspiciously perfect gets asked again.
- **`/roleplay`:** a typed scene from your life with a concrete goal the other
  person won't simply give you. No corrections until the end.
- **`/call`:** the same idea, spoken both ways. Claude's lines are read aloud;
  your answer records automatically from when you start speaking until 2.5
  seconds of silence, which is short on purpose, to keep you talking. A turn
  waits 20 seconds for you to start, lasts 90 seconds at most, and every
  turn's audio is saved. Corrections and your words per minute come after the
  call, which is saved in `me/calls/`.
- **`/mistakes`:** your own logged errors, shown one at a time for you to
  rewrite. An error is *resolved* once you've fixed it on two different days.
  A miss isn't logged again, so it doesn't inflate your error counts.
- **`/story`:** a short story about your life, carrying the current unit's
  structure, read aloud and saved in `me/stories/`. Then comprehension
  questions and a retell, typed or spoken.
- **`./english listen 25 --what "…"`:** logs listening time (podcasts,
  series). `./english say "…"` reads any text aloud in your card voice.

### Level and reports

`/level` is an adaptive placement: grammar items that get harder or easier
with your answers, plus a short piece of writing. Recording a level updates
your profile: `level`, `deck.max_level` (one step above, capped at C1) and
`weak_areas`. Between placements, `./english level` shows signals that update
by themselves: errors per 100 words, Anki recall by topic, and speaking pace.
`./english report` makes a shareable page with numbers and topic names only:
no journal text and no corrected sentences.

### The dashboard

`/dashboard` keeps a private page on claude.ai with all of the above in charts:
the path, quests, badges, XP, Anki recall, errors by topic and your recent
corrections. The loop commands (`/journal`, `/check`, `/drill`, `/call`,
`/mine`…) refresh it as their last step. Anki reviews alone can't trigger a
refresh, so they appear the next time one of those runs.

It contains your corrected sentences, which is fine only because it's private.
Share `./english report` instead.

## Command reference

### In Claude Code

| Command | Arguments | When |
|---|---|---|
| `/level` | none, or `quick` | First day, then monthly |
| `/journal` | none, a topic (`/journal conditionals`), or `free` | Start of your writing session |
| `/check` | none (uses today's), or a path | Right after you finish writing |
| `/drill` | none (picks from your errors), or a topic; add `speak` to answer out loud | Once a week |
| `/roleplay` | none (picks from your life), or a situation | Once a week |
| `/mine` | none, a topic to limit to, or `vocab` | Every 2–4 weeks, **not** daily |
| `/practice` | none, or an activity (`call`, `mistakes`, `story`…) | Whenever you want something to do |
| `/mistakes` | none, or a topic | Any day: re-correct your own logged errors; two good days resolves one |
| `/story` | none, or a situation | A story about your life read aloud, questions, then a retell |
| `/call` | none, or who to call | A spoken call: Claude talks, you answer into the mic (needs `--speech`) |

### In Terminal

| Command | What it does |
|---|---|
| `./install.sh` | Installs everything and sets you up; safe to re-run |
| `./english update` | Gets the newest app version and applies it |
| `./english doctor` | Checks the whole install and says how to fix problems |
| `./english` | The home screen: path, next step, daily quests, practice menu (`./english help` lists commands) |
| `./english status` | Today's three checkboxes, the streak, and time left |
| `./english listen 25 --what "…"` | Logs listening time (podcasts, series) for XP and quests |
| `./english say "…"` | Reads text, or a file, aloud in your card voice |
| `./english speak` | Talk instead of writing: records you, transcribes on this Mac, adds it to today's journal for `/check` (`--file memo.m4a` for a phone recording) |
| `./english build` | Generates audio and builds the deck file |
| `./install.sh --speech` | Optional: Kokoro voices for card audio and Whisper for `speak` (~1.5 GB) |
| `./english deck` | Imports it into Anki. **Anki must be closed**, and synced first. Refuses a build older than your cards: run `./english build` first |
| `./english level` | Level history and progress signals; `--efset N` records a test |
| `./english report` | Writes and opens your shareable progress page |
| `./english check` / `stats` | Validates card files / counts cards per topic |
| `./english vocab` | The most frequent words at your level that no card tests (`--fetch` once first; `--word X` looks one up) |
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

Audio comes from macOS `say` by default. After `./install.sh --speech`, set
`audio.engine: kokoro` in `me/profile.yml` for [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)
(Apache 2.0), a far more natural neural voice, in a US or UK accent
(`audio.accent`). `audio.cards: all` gives every card a spoken sentence, not
just vocabulary. Vocab cards also link to [YouGlish](https://youglish.com),
where you hear the word in real speech.

For graded exercises with answer keys alongside this: Murphy, *English Grammar
in Use* (intermediate) for the B1–B2 foundation, and Hewings, *Advanced Grammar
in Use* for C1. Beyond that, the biggest lever for everyday English is input
volume: podcasts and shows you'd watch anyway, mined for sentences that become
cards.

### Open data

`./english vocab` and the vocabulary line in `./english level` use open word
lists, downloaded into `data/` (gitignored) by `./install.sh` or
`./english vocab --fetch`. They decide which words to look at, never what a
card says. Card sentences stay original.

- **NGSL 1.2 and NGSL-Spoken 1.2**: Browne, C., Culligan, B. (2013). *The New
  General Service List*. [newgeneralservicelist.com](https://www.newgeneralservicelist.com),
  CC BY-SA 4.0.
- **CEFR-J Wordlist 1.5**: compiled by Yukio Tono, Tokyo University of Foreign
  Studies, via [openlanguageprofiles/olp-en-cefrj](https://github.com/openlanguageprofiles/olp-en-cefrj).
  Free for research and commercial use with citation.
- **Octanove Vocabulary Profile C1/C2 1.0**: Octanove Labs, CC BY-SA 4.0 (same repository).
- **CEFR-J Grammar Profile 20180315**: same terms as the wordlist; used only to
  check which grammar topics the deck covers.

## License

- **Code** (everything outside `content/`): [MIT](LICENSE).
- **Cards** (`content/`): [CC BY-SA 4.0](content/LICENSE). Copy, adapt and share
  them, commercially too, as long as you credit this repo and share your
  adapted cards under the same license.

Your own data in `me/`, including cards you write in `me/my-cards/`, belongs
to you and isn't covered by either license.
