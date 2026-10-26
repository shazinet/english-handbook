---
description: Your home screen: path, next step, quests, and a practice activity to start
argument-hint: [activity: call, roleplay, drill, mistakes, story, speak, listen — or omit]
allowed-tools: Read, Edit, Write, Glob, Grep, Bash(date:*), Bash(mkdir:*), Bash(./english:*), Bash(shasum:*), Artifact, ArtifactData
---

Open the practice home: $1

Run `./english home` and show its output as it is, in a code block.

Then:

- **$1 names an activity**: start it right away by following that command's
  file in `.claude/commands/` exactly as if I had typed it: `call.md`,
  `roleplay.md`, `drill.md`, `mistakes.md`, `story.md`, `journal.md`,
  `check.md`. For `speak`, tell me to run `./english speak` myself (it waits
  for Enter, which only works in my terminal), then `/check`. For `listen`,
  ask how many minutes and what, and run `./english listen MINUTES --what "…"`.
- **No $1**: recommend one in a line, using `./english home --json`:
  1. The `next` step, if its kind is `loop`: the daily loop comes first,
     because a day only counts when Anki, the journal and /check are all done.
  2. Otherwise, an open quest that one activity would finish.
  3. Otherwise, the next lesson on the path.

  Then ask which one to start. Use AskUserQuestion with the recommendation
  first, and start whatever I pick by following its command file.

Anki itself can't be started from here: for **Words**, say how many are due
and to open Anki.
