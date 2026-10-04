---
description: Run a spoken-style conversation drill targeting a weak grammar point
argument-hint: [grammar point, e.g. "conditionals" — or omit to pick from me/errors.md]
allowed-tools: Read, Edit, Write, Bash(date:*), Glob, Grep
---

Run a conversation drill on: $1

If no topic was given, read `me/errors.md` and pick the grammar point that appears
most often in the last month. Say which one you picked and why.

## How to run the drill

Read `me/profile.yml` for the learner's level and life context, and load the
relevant file(s) from `content/` and `me/my-cards/` so the drill targets the actual rules
in the deck, not a generic version of the topic.

Then run **eight to ten turns** of realistic conversation. Rules:

- Ask questions whose natural answer *requires* the target structure. For
  conditionals: "What would you have done differently about your career?" — not
  "Make a third conditional sentence." The structure should be pulled out of me
  by the situation, never named in the prompt.
- Stay in everyday register — work, travel, money, friends, plans. This is for
  conversational English, not exam practice.
- **One turn at a time.** Wait for my answer before continuing.
- After each of my answers, give brief feedback: correct any error in the target
  structure, and note anything unnatural. Keep it to a line or two, then move on
  — don't break the flow of the conversation with a lecture.
- Push difficulty up as I get things right. If I'm getting everything correct,
  say so and move to a harder variation of the structure.

## At the end

Summarise: which forms I produced correctly, which I avoided (avoidance is a
real signal — if I never once used the target structure voluntarily, say so),
and which I got wrong.

Append genuine errors to `me/errors.md` in the same format `/check` uses, tagged
with the grammar point. Then suggest whether this topic needs new cards — and if
so, run `/mine` yourself rather than telling me to.
