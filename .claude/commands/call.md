---
description: A voice call with a character: Claude speaks, you answer out loud
argument-hint: [who to call or the situation, or omit to pick one]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(date:*), Bash(mkdir:*), Bash(./english say:*), Bash(./english speak:*), Bash(./english log:*), Bash(./english dashboard:*), Bash(shasum:*), Artifact, ArtifactData
effort: low
---

Start a voice call: $1

`/roleplay` is typed; this is spoken both ways. You say your lines out loud
with `./english say`, and I answer into the microphone with
`./english speak --turn`, which starts when I speak, stops when I've been quiet
for a couple of seconds, and prints what Whisper heard. The point is real-time
listening and speaking, with no time to edit.

## Setting it up

Read `me/profile.yml` (`life_context`, `level`, `weak_areas`). Choose a
character and a reason for the call: $1 if given, otherwise something from
`life_context` I'll plausibly face, such as a friend making weekend plans, a
landlord about a repair, a colleague about a deadline, or a clinic rescheduling
an appointment. Skip anything used in the last two weeks (`me/calls/`).

Tell me in two lines who's calling and what I want from the call. Then start.

## Each turn

1. Your line: one to three short sentences, the way people talk on the phone,
   at my level plus a little. Show it, then run
   `./english say --engine say "YOUR LINE"` (the `say` engine answers in about
   4 s; Kokoro is nicer but takes 15 s a line, too slow for a call).
2. Run `./english speak --turn`. It waits up to 20 s for me to start. Read the
   transcript it prints and the `TURN {...}` line (seconds, words, wpm,
   fillers, and `audio`, the turn's recording); keep a running total of the
   seconds. The 2.5 s end-of-turn silence is deliberate, to keep me talking:
   never offer to lengthen it, but if a turn ends mid-sentence, say so out of
   character in one line and suggest filling the pause ("let me think…").
3. Reply in character to what I actually said. If nothing was heard twice in a
   row, ask whether I'd like to switch to typing, and continue in text if so.

**No corrections during the call**: note them for the end. If a real person
wouldn't understand me, react as they would ("Sorry, the line's bad, you
mean…?"). Whisper often smooths grammar, so a clean transcript is weak
evidence. 6–10 turns, then end the call naturally.

## After the call

1. **How it went**: did I get what I called for, and one thing I did well.
2. **Errors**: a `/check`-style table from the transcripts (spoken-text rules:
   never punctuation, capitals, fillers or restarts). Append them to
   `me/errors.md` in the `/check` format.
3. **Say it like this**: two or three of my lines as a native speaker would say
   them on the phone.
4. **Fluency**: my words per minute over the call (total words × 60 ÷ total
   seconds) against the 120 goal, in one line.

Save the call to `me/calls/YYYY-MM-DD-HHMM.md`: the setup, then each turn as
`**Name:** …` / `**Me:** …` (mark a cut-off or unheard turn, with its `audio`
path so I can listen back), then the debrief. Then log it, with the minutes I
spoke, rounded up:

```
./english log call --minutes N --goal yes --note "who / why"
```

## Dashboard

If `me/dashboard/artifact-url` exists, finish by refreshing the dashboard the
way `.claude/commands/dashboard.md` describes, and add its one-line summary to
your reply. If it doesn't exist, skip this.
