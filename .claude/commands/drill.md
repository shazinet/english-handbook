---
description: Run a spoken-style conversation drill targeting a weak grammar point
argument-hint: [grammar point, e.g. "conditionals" — or omit to pick from me/errors.md]
allowed-tools: Read, Edit, Write, Bash(date:*), Glob, Grep, Bash(./english dashboard:*), Bash(./english log:*), Bash(./english home:*), Bash(shasum:*), Artifact, ArtifactData
---

Run a conversation drill on: $1

If no topic was given, drill the current unit on the learner's path: run
`./english home --json` and take `unit.point`. The path ranks unfinished units
by recent errors, so this is the point `me/errors.md` says is weakest. Say
which one you picked and why. (If there's no unit, pick the grammar point that
appears most often in `me/errors.md` in the last month.)

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

Record the session, which is what earns its XP and ticks the path's drill
lesson. `--point` is the exact `point:` value, `--items` the turns where the
target structure was called for, `--correct` how many of those I got right:

```
./english log drill --point "6B Conditionals" --items 9 --correct 7
```

## Dashboard

If `me/dashboard/artifact-url` exists, finish by refreshing the dashboard the
way `.claude/commands/dashboard.md` describes, and add its one-line summary to
your reply. If it doesn't exist, skip this.
