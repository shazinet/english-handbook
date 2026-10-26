#!/usr/bin/env python3
"""Speak instead of write: record, transcribe locally, and add it to today's journal.

    ./english speak                    record until you press Enter (max 5 min)
    ./english speak --seconds 90       record for a fixed time
    ./english speak --file memo.m4a    transcribe a recording you already have,
                                       e.g. a phone voice memo
    ./english speak --model mlx-community/whisper-small.en-mlx
                                       a smaller, faster model (default: large-v3-turbo)
    ./english speak --list-mics        the microphones this Mac can record from
    ./english speak --turn             one conversational turn for /call: starts
                                       when you speak, stops when you go quiet,
                                       prints the words, touches no journal
                                       (the audio is kept in me/recordings/)

The microphone is `speech.microphone` in the profile (part of its name, e.g.
"USB-C"), or the Mac's current input when that's empty or not plugged in.

The transcript goes into me/journal/YYYY-MM-DD.md under a `## spoken` heading,
with a `<!-- spoken: … -->` marker carrying fluency numbers (speaking time,
words per minute, long pauses, fillers). Then run /check as for a written
entry. A spoken entry counts as the day's journal: it's real production, the
thing the writing stands in for.

Transcription is Whisper via mlx-whisper, on this Mac, nothing uploaded. Whisper
is trained to produce clean text, so it tends to *fix* grammar and drop "um"s;
this asks it for a verbatim transcript, but a missing error isn't proof you
didn't make it. The recording is kept in me/recordings/ so you can listen back.

Runs with .venv-speech's Python (`./install.sh --speech`); cli.py switches to it.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import threading
from datetime import datetime
from pathlib import Path

import numpy as np

from paths import JOURNAL, ME, load_profile

RATE = 16000  # what Whisper expects
MAX_SECONDS = 300
DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"
RECORDINGS = ME / "recordings"
# A verbatim-style example nudges Whisper to keep fillers, restarts and errors
# instead of writing what you meant to say.
VERBATIM_PROMPT = ("Um, so yesterday I- I go to the, uh, the gym and, er, I meet "
                   "my friend there. He say me that, hmm, we should to go together.")
FILLERS = {"um", "uh", "er", "erm", "hmm", "mm", "ah", "eh"}
PAUSE = 1.0  # seconds of silence between words that counts as a long pause
# --turn: how long to wait for the first word, the silence that ends a turn,
# and the longest turn. The silence is short on purpose: a call pushes you to
# keep talking (say "let me think…") rather than stop and compose.
TURN_WAIT, TURN_SILENCE, TURN_MAX = 20, 2.5, 90
# What counts as speech, as RMS level per 100 ms. Starting needs a clear lift
# above the room's noise; once you're talking, a quieter level keeps the turn
# open, so a soft "er…" mid-answer isn't taken for silence. Headset mics with a
# noise gate send exact zeros between words, so the floors sit just above zero.
START_FLOOR, START_OVER_NOISE = 0.003, 3.5
KEEP_FLOOR, KEEP_OVER_NOISE = 0.0015, 2.0


def input_devices() -> list[tuple[int, str]]:
    import sounddevice as sd

    return [(i, d["name"]) for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]


def pick_microphone(wanted: str) -> int | None:
    """The first input whose name contains `wanted`, ignoring case. None means
    the Mac's current input: nothing asked for, or the asked-for one is unplugged.
    The setting matters because macOS quietly switches input to earbuds when
    they connect, and earbud mics give Whisper much worse audio."""
    if not wanted:
        return None
    for index, name in input_devices():
        if wanted.lower() in name.lower():
            return index
    print(f"No microphone matching “{wanted}” is connected; using the Mac's current input.")
    return None


def record(seconds: int | None, mic: int | None = None) -> np.ndarray:
    import sounddevice as sd

    chunks: list[np.ndarray] = []
    stop = threading.Event()

    def callback(indata, frames, time, status):  # noqa: ARG001
        chunks.append(indata.copy())

    limit = seconds or MAX_SECONDS
    device = sd.query_devices(mic if mic is not None else sd.default.device[0])["name"]
    with sd.InputStream(samplerate=RATE, channels=1, dtype="float32", callback=callback,
                        device=mic):
        if seconds:
            print(f"Recording {seconds}s from {device}… speak now.")
            stop.wait(seconds)
        else:
            print(f"Recording from {device}. Speak, then press Enter to stop "
                  f"(stops by itself after {limit // 60} min).")
            timer = threading.Timer(limit, stop.set)
            timer.start()
            threading.Thread(target=lambda: (sys.stdin.readline(), stop.set()), daemon=True).start()
            stop.wait()
            timer.cancel()
    audio = np.concatenate(chunks)[:, 0] if chunks else np.zeros(0, dtype="float32")
    print(f"Recorded {len(audio) / RATE:.0f}s.")
    return audio


def record_turn(mic: int | None = None) -> tuple[np.ndarray, bool]:
    """Record one turn with no key press: wait for speech, stop after
    TURN_SILENCE seconds of quiet. Thresholds are set from the first half
    second of room noise, so a noise-gated headset and a laptop mic both work.
    Returns the audio and whether speech started; if it never did, the audio
    is the whole wait, kept so a missed answer can be listened to."""
    import queue

    import sounddevice as sd

    block = RATE // 10                    # 100 ms
    q: queue.Queue = queue.Queue()
    chunks: list[np.ndarray] = []
    with sd.InputStream(samplerate=RATE, channels=1, dtype="float32", blocksize=block,
                        callback=lambda indata, *_: q.put(indata[:, 0].copy()), device=mic):
        noise = float(np.median([np.sqrt(np.mean(q.get() ** 2)) for _ in range(5)]))
        start = max(START_FLOOR, START_OVER_NOISE * noise)
        keep = max(KEEP_FLOOR, KEEP_OVER_NOISE * noise)
        name = sd.query_devices(mic if mic is not None else sd.default.device[0])["name"]
        print(f"● Listening on {name}… speak when you're ready.", flush=True)
        started, quiet, waited = False, 0.0, 0.0
        while True:
            chunk = q.get()
            level = float(np.sqrt(np.mean(chunk ** 2)))
            chunks.append(chunk)
            if not started:
                waited += 0.1
                if level > start:
                    started = True
                    chunks = [np.zeros(block, dtype="float32"), *chunks[-3:]]
                elif waited >= TURN_WAIT:
                    break
                continue
            quiet = 0.0 if level > keep else quiet + 0.1
            if quiet >= TURN_SILENCE or len(chunks) * 0.1 >= TURN_MAX:
                break
    return np.concatenate(chunks) if chunks else np.zeros(0, dtype="float32"), started


def load_file(path: Path) -> np.ndarray:
    """Any format Core Audio reads (m4a, mp3, wav, caf…) → 16 kHz mono floats.
    afconvert rather than ffmpeg, which mlx-whisper would otherwise need."""
    import soundfile as sf

    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        subprocess.run(["afconvert", "-f", "WAVE", "-d", f"LEI16@{RATE}", "-c", "1",
                        str(path), tmp.name], check=True, capture_output=True)
        audio, _ = sf.read(tmp.name, dtype="float32")
    return audio


def save_recording(audio: np.ndarray, stamp: str) -> Path:
    import soundfile as sf

    RECORDINGS.mkdir(parents=True, exist_ok=True)
    ignore = RECORDINGS / ".gitignore"
    if not ignore.exists():
        # Audio would bloat the private me/ repo; keep it local unless you choose otherwise.
        ignore.write_text("# recordings stay on this Mac; delete this file to back them up\n*\n!.gitignore\n")
    dest = RECORDINGS / f"{stamp}.m4a"
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        sf.write(tmp.name, audio, RATE)
        subprocess.run(["afconvert", "-f", "mp4f", "-d", "aac", tmp.name, str(dest)],
                       check=True, capture_output=True)
    return dest


def transcribe(audio: np.ndarray, model: str) -> dict:
    import mlx_whisper

    print(f"Transcribing on this Mac ({model.split('/')[-1]}; the first run downloads it)…")
    return mlx_whisper.transcribe(
        audio, path_or_hf_repo=model, language="en", word_timestamps=True,
        initial_prompt=VERBATIM_PROMPT, condition_on_previous_text=False, temperature=0.0)


def fluency(result: dict) -> dict:
    words = [w for seg in result.get("segments", []) for w in seg.get("words", [])]
    if not words:
        return {"seconds": 0, "words": 0, "wpm": 0, "pauses": 0, "fillers": 0}
    span = max(words[-1]["end"] - words[0]["start"], 1.0)
    tokens = [re.sub(r"[^a-z']", "", w["word"].lower()) for w in words]
    pauses = sum(1 for a, b in zip(words, words[1:]) if b["start"] - a["end"] >= PAUSE)
    fillers = sum(1 for t in tokens if t in FILLERS)
    spoken = sum(1 for t in tokens if t and t not in FILLERS)
    return {"seconds": round(span), "words": spoken, "wpm": round(60 * spoken / span),
            "pauses": pauses, "fillers": fillers}


def paragraphs(result: dict) -> str:
    """Segments joined into paragraphs at long pauses, which is where a speaker
    usually changes thought."""
    out, current, last_end = [], [], None
    for seg in result.get("segments", []):
        text = seg["text"].strip()
        if not text:
            continue
        if current and last_end is not None and seg["start"] - last_end > 2.5:
            out.append(" ".join(current))
            current = []
        current.append(text)
        last_end = seg["end"]
    if current:
        out.append(" ".join(current))
    return "\n\n".join(out)


def append_entry(text: str, stats: dict, recording: Path | None, now: datetime) -> Path:
    JOURNAL.mkdir(parents=True, exist_ok=True)
    path = JOURNAL / f"{now:%Y-%m-%d}.md"
    m, s = divmod(stats["seconds"], 60)
    marker = (f"<!-- spoken: {now:%Y-%m-%dT%H:%M} · {m}m{s:02d}s · {stats['words']} words · "
              f"{stats['wpm']} wpm · {stats['pauses']} pauses · {stats['fillers']} fillers"
              + (f" · {recording.name}" if recording else "") + " -->")
    block = f"## spoken\n\n{marker}\n\n{text}\n"
    if path.exists():
        body = path.read_text().rstrip("\n")
        path.write_text(f"{body}\n\n{block}")
    else:
        path.write_text(f"# {now:%Y-%m-%d}\n\n{block}")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seconds", type=int, help="record for a fixed time instead of until Enter")
    ap.add_argument("--file", type=Path, help="transcribe an existing recording")
    ap.add_argument("--model", help=f"Whisper model (default {DEFAULT_MODEL})")
    ap.add_argument("--mic", help="part of a microphone's name (default: the profile's "
                                  "speech.microphone)")
    ap.add_argument("--list-mics", action="store_true", help="list microphones and exit")
    ap.add_argument("--dry-run", action="store_true", help="print, don't touch the journal")
    ap.add_argument("--turn", action="store_true",
                    help="one /call turn: record until you go quiet, print, touch nothing")
    args = ap.parse_args()

    speech = load_profile().get("speech") or {}
    if args.list_mics:
        mic = pick_microphone(args.mic or speech.get("microphone") or "")
        for index, name in input_devices():
            print(f"{'→' if index == mic else ' '} {name}")
        return 0

    if args.turn:
        return turn(args, speech)
    if not args.file and not args.seconds and not sys.stdin.isatty():
        sys.exit("No terminal to press Enter in: use --seconds N, or --file.")
    model = args.model or speech.get("model") or DEFAULT_MODEL
    now = datetime.now()

    if args.file:
        audio = load_file(args.file)
    else:
        audio = record(args.seconds, pick_microphone(args.mic or speech.get("microphone") or ""))
    if len(audio) < RATE * 3:
        sys.exit("Under three seconds of audio: nothing to transcribe.")
    result = transcribe(audio, model)
    text = paragraphs(result)
    if not text.strip():
        sys.exit("Whisper heard no speech. Check the microphone (System Settings → "
                 "Privacy & Security → Microphone) and try again.")
    stats = fluency(result)

    print(f"\n{text}\n")
    print(f"{stats['words']} words in {stats['seconds']}s · {stats['wpm']} words/min · "
          f"{stats['pauses']} long pauses · {stats['fillers']} fillers")
    if args.dry_run:
        return 0
    recording = None if args.file else save_recording(audio, f"{now:%Y-%m-%d-%H%M}")
    path = append_entry(text, stats, recording, now)
    print(f"\nAdded to {path.relative_to(ME.parent) if path.is_relative_to(ME.parent) else path}. "
          f"Now run /check in Claude Code.")
    return 0


def turn(args, speech: dict) -> int:
    """Print the turn's words, then one `TURN {json}` line for /call to total.
    Every turn's audio is saved, a missed one included, so a cut-off can be
    checked by ear: a real pause, or the mic going quiet."""
    audio, started = record_turn(pick_microphone(args.mic or speech.get("microphone") or ""))
    saved = save_recording(audio, f"call-{datetime.now():%Y-%m-%d-%H%M%S}"
                           + ("" if started else "-unheard")) if len(audio) else None
    where = str(saved.relative_to(ME)) if saved else None
    if not started or len(audio) < RATE:
        print("(no answer heard)")
        print("TURN " + json.dumps({"seconds": 0, "words": 0, "wpm": 0, "fillers": 0,
                                    "audio": where}))
        return 0
    result = transcribe(audio, args.model or speech.get("model") or DEFAULT_MODEL)
    stats = fluency(result)
    print(f"\n{paragraphs(result) or '(no words recognised)'}\n")
    print("TURN " + json.dumps({**{k: stats[k] for k in ("seconds", "words", "wpm", "fillers")},
                                "audio": where}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
