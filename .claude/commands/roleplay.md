---
description: Role-play a real situation from your life, with a goal to achieve
argument-hint: [a situation, e.g. "returning a faulty phone", or omit to pick from your profile]
allowed-tools: Read, Edit, Write, Bash(date:*), Glob, Grep, Bash(./english dashboard:*), Bash(./english log:*), Bash(shasum:*), Artifact, ArtifactData
effort: medium
---

Run a role-play of: $1

`/drill` practises a grammar point; this practises a **situation**. The test is
whether I get what I came for, in English, under a little pressure, the way it
happens in real life.

## Setting it up

Read `me/profile.yml`: `life_context` supplies the situation, `level` the
difficulty, `weak_areas` what to listen for. Skim the last month of
`me/errors.md` for my most frequent grammar points.

If $1 names a situation, use it. Otherwise pick one I'll plausibly face soon,
from `life_context`. Typical shapes: viewing a place to rent, an appointment at a
government office, signing up for or cancelling a service, a problem with a bill,
a meeting or a one-to-one at work, returning something to a shop, making plans
with someone new. Don't repeat a scene from the last two weeks (check
`me/roleplay.log` if it exists).

Then give me a short brief, in this order, and nothing else:

1. **The scene** in two lines: where we are, who you are.
2. **My goal**: one concrete outcome I need to get, which the other person won't
   simply hand over. For example: a lower deposit, an earlier appointment, a
   refund rather than store credit, a deadline moved. Make it reachable, but only
   if I ask clearly, give a reason and handle one objection.
3. **Two or three phrases that might help**, natural for the scene. Not a script.

## Playing it

- Stay in character: a real, busy, mildly unhelpful person, not a teacher. Speak
  the way people actually talk in that place, at my level plus a little.
- **One turn at a time.** Wait for my reply.
- Push back once or twice: a policy, a missing document, "that's not possible".
  Don't cave until I've earned it, and don't stall forever either.
- **Don't correct me during the scene.** Interrupting breaks exactly the thing
  this practises. Note errors silently for the end. The exception: if I'm
  so unclear that a real person wouldn't understand, react the way they would
  ("Sorry, you mean…?").
- 8–12 turns. End the scene naturally when the goal is won, clearly lost, or
  we run out of road.

If I'd like it to be speaking practice, I can dictate my replies (macOS
dictation: press the microphone key or Fn twice). Dictation tidies grammar, so
say at the end that some errors may have been hidden.

## Debrief

Step out of character and give:

1. **Goal**: achieved, partly, or not, and the moment it turned.
2. **What worked**: one or two things I did well, specifically.
3. **Errors**: a short table in `/check` style: what I said, the fix, the
   `point:` from `content/` or `me/my-cards/`, and a one-line reason. Only genuine
   errors, not style.
4. **Phrases you could have used**: three or four natural expressions for this
   scene I didn't use, each in a sentence from our actual conversation. This is
   the part I'll reuse, so make them everyday-register and high-value.

## Then log

Append the genuine errors to `me/errors.md` in the format `/check` uses, dated today
and tagged with the grammar point. Append `DATE<TAB>SCENE<TAB>achieved|partly|not`
to `me/roleplay.log`. Append the **Phrases you could have used** sentences to
`me/say-aloud.md` under `## YYYY-MM-DD · /roleplay (SCENE)`, in the format
`.claude/commands/check.md` describes; the `said:` comment quotes my line each
one improves on, or names the moment it fits if I said nothing there. If the
same error came up twice or more, suggest `/mine`.

Record the session for XP (`--goal yes` only when the goal was achieved in
full; `--minutes` is a rough length of the scene):

```
./english log roleplay --goal yes --minutes 12 --note "SCENE"
```

## Dashboard

If `me/dashboard/artifact-url` exists, finish by refreshing the dashboard the
way `.claude/commands/dashboard.md` describes, and add its one-line summary to
your reply. If it doesn't exist, skip this.
