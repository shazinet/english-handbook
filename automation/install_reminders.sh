#!/usr/bin/env bash
# Set up the evening reminder job. Idempotent — safe to re-run after editing
# tiers in .reminders.json, and `--uninstall` removes the agent again.
#
# What it does, in order:
#   1. writes me/.reminders.json (gitignored) with a random ntfy topic
#   2. creates a secret gist that the phone widget reads
#   3. installs and loads the launchd agent
#
# It never touches the Anki collection, and everything it creates is either
# gitignored or lives outside the repo.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ME="${ENGLISH_ME:-$REPO/me}"
LABEL="com.english-handbook.reminder"
# The name this job had before the app was made shareable; removed on install so
# an upgraded Mac doesn't run both and push every reminder twice.
LEGACY_LABEL="dev.hoomaan.english-reminder"
PLIST_SRC="$REPO/automation/$LABEL.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$LABEL.plist"
CONFIG="$ME/.reminders.json"
STATE="$ME/.state"
EXAMPLE="$REPO/automation/reminders.example.json"
DOMAIN="gui/$(id -u)"

die() { echo "error: $*" >&2; exit 1; }

uninstall() {
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    rm -f "$PLIST_DEST"
    echo "Removed $LABEL. me/.reminders.json and the gist are untouched —"
    echo "delete them by hand if you want them gone too."
    exit 0
}

if [[ "${1:-}" == "--uninstall" ]]; then
    uninstall
elif [[ -n "${1:-}" ]]; then
    die "unknown argument: $1 (only --uninstall is accepted)"
fi

command -v jq >/dev/null || die "jq not found — brew install jq"
GH="$(command -v gh)" || die "gh not found — brew install gh"
gh auth status >/dev/null 2>&1 || die "gh isn't logged in — run: gh auth login"

# The plist hardcodes an interpreter because launchd's PATH is minimal. Resolve
# it here so the one that actually has `anki` is the one that gets baked in.
if [[ -x "$REPO/.venv/bin/python" ]]; then
    PYTHON="$REPO/.venv/bin/python"
else
    PYTHON="$(command -v python3)" || die "no python3 on PATH — run ./install.sh"
fi
"$PYTHON" -c "import anki, yaml" 2>/dev/null \
    || die "$PYTHON can't import anki/yaml — run ./install.sh"

# --- 1. config ---------------------------------------------------------------

mkdir -p "$ME"
if [[ ! -f "$CONFIG" && -f "$REPO/.reminders.json" ]]; then
    # Config from before learner data moved into me/: keep its topic and gist,
    # so the phone apps already subscribed to them carry on working.
    mv "$REPO/.reminders.json" "$CONFIG"
    echo "Moved .reminders.json into me/"
fi
if [[ ! -f "$CONFIG" ]]; then
    cp "$EXAMPLE" "$CONFIG"
    echo "Created me/.reminders.json"
fi

# launchd runs with a bare PATH, so remind.py needs gh's absolute location.
jq --arg gh "$GH" '.gh_bin = $gh' "$CONFIG" > "$CONFIG.tmp" && mv "$CONFIG.tmp" "$CONFIG"

topic="$(jq -r '.ntfy.topic // ""' "$CONFIG")"
if [[ -z "$topic" ]]; then
    # Long and random on purpose: an ntfy topic is the only credential there is.
    # Anyone who guesses it can read your reminders and publish to them.
    topic="english-$(openssl rand -hex 10)"
    jq --arg t "$topic" '.ntfy.topic = $t' "$CONFIG" > "$CONFIG.tmp" && mv "$CONFIG.tmp" "$CONFIG"
    echo "Generated ntfy topic"
fi

# --- 2. gist -----------------------------------------------------------------

gist_id="$(jq -r '.gist_id // ""' "$CONFIG")"
if [[ -z "$gist_id" ]]; then
    seed_dir="$(mktemp -d)"
    echo '{"date":"","done":false,"streak":0,"remaining":[],"generated_at":""}' \
        > "$seed_dir/status.json"
    url="$(gh gist create -d "English practice status (widget)" "$seed_dir/status.json")"
    rm -rf "$seed_dir"
    gist_id="${url##*/}"
    login="$(gh api user --jq .login)"
    raw="https://gist.githubusercontent.com/$login/$gist_id/raw/status.json"
    jq --arg id "$gist_id" --arg raw "$raw" '.gist_id = $id | .gist_raw_url = $raw' \
        "$CONFIG" > "$CONFIG.tmp" && mv "$CONFIG.tmp" "$CONFIG"
    echo "Created secret gist $gist_id"
fi

# --- 3. launchd --------------------------------------------------------------

if [[ -f "$HOME/Library/LaunchAgents/$LEGACY_LABEL.plist" ]]; then
    launchctl bootout "$DOMAIN/$LEGACY_LABEL" 2>/dev/null || true
    rm -f "$HOME/Library/LaunchAgents/$LEGACY_LABEL.plist"
    echo "Removed the old $LEGACY_LABEL job"
fi

mkdir -p "$STATE" "$HOME/Library/LaunchAgents"
sed -e "s|__PYTHON__|$PYTHON|g" -e "s|__REPO__|$REPO|g" -e "s|__STATE__|$STATE|g" \
    "$PLIST_SRC" > "$PLIST_DEST"
plutil -lint "$PLIST_DEST" >/dev/null || die "generated plist is malformed"

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST_DEST"
echo "Loaded $LABEL (every 30 min, 18:00–23:30)"

# One run now, so a mistake surfaces here rather than silently at 22:00.
launchctl kickstart "$DOMAIN/$LABEL"
sleep 2

cat <<EOF

Done. Next, on the phone:

  ntfy      App Store -> "ntfy" -> subscribe to topic:
            $(jq -r .ntfy.topic "$CONFIG")

  widget    App Store -> "Scriptable" -> new script, paste
            automation/widget.scriptable.js, set GIST_URL to:
            $(jq -r .gist_raw_url "$CONFIG")

Full walkthrough: automation/README.md
Check it ran: tail $STATE/remind.log
EOF
