---
description: Refresh my private progress dashboard (Anki, journal, errors)
allowed-tools: Read, Write, Bash(./english dashboard:*), Bash(shasum:*), Bash(cat:*), Artifact, ArtifactData
effort: low
---
Refresh the learner's private dashboard on claude.ai.

The dashboard is an artifact made from the **Dashboard** type. Its page is
`build/dashboard.html` (shared app code, no learner data). Its numbers are one
attached file, `me/dashboard/practice.json`, written by `./english dashboard`.
The state that ties the two together lives in `me/dashboard/`:

- `artifact-url`: the dashboard's link
- `asset-id`: the id of the data file currently attached
- `page-sha`: sha256 of the `build/dashboard.html` last written to it

## Steps

1. Run `./english dashboard`. Note its `Changed:` line.

2. **No `me/dashboard/artifact-url` yet?** Create the dashboard: `Artifact`
   quickstart (intent "other"), then publish with the Dashboard `type_url`,
   title "English Practice", and `auto_open: "after_first_write"`. Save the
   returned URL to `me/dashboard/artifact-url`. Follow the type's
   instructions for everything below.

3. **Upload the data.** `Artifact` publish with `url` (from `artifact-url`),
   `asset: true`, and `file_path: me/dashboard/practice.json`. Then `ArtifactData`
   `get` `datasets/practice` and `update` it, pinned with `if_version`, setting
   `source.url` to the new `/_blob/<id>` and `updated: {at: <now, ISO>, by: "Claude (/dashboard)"}`.
   On the first run, `set` it instead:
   `{title: "Practice data from your Mac", description: "Exported by ./english dashboard from your Anki collection, me/journal and me/errors.md, then uploaded by Claude.", source: {kind: "file", url, name: "practice.json", format: "json"}, updated, schedule: "Refreshed by /dashboard, and at the end of /journal, /check, /mine, /drill, /roleplay, /call, /mistakes, /story and /level", staleAfterHours: 48}`,
   plus `dash/meta` `{title: "English Practice"}`.
   Then delete the previous data file (`Artifact` delete, `url`, `path`: the old
   `asset-id`) and write the new id to `me/dashboard/asset-id`.

4. **Page changed?** Compare `shasum -a 256 build/dashboard.html` with
   `me/dashboard/page-sha`. If they differ, or it's the first run, write
   `files/index.html` as `{text: <the whole file>}` (an `update` pinned with
   `if_version`, or `set` the first time), then save the new sha. After a page
   write, read `data/users/me` doc `check` as the type's instructions say.

5. Reply in one or two lines: the `Changed:` line in plain words, and the link.

Never put journal text or `errors.md` sentences anywhere but this private
dashboard. `./english report` is the shareable page and stays numbers-only.
If a write is refused or the artifact can't be reached, say so and stop; the
next refresh catches up, because each upload carries the full data.
