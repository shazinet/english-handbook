#!/usr/bin/env python3
"""Generate audio for cards: those marked `audio: true`, or every card.

Two engines, chosen in me/profile.yml under `audio:` and both fully offline:

    say      macOS `say` + `afconvert`. Built in, nothing to install. The default.
    kokoro   Kokoro-82M neural TTS (Apache 2.0): far more natural, US or UK
             voices. Needs `./install.sh --speech`, which builds .venv-speech/;
             without it this falls back to `say` and says so.

`accent: us|uk` picks the voice and `cards: all` gives every sentence audio,
grammar cards included, rather than only cards marked `audio: true`.

Output is cached by card id and a hash of voice and text: unchanged cards are
not regenerated, so re-running is cheap. Clips from voices other than the
original `say` Samantha are named `<id>-<voice>.m4a`, so switching voice gives
Anki a new file name rather than a same-named file with different sound.

`--say` reads text aloud instead, in the same voice: /story reads its story
with it and /call speaks the other person's lines (`./english say`).

    ./english say "Hi, how can I help?"        speak a line
    ./english say me/stories/x.md --save x.m4a  speak a file's prose, keep the audio
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from paths import MEDIA, ROOT, SPEECH_PYTHON, content_files, load_profile

CACHE = MEDIA / ".cache.json"
VOICES = {
    ("say", "us"): "Samantha",
    ("say", "uk"): "Daniel",
    ("kokoro", "us"): "af_heart",
    ("kokoro", "uk"): "bf_emma",
}
LEGACY_VOICE = "Samantha"  # clips from before engines existed: <id>.m4a
KOKORO_LANG = {"us": "a", "uk": "b"}

CLOZE_RE = re.compile(r"\{\{c\d+::(.+?)(?:::.+?)?\}\}")


def spoken_text(text: str) -> str:
    """Strip cloze markup so the full natural sentence is spoken."""
    return CLOZE_RE.sub(r"\1", text).strip()


def kokoro_ready() -> bool:
    return SPEECH_PYTHON.exists()


def settings(profile: dict, quiet: bool = True) -> tuple[str, str, str]:
    """(engine, accent, voice) the build will use, falling back to `say` when
    Kokoro is asked for but not installed."""
    conf = profile.get("audio") or {}
    engine = conf.get("engine") or "say"
    accent = conf.get("accent") if conf.get("accent") in KOKORO_LANG else "us"
    if engine == "kokoro" and not kokoro_ready():
        if not quiet:
            print("audio.engine is kokoro but .venv-speech/ is missing — using say. "
                  "Install it with: ./install.sh --speech")
        engine = "say"
    if engine not in ("say", "kokoro"):
        sys.exit(f"audio.engine must be say or kokoro, not {engine!r}")
    return engine, accent, VOICES[(engine, accent)]


def wants_audio(card: dict, profile: dict) -> bool:
    if (profile.get("audio") or {}).get("cards") == "all":
        return card.get("audio", True) is not False
    return bool(card.get("audio"))


def clip_path(card_id: str, voice: str) -> Path:
    if voice == LEGACY_VOICE:
        return MEDIA / f"{card_id}.m4a"
    return MEDIA / f"{card_id}-{voice}.m4a"


def load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    return {}


def to_m4a(src: Path, dest: Path) -> None:
    # afconvert produces AAC-in-MP4 (.m4a) — macOS has no MP3 encoder.
    subprocess.run(["afconvert", "-f", "mp4f", "-d", "aac", str(src), str(dest)],
                   check=True, capture_output=True)


def synth_say(todo: list[tuple], voice: str) -> None:
    for i, (cid, text, dest, _) in enumerate(todo, 1):
        # `say` writes AIFF at its own default format; passing --data-format here
        # makes it fail with "Opening output file failed: fmt?".
        with tempfile.NamedTemporaryFile(suffix=".aiff", delete=True) as tmp:
            subprocess.run(["say", "-v", voice, "-o", tmp.name, text], check=True)
            to_m4a(Path(tmp.name), dest)
        print(f"  [{i}/{len(todo)}] {cid}")


def synth_kokoro(todo: list[tuple], voice: str, accent: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        wavs = [Path(tmp) / f"{i}.wav" for i in range(len(todo))]
        job = {"voice": voice, "lang": KOKORO_LANG[accent],
               "items": [{"text": t, "out": str(w)} for (_, t, _, _), w in zip(todo, wavs)]}
        print(f"  Kokoro ({voice}): {len(todo)} clip(s); the first run downloads the model")
        worker = subprocess.run([str(SPEECH_PYTHON), str(Path(__file__).with_name("tts_kokoro.py"))],
                                input=json.dumps(job), text=True, capture_output=True)
        if worker.returncode != 0:
            sys.exit("Kokoro failed:\n" + worker.stderr.strip()[-1500:])
        for i, ((cid, _, dest, _), wav) in enumerate(zip(todo, wavs), 1):
            to_m4a(wav, dest)
            if i % 50 == 0 or i == len(todo):
                print(f"  [{i}/{len(todo)}] {cid}")


def prose(text: str) -> str:
    """A markdown file's readable lines: no headings, comments or rules."""
    keep = [line for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith(("#", "<!--", "---", "|"))]
    return " ".join(line.strip().lstrip("-*> ").replace("*", "").replace("_", " ") for line in keep)


def say_aloud(text: str, engine: str, accent: str, voice: str, save: Path | None = None) -> None:
    """Speak text now (afplay), optionally keeping the audio as .m4a."""
    with tempfile.TemporaryDirectory() as tmp:
        if engine == "kokoro":
            wav = Path(tmp) / "say.wav"
            job = {"voice": voice, "lang": KOKORO_LANG[accent], "items": [{"text": text, "out": str(wav)}]}
            worker = subprocess.run([str(SPEECH_PYTHON), str(Path(__file__).with_name("tts_kokoro.py"))],
                                    input=json.dumps(job), text=True, capture_output=True)
            if worker.returncode != 0:
                sys.exit("Kokoro failed:\n" + worker.stderr.strip()[-1500:])
        else:
            wav = Path(tmp) / "say.aiff"
            subprocess.run(["say", "-v", voice, "-o", str(wav), text], check=True)
        if save:
            save.parent.mkdir(parents=True, exist_ok=True)
            to_m4a(wav, save)
        subprocess.run(["afplay", str(wav)], check=False)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", choices=("say", "kokoro"), help="override audio.engine")
    ap.add_argument("--voice", help="override the voice (say -v '?' lists them)")
    ap.add_argument("--force", action="store_true", help="regenerate everything")
    ap.add_argument("--say", action="store_true", help="read the text (or a file) given aloud")
    ap.add_argument("text", nargs="*", help="with --say: the words, or one file")
    ap.add_argument("--save", type=Path, help="with --say: also keep the audio here (.m4a)")
    args = ap.parse_args()

    if sys.platform != "darwin":
        sys.exit("audio generation requires macOS (`say`, `afconvert`)")

    profile = load_profile()
    if args.engine:
        profile["audio"] = {**profile["audio"], "engine": args.engine}
    engine, accent, voice = settings(profile, quiet=False)
    voice = args.voice or voice

    if args.text and not args.say:
        ap.error("text is only read with --say")
    if args.say:
        source = Path(args.text[0]) if args.text else None
        text = prose(source.read_text()) if len(args.text) == 1 and source.is_file() else " ".join(args.text)
        if not text.strip():
            sys.exit("nothing to say")
        say_aloud(text, engine, accent, voice, args.save)
        return

    MEDIA.mkdir(parents=True, exist_ok=True)
    cache = {} if args.force else load_cache()

    todo = []
    for _, data, _ in content_files():
        for card in data.get("cards", []):
            if not wants_audio(card, profile):
                continue
            text = spoken_text(card["text"])
            key = hashlib.sha1(f"{voice}::{text}".encode()).hexdigest()
            dest = clip_path(card["id"], voice)
            # Keyed by file stem (the card id for legacy clips), so each voice's
            # clips stay cached when you switch back and forth.
            if cache.get(dest.stem) == key and dest.exists():
                continue
            todo.append((card["id"], text, dest, key))

    if not todo:
        print("Audio up to date — nothing to generate.")
        return

    if engine == "kokoro":
        synth_kokoro(todo, voice, accent)
    else:
        synth_say(todo, voice)
    for _, _, dest, key in todo:
        cache[dest.stem] = key

    CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True))
    print(f"Generated {len(todo)} file(s) into {MEDIA.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
