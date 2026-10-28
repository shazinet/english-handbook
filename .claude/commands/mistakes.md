---
description: Re-correct your own logged errors, one at a time, until they're resolved
argument-hint: [grammar point to limit to, or omit for the most recurring ones]
allowed-tools: Read, Glob, Grep, Bash(date:*), Bash(./english mistakes:*), Bash(./english log:*), Bash(./english home:*), Bash(./english dashboard:*), Bash(shasum:*), Artifact, ArtifactData
effort: medium
---

Run a mistakes round on: $1

Every row in `me/errors.md` is a mistake I actually made. This round shows them
back to me and asks for the fix, the way a review of wrong answers does. A
mistake is **resolved** once I've fixed it on two different days.

## Picking the mistakes

Run `./english mistakes --next 10`, with `--point "$1"` if a point was given.
If none was given and the path has a current unit (`./english home --json`,
`unit.point`) whose "Fix your mistakes" lesson isn't done, use that point, and
say so. If the list comes back empty, say there's nothing open for that point
and stop.

The JSON gives each mistake's `key`, `wrong`, `right`, `why` and `point`.

## The round

Read `me/profile.yml` for the learner's level and native language.

For each mistake, **one at a time**:

1. Show the wrong version as a short scene, so the fix depends on meaning, not
   on spotting a typo: a line of context, then the sentence. For example:
   *You're telling a friend about last month: "I am living here since two weeks."*
   Ask me to say it correctly. Never show the correction or name the rule
   before I answer.
2. Wait for my answer.
3. Judge it. **ok** means my version fixes the logged error and is natural; a
   different correct fix counts (there's often more than one). Anything that
   keeps the error, or swaps it for a new one, is a **miss**.
4. Record it straight away: `./english mistakes --mark KEY ok` (or `miss`).
5. Reply in one or two lines: on ok, confirm and, if useful, give the most
   natural version; on a miss, give the fix and the rule in one sentence.

Don't log misses to `me/errors.md`: they're the same error, already logged, and
logging them again would double its count. Do log a **new** error I make while
answering, in the `/check` format.

## At the end

Give the score, which mistakes are now resolved (the `--mark` output says so),
and which point the misses cluster on. If a point keeps missing, suggest `/mine`
for it.

Then record the round. `--items` is how many I answered, `--correct` how many
were ok, and `--point` the point if the round was limited to one:

```
./english log mistakes --point "00 Prepositions" --items 10 --correct 8
```

## Dashboard

If `me/dashboard/artifact-url` exists, finish by refreshing the dashboard the
way `.claude/commands/dashboard.md` describes, and add its one-line summary to
your reply. If it doesn't exist, skip this.
