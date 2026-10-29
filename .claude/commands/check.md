---
description: Correct a journal entry, explain each error by grammar point, and log it
argument-hint: [path to journal file, or omit for today's]
allowed-tools: Read, Edit, Write, Bash(date:*), Glob, Bash(./english dashboard:*), Bash(shasum:*), Artifact, ArtifactData
effort: high
---

Correct the writing in: $1

If no file was given, use today's entry in `me/journal/` (get the date with `date +%F`).
If that file doesn't exist, say so and stop — don't invent content.

## How to correct

Read `me/profile.yml` first. Pitch explanations at the learner's `level`, and
when an error is a typical transfer from their `native_language`, say so in a
few words — knowing *why* you make an error is half of stopping.

Read the entry, then produce a correction table. For every error:

1. **Quote the original** exactly as written.
2. **Give the correction.**
3. **Name the grammar point** using the `point:` value from the relevant file in
   `content/` or `me/my-cards/` (e.g. "6B Conditionals", "00 Future forms"). A wrong
   or unnatural word ("too much" meaning "very much", "per week" for "a week")
   is `00 Word choice`, and a word that's wrong with its partner ("make a
   photo") is `00 Collocations`; don't log either as a topic-less "Vocabulary".
   If an error maps to no existing topic, say so: that's a signal the deck has a gap.
4. **Explain in one sentence WHY**, in terms of the rule. Not "this sounds
   better" — state the rule that was broken.

Then separately list **register or naturalness notes**: things that are
grammatically correct but that a native speaker wouldn't say. Mark these clearly
as style, not errors — conflating the two is discouraging and inaccurate.

If the entry has a `## spoken` section, that part is a Whisper transcript of the
learner speaking (`./english speak`), so correct it as speech. Punctuation,
capitals and spelling are Whisper's, not the speaker's, so never log them.
Fillers ("um"), restarts and self-corrections are normal speech, not errors.
Grammar, word choice and prepositions are logged exactly as for writing. Whisper
sometimes smooths an error away, so a clean transcript is weaker evidence than
a clean written entry. After the table, give a natural spoken version of two or
three of the speaker's sentences to say aloud (the corrected meaning, the way a
native speaker would put it in conversation), and one line on the fluency
numbers in the `<!-- spoken: … -->` marker if they stand out.

If the prompt offered **words to try** (from `/journal`), say in one line which
ones were used and whether naturally. A word used wrongly is a genuine error,
logged like any other wrong word (below). A word left unused is not an error, and it
isn't logged.

Be honest. If the entry is good, say it's good and don't manufacture errors to
seem useful. If it's full of the same mistake, say that plainly — a repeated
error is the most valuable thing this command can surface.

## Then log

Append to `me/errors.md`, one line per genuine error (not style notes), in this format:

```
| 2026-08-08 | 6B Conditionals | "If I would have known" | "If I had known" | would in the if-clause |
```

Create `me/errors.md` with that table header if it doesn't exist yet.

If you gave natural spoken versions (a `## spoken` entry), append them to
`me/say-aloud.md` under a `## YYYY-MM-DD · /check` heading, each as a
`<!-- said: "…" -->` line quoting what the speaker said, then a `- ` line with
the natural version. `./english say me/say-aloud.md` skips headings and
comments, so it reads only the natural versions, for listening and repeating.
Create the file with a `# Say it aloud` heading if it doesn't exist. Never put
these sentences in the journal file: progress counts the words written there.

Then append this marker as the last line of the journal file you corrected:

```
<!-- checked: 2026-08-08T21:14 · 3 errors -->
```

Use the current time (`date +%FT%H:%M`) and the number of genuine errors, zero
included. **Always write it, even for a flawless entry** — it is the only record
that `/check` ran, and the streak in `build/status.py` counts a day as done only
if it's there. Error rows can't stand in for it: a perfect entry logs none.

If the same grammar point now clearly dominates `me/errors.md` and isn't in the
profile's `weak_areas`, add it there — the profile should follow the evidence.

Finally, tell me the single grammar point I should focus on next, based on what
recurs in `me/errors.md` as a whole — not just today's entry.

## Dashboard

If `me/dashboard/artifact-url` exists, finish by refreshing the dashboard the
way `.claude/commands/dashboard.md` describes, and add its one-line summary to
your reply. If it doesn't exist, skip this.
