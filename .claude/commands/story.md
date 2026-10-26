---
description: A short story about your life, read aloud, then questions and a retell
argument-hint: [a situation or theme, or omit to pick one]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(date:*), Bash(mkdir:*), Bash(./english say:*), Bash(./english speak:*), Bash(./english vocab:*), Bash(./english home:*), Bash(./english log:*), Bash(./english dashboard:*), Bash(shasum:*), Artifact, ArtifactData
---

Tell me a story about: $1

This is listening and reading practice first, speaking second: input I can
understand, about my real life, carrying the structure I'm working on.

## Writing it

Read `me/profile.yml`. Then:

- **Situation**: $1 if given, otherwise something from `life_context` that
  hasn't been a story in the last two weeks (check `me/stories/`).
- **Structure**: the path's current unit (`./english home --json`,
  `unit.point`). Load its card file from `content/` or `me/my-cards/`, and use
  the structure naturally four to six times. Never name or highlight it.
- **Words**: if `./english vocab --tsv -n 60` works, work in three words from it
  that fit the story.
- **Length and level**: 150–250 words, at the learner's level plus a little.
  Everyday register, with some dialogue, since dialogue is what I most need to
  hear. Characters are generic (a landlord, a colleague, a friend), never real
  people from the profile.

Save it as `me/stories/YYYY-MM-DD-short-slug.md`: a `# Title` heading, then
the story. Don't show me the text yet.

## Listening

Run `./english say me/stories/<file>.md --save me/stories/<file>.m4a`, which
reads it aloud and keeps the audio so I can replay it. Then ask:

1. **Three to five comprehension questions**, one at a time: one about the
   gist, the others about details that depend on the target structure (who
   *had* done what, what *would* have happened). Wait for each answer and
   correct only meaning, not my grammar, in a line.
2. Now show the text, so I can read what I heard.

## Retell

Ask me to retell the story in my own words, in four to six sentences. I can
type it, or speak it with `./english speak --turn` (run it for me; it prints
what I said). Then correct the retell the way `/check` does: a table of genuine
errors with the `point:`, the fix and a one-line reason, spoken-text rules if I
spoke. Append those errors to `me/errors.md` in the `/check` format.

Append to the story file, under `## retell`, my retell and a line
`<!-- story: N questions · M right · retold -->`.

## Log

```
./english log story --point "UNIT POINT" --items N --correct M --goal yes
```

`--goal yes` means I did the retell; leave it off if I skipped it.

## Dashboard

If `me/dashboard/artifact-url` exists, finish by refreshing the dashboard the
way `.claude/commands/dashboard.md` describes, and add its one-line summary to
your reply. If it doesn't exist, skip this.
