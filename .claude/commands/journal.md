---
description: Create today's journal entry with a prompt aimed at your current weak point
argument-hint: [optional topic, or "free" for an unprompted entry]
allowed-tools: Read, Write, Glob, Grep, Bash(date:*)
---

Create today's journal entry at `me/journal/YYYY-MM-DD.md` (get the date with `date +%F`).

If the file already exists, say so and show it — never overwrite work.

Read `me/profile.yml` first: `level` sets how demanding the prompt is,
`life_context` supplies the real situations to write about, and `weak_areas`
is the fallback target.

## Choosing the target structure

If $1 names a topic, use it. If $1 is "free", see *Free entries* below. Otherwise
pick the target yourself:

1. Read `me/errors.md`. The grammar point with the most entries in the last two
   weeks is the default target — that's demonstrated weakness, not guesswork.
2. If `me/errors.md` is thin (under ~5 entries), fall back to the profile's
   `weak_areas`, and failing that to the most recently added `content/` topic
   at or below the learner's level.

Say which target you picked and why, in one line.

## Writing the prompt

Produce a file with:

- A `# YYYY-MM-DD` heading.
- One line naming the target structure.
- A prompt asking about **the writer's real life** — actual plans, work, people,
  the situations in `life_context`. Never a generic textbook scenario. Real
  content is what makes the structure stick, and it's the only way to find out
  what the writer actually reaches for.
- 4–6 bullets, each describing a *situation* that naturally requires a different
  form of the target structure. Describe the situation, never name the form —
  "something you've arranged with another person", not "use present continuous".
  Naming it turns production into translation.
- A line telling the writer to delete the prompts and write below, then run `/check`.

Aim for 5–8 sentences of output. Enough to show a pattern, short enough to
finish in ten minutes.

## Free entries

Roughly once a week, make it a free entry instead: no target, no bullets, just a
prompt to write about anything from the last few days. These matter because a
targeted prompt can't reveal **avoidance** — the structures they silently steer
around. A free entry can. If there was no free entry in the last 7 days, prefer
one regardless of what $1 says, and explain why.

## Recording what you chose

Append one `DATE<TAB>TARGET` line to `me/journal/.prompts.log` every time, using
`free` for untargeted entries. **Read that file, not the journal entries, to
decide whether a free entry is due** — the prompt text is deleted when the entry
is written, so a free entry leaves no trace in the file itself.

## Checking for avoidance

Before choosing, grep the last week or two of `me/journal/` for the forms the
target would require. A structure with **zero occurrences across several
entries** is being avoided, and avoidance never appears in `me/errors.md` — you
cannot log an error in something never attempted. If you find a structure the
deck teaches but that the writer has never once produced, prefer it over the
frequency-based default, and say that's what you're doing.
