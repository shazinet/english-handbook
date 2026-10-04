---
description: Estimate my CEFR level with a short adaptive placement, and record it
argument-hint: [omit for the full placement (~15 min), or "quick" for a monthly re-check]
allowed-tools: Read, Glob, Grep, Bash(date:*), Bash(./english level:*)
---

Estimate my English level: $1

This is a placement, not a lesson. Its job is an honest CEFR estimate (A1–C2)
per area and overall, recorded so progress can be tracked and the deck cut to
fit. Keep teaching out of it until the end.

## Before starting

Read `me/profile.yml`, `me/level-history.yml` (if any), `me/errors.md`, and the
last few entries in `me/journal/`. Existing writing is evidence too: weigh it
alongside the placement, and say so if the two disagree.

Tell me in two lines what's about to happen and roughly how long it takes.

## Part 1 — grammar and vocabulary in use (adaptive)

Full placement: **14–16 items**. `quick`: **8 items**.

- **One item at a time.** Wait for my answer before the next one.
- Each item is a short everyday sentence with a gap I must **fill in myself** —
  production, never multiple choice. Give a hint in brackets when the target is
  a verb form, e.g. `If I ___ (know) earlier, I'd have called you.`
- Cover these areas, roughly evenly: tenses (present / past / perfect / future),
  conditionals and unreal past, articles and countability, prepositions,
  modals, verb patterns (gerund / infinitive), vocabulary and collocation.
- Use the shared topics in `content/` as the syllabus — each file's `level:`
  says where a structure sits — but **write new sentences**. Never reuse a card's
  sentence: I may have memorised it in Anki, which would measure memory, not level.
- Start at B1. After two right at a level, step up; after two wrong, step down.
  Track where each area tops out.
- After each answer reply only "✓" or "✗ — <correct form>". No explanations yet.

## Part 2 — writing

Full placement: ask for **100–150 words** on something from my real life
(`life_context` in the profile), with a prompt that invites past, present and
future, and at least one hypothetical. `quick`: skip this and assess the journal
entries written since the last placement instead.

Judge it against the CEFR descriptors for **range** (variety of structures and
vocabulary), **accuracy** (how often errors occur and whether they block
meaning) and **coherence** (linking, organisation). Don't correct it line by line.

## Result

Give me:

1. **Overall level**, with one sentence of evidence.
2. **Per area** (tenses, conditionals, articles, prepositions, modals,
   verb-patterns, vocabulary): a CEFR level each.
3. **The two weakest areas** — these become the profile's `weak_areas`.
4. **Confidence.** Be honest: this is an estimate from a short sample, roughly
   ±half a band. If Part 1 and Part 2 disagree, say which you trust more and why.
5. Now the teaching: the three mistakes from the placement most worth fixing,
   with the rule for each.

Then record it — one command, which also updates the profile:

```
./english level --record <LEVEL> --areas "tenses=B2,conditionals=B1,..." --weak "<area>,<area>" --note "<one line of evidence>"
```

Finish by suggesting the free EF SET test (efset.org, ~50 min) once a quarter
as an objective anchor — recorded with `./english level --efset <score>` — and
remind me that a changed level reaches the deck after:
sync Anki → quit Anki → `./english build` → `./english deck`.
