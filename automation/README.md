# Reminders

The cards and the journal only work if you actually do them. This is the layer
that makes forgetting hard: an escalating push to your phone through the
evening, and a lock-screen widget showing the streak and how much of the day is
left.

A day counts only when **all three** parts of the loop happened — reps, journal,
`/check`. Two out of three is a broken streak, on purpose: the loop is what
converts rules you can recite into English you can speak.

## Setup

### On this Mac — one command

```bash
automation/install_reminders.sh
```

It generates a random ntfy topic, creates a secret gist for the widget to read,
installs the launchd agent, and runs it once so any mistake surfaces
immediately. Re-running is safe. `--uninstall` removes the agent.

Everything it writes is either gitignored (`me/.reminders.json`, `me/.state/`) or
outside the repo (`~/Library/LaunchAgents/`).

### On the phone — notifications

1. App Store → **ntfy** → open it.
2. Subscribe to the topic printed by the installer (`jq -r .ntfy.topic
   me/.reminders.json` if you need it again).
3. Settings → Focus → whichever mode you use in the evening → allow **ntfy**,
   and check Settings → Notifications → **Scheduled Summary** doesn't include
   ntfy. A summarised reminder arrives the next morning, which is useless.

There is nothing to configure inside the ntfy app itself. It maps `priority`
onto iOS interruption levels on its own (this is ntfy-ios v1.7.0,
`NotificationContent.swift`):

| ntfy priority | iOS behaviour |
|---|---|
| 1–2 `min`/`low` | passive — no sound, no banner, just sits in the list |
| 3 `default` | normal banner (the 20:00 nudge) |
| 4 `high` | **Time Sensitive** — breaks through Focus (22:00, 23:00) |
| 5 `urgent` | asks for **Critical**; iOS downgrades it to Time Sensitive unless the app holds the critical-alert entitlement (23:30) |

So the escalation works out of the box, and Focus is the only thing that can
swallow it — hence step 3.

iOS only adds a **Time Sensitive Notifications** row under Settings →
Notifications → ntfy *after* a time-sensitive push has actually arrived. If you
don't see it, the pushes so far were low priority; it appears on its own once a
22:00-or-later tier fires.

(A user-facing Critical Alerts toggle exists in ntfy's `main` branch, added
2026-06-09 — after v1.8.0 — so it is not in any released build yet. Ignore any
instructions that mention it until it ships.)

The topic name is the *only* credential ntfy has. Anyone who learns it can read
your reminders and send you fake ones — which is why it's random and why
`me/.reminders.json` is gitignored. It carries card counts and a streak number,
nothing sensitive, but treat it like a password anyway.

### On the phone — lock-screen widget

1. App Store → **Scriptable**.
2. New script named `English`, paste `automation/widget.scriptable.js`.
3. Set `GIST_URL` at the top to the raw URL the installer printed
   (`jq -r .gist_raw_url me/.reminders.json`).
4. Lock the phone, long-press the lock screen → **Customise** → **Lock Screen**
   → tap the widget row → add **Scriptable**.
5. Tap the widget you just added and set **Script** to `English`. This step is
   easy to miss, and a Scriptable widget with no script selected renders blank.
6. **When Interacting: Run Script.** Tapping then opens Scriptable and runs the
   script outside widget context, which the script detects and renders as a
   larger, freshly-fetched view rather than the cached widget snapshot. Leave
   **Parameter** empty — it arrives as `args.widgetParameter`, which this script
   doesn't read.

   The alternative is **Open URL** → `https://ankiweb.net/decks`, so the tap
   starts reps instead. Note that it lands in *Safari*: a widget can't launch a
   home-screen web app (web clips have no URL scheme), and since iOS 16.4 the two
   keep separate storage, so Safari will want a fresh AnkiWeb login once.

Do **not** use Scriptable's *Add to Home Screen* button. That feature builds a
Safari web-clip from a `data:` URL, which modern iOS refuses — hence *"Not
allowed to use restricted network port"*. It has nothing to do with widgets; it
only makes a tappable icon that runs the script. Widgets are added by
long-pressing the screen, as above.

The same script also renders as a Home Screen widget, in colour, which the lock
screen can't do — accessory widgets are always monochrome.

## Two free extra layers

**Reps on the phone without paying for AnkiMobile.** AnkiMobile is a paid app,
but **ankiweb.net** in Safari is the same collection with a full reviewer, free.
Log in, open it, Share → *Add to Home Screen*, and it behaves like an app. Sync
the desktop first so it has your latest cards, and sync again afterwards so
`./english status` can see the reps — until the desktop pulls them down, the reminder
still thinks you haven't studied.

**A Shortcuts backstop, if the Mac is often shut.** launchd can only fire while
the Mac is awake; it replays one missed run on wake, but a Mac that stays closed
all evening sends nothing. To cover that, on the phone: Shortcuts → Automation →
Time of Day 22:30 → *Get Contents of URL* (your gist raw URL) → *Get Dictionary
Value* `done` → *If* not true → *Show Notification*. It reads whatever the Mac
last published, so it can be out of date, but it fires whether or not the Mac
ever woke up.

## How the escalation works

`build/remind.py` runs every 30 minutes from 18:00 to 23:30 and sends **at most
one push per tier per day**:

| Tier | Priority | Reads roughly |
|---|---|---|
| 20:00 | default | `English — today's practice · Still to do: 12 cards, journal, check` |
| 22:00 | high | `2h 00m left · Still to do: journal, check · 🔥 5 on the line` |
| 23:00 | high | `1h 00m left · …` |
| 23:30 | urgent | `30m left · …` |

Only the **latest** due tier fires, so a Mac that wakes at 23:10 sends the 23:00
nudge rather than replaying the whole evening. Finish all three parts and you
get one quiet `🔥 N` confirmation instead.

Edit the times, priorities, or `journal_min_words` in `me/.reminders.json`; changes
take effect on the next run, no reinstall needed. `"celebrate": false` turns off
the confirmation push.

## When something looks wrong

```bash
./english status                                   # what the system thinks is done
python3 build/remind.py --dry-run --force-tier 22:00   # exact payload, sends nothing
tail -20 me/.state/remind.log                         # one line per run
launchctl print gui/$(id -u)/com.english-handbook.reminder | head -20
launchctl kickstart -k gui/$(id -u)/com.english-handbook.reminder   # run it now
rm me/.state/reminders-$(date +%F).json               # let today's tiers fire again
```

**"Anki says I did my reps but the nudge disagrees."** Reps done on the phone are
invisible here until Anki on *this Mac* syncs — `status.py` reads the desktop
collection. It says so when the collection looks untouched for a long time. Open
Anki, press `Y`, re-run.

**"The widget is stale."** It shows `as of HH:MM` once the payload is older than
45 minutes, and falls back to its last good copy when offline. The countdown
itself is always computed on the phone, so that number is never stale.

**"No notification at all."** Check ntfy's iOS notification permission first,
then whether a Focus mode or Scheduled Summary is holding it, then
`me/.state/remind.log` — every failed send is logged there, and the script always
exits 0 so launchd never throttles it. To send yourself a test push without
touching today's tier state:

```bash
curl -d '{"topic":"'"$(jq -r .ntfy.topic me/.reminders.json)"'","title":"test","message":"hello","priority":4}' https://ntfy.sh
```
