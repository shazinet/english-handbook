#!/usr/bin/env python3
"""Generate pronunciation audio for cards marked `audio: true`.

Uses macOS `say` + `afconvert`, so this is fully offline and free. Output is
cached by card id and content hash: unchanged cards are not regenerated, so
re-running is cheap.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from paths import MEDIA, ROOT, content_files

CACHE = MEDIA / ".cache.json"
VOICE = "Samantha"  # US English; `say -v '?'` lists alternatives

CLOZE_RE = re.compile(r"\{\{c\d+::(.+?)(?:::.+?)?\}\}")


def spoken_text(text: str) -> str:
    """Strip cloze markup so the full natural sentence is spoken."""
    return CLOZE_RE.sub(r"\1", text).strip()


def load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    return {}


def synth(text: str, dest: Path, voice: str) -> None:
    # `say` writes AIFF at its own default format; passing --data-format here
    # makes it fail with "Opening output file failed: fmt?". afconvert then
    # produces AAC-in-MP4 (.m4a) — macOS has no MP3 encoder.
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=True) as tmp:
        subprocess.run(["say", "-v", voice, "-o", tmp.name, text], check=True)
        subprocess.run(
            ["afconvert", "-f", "mp4f", "-d", "aac", tmp.name, str(dest)],
            check=True,
            capture_output=True,
        )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--voice", default=VOICE, help=f"say voice (default: {VOICE})")
    ap.add_argument("--force", action="store_true", help="regenerate everything")
    args = ap.parse_args()

    if sys.platform != "darwin":
        sys.exit("audio generation requires macOS (`say`)")

    MEDIA.mkdir(parents=True, exist_ok=True)
    cache = {} if args.force else load_cache()

    todo = []
    for _, data, _ in content_files():
        for card in data.get("cards", []):
            if not card.get("audio"):
                continue
            text = spoken_text(card["text"])
            key = hashlib.sha1(f"{args.voice}::{text}".encode()).hexdigest()
            dest = MEDIA / f"{card['id']}.m4a"
            if cache.get(card["id"]) == key and dest.exists():
                continue
            todo.append((card["id"], text, dest, key))

    if not todo:
        print("Audio up to date — nothing to generate.")
        return

    for i, (cid, text, dest, key) in enumerate(todo, 1):
        synth(text, dest, args.voice)
        cache[cid] = key
        print(f"  [{i}/{len(todo)}] {cid}")

    CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True))
    print(f"Generated {len(todo)} file(s) into {MEDIA.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
