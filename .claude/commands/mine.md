---
description: Turn recurring errors from me/errors.md into new cloze cards
argument-hint: [optional grammar point to limit to]
allowed-tools: Read, Edit, Write, Glob, Grep, Bash(./english check:*)
---

Read `me/errors.md` and turn my recurring errors into new cards.

Scope: $1 (if empty, consider all of `me/errors.md`).

Also read any `## input` sections at the bottom of files in `me/journal/` —
phrases mined from podcasts and series (see `me/input-plan.md` if it exists). Treat a phrase as
card-worthy if it appears twice, or if it directly answers an error already in
`me/errors.md`. A phrase noted once and never repeated is not yet worth a card.

## What to mine

Only mine errors that are **worth a card**:

- The same error appearing **two or more times** — a repeated error is a real
  gap, not a slip.
- A single error that reveals a rule I clearly don't know, as opposed to a typo
  or a one-off lapse of attention.

Skip typos, and skip anything already well covered by an existing card. Check
first — read the relevant files in `content/` and `me/my-cards/` and see whether the point is
already tested. Adding a near-duplicate card wastes daily reps, which is the
scarcest resource in this whole system.

If nothing meets the bar, say so and stop. An empty result is a good outcome.

## How to write the cards

Follow the authoring rules in `CLAUDE.md` — cloze only, everyday register, one
point per card, never IPA.

Write cards **based on my own sentences** from `me/errors.md` where possible,
corrected. A card built from a mistake I actually made is far stickier than a
textbook example of the same rule.

Mined cards are **mine, not the app's**: write them to `me/my-cards/`, never
into `content/` (that's shared with everyone who uses the app). Use one file per
topic, named like the shared file it extends (`me/my-cards/06b-conditionals.yml`),
with the **exact same `point:`** so the cards land in the same Anki subdeck.

Ids are `<handle>-<topic>-m01`, `<handle>-<topic>-m02`, … where `handle` comes
from `me/profile.yml` — the build rejects own cards without it, because the
prefix is what lets a card be shared later without colliding with anyone
else's. Continue the numbering from cards already there. Never reuse or rewrite
an existing id.

## Then

Run `./english check` and confirm it passes.

Report what you added and which errors you deliberately skipped, with the reason.
Remind me to rebuild and re-import if I want them on my phone today.
