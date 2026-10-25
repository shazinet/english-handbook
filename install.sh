#!/usr/bin/env bash
# From a fresh clone to a working setup in one command:
#
#     git clone <repo> ~/english && ~/english/install.sh
#
# Options are passed to `./english setup`; --no-deck skips the Anki import.
# --speech also installs the optional speech tools (Kokoro TTS for natural card
# audio, Whisper for `./english speak`) into .venv-speech/, about 1.5 GB.
#
# Safe to re-run at any time — every step checks before it acts — and
# `./english update` runs it again after pulling a new version. It installs what
# the Mac is missing (Command Line Tools, Homebrew, Anki, uv, Claude Code), builds
# an isolated Python in .venv/ with the anki library pinned to the Anki app's
# version, then hands over to `./english setup` for the learner's profile and deck.
#
# What it can't do for you: sign in to AnkiWeb or Claude, or install the phone
# apps. It stops and says so at the right moment.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEECH=0
SETUP_ARGS=()
for arg in "$@"; do
    if [[ "$arg" == "--speech" ]]; then SPEECH=1; else SETUP_ARGS+=("$arg"); fi
done
ANKI_APP="/Applications/Anki.app"
cd "$REPO"

step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
note() { printf '    %s\n' "$*"; }
die()  { printf '\n\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }

[[ "$(uname)" == "Darwin" ]] || die "macOS only for now — audio uses 'say' and reminders use launchd."

# --- 1. Command Line Tools (git, compilers) ------------------------------------

if ! xcode-select -p >/dev/null 2>&1; then
    step "Installing Apple's Command Line Tools"
    xcode-select --install || true
    die "Finish the install window that just opened, then run ./install.sh again."
fi

# --- 2. Homebrew ---------------------------------------------------------------

if ! command -v brew >/dev/null; then
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        [[ -x "$candidate" ]] && eval "$("$candidate" shellenv)" && break
    done
fi
if ! command -v brew >/dev/null; then
    step "Installing Homebrew (it will ask for your Mac password)"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        [[ -x "$candidate" ]] && eval "$("$candidate" shellenv)" && break
    done
    command -v brew >/dev/null || die "Homebrew didn't install — see https://brew.sh"
fi

# --- 3. Apps and tools -----------------------------------------------------------

if [[ ! -d "$ANKI_APP" ]]; then
    step "Installing Anki"
    brew install --cask anki
fi
if ! command -v uv >/dev/null; then
    step "Installing uv (keeps this app's Python separate from everything else)"
    brew install uv
fi
if ! command -v claude >/dev/null; then
    step "Installing Claude Code"
    brew install --cask claude-code
    note "Run 'claude' once and sign in before using /level, /journal or /check."
fi

# --- 4. Python environment --------------------------------------------------------

step "Preparing Python"
[[ -x .venv/bin/python ]] || uv venv --quiet --python 3.12 .venv
ANKI_VERSION="$(defaults read "$ANKI_APP/Contents/Info" CFBundleShortVersionString 2>/dev/null || true)"
# The library must match the app: an older one can't open the collection, a newer
# one can upgrade it so the app can't. PyPI uses the app's version numbers.
if [[ -n "$ANKI_VERSION" ]] \
    && uv pip install --quiet --python .venv/bin/python -r requirements.txt "anki==$ANKI_VERSION"; then
    note "anki library pinned to $ANKI_VERSION (same as the app)"
else
    note "no anki library matching app version '${ANKI_VERSION:-unknown}' — using the latest"
    note "if ./english doctor complains, upgrade Anki: brew upgrade --cask anki"
    uv pip install --quiet --python .venv/bin/python -r requirements.txt anki
fi

# Open word lists for `./english vocab` and the vocabulary signal in `level`.
# Optional: everything else works without them, so a failed download only warns.
if [[ ! -f data/lexicon/words.tsv ]]; then
    .venv/bin/python build/lexicon.py --fetch >/dev/null \
        && note "word lists downloaded (NGSL, CEFR-J, Octanove)" \
        || note "couldn't download the word lists — retry later: ./english vocab --fetch"
fi

# Speech tools: installed on request, and kept current once they exist.
if [[ $SPEECH == 1 || -x .venv-speech/bin/python ]]; then
    step "Speech tools (Kokoro TTS, Whisper)"
    [[ -x .venv-speech/bin/python ]] || uv venv --quiet --python 3.12 .venv-speech
    uv pip install --quiet --python .venv-speech/bin/python -r requirements-speech.txt
    note "installed in .venv-speech/ — set audio.engine: kokoro in me/profile.yml to use it"
fi

# --- 5. Anki profile -----------------------------------------------------------------

# The deck import needs a collection, which Anki only creates on first launch.
if ! ls "$HOME/Library/Application Support/Anki2/"*/collection.anki2 >/dev/null 2>&1; then
    step "First Anki launch"
    open -a Anki
    note "Anki is opening. If you'll review on a phone too, click Sync and sign in"
    note "to (or create) a free AnkiWeb account. Then QUIT Anki (Cmd-Q)."
    if [[ -t 0 ]]; then
        read -r -p "    Press Enter once Anki is closed... " _
    fi
fi

# --- 6. The learner's profile and deck ---------------------------------------------

step "Setting up your profile and deck"
exec "$REPO/english" setup ${SETUP_ARGS[@]+"${SETUP_ARGS[@]}"}
