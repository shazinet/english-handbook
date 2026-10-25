#!/usr/bin/env python3
"""Kokoro TTS worker, run by audio.py with .venv-speech's Python.

Kokoro (Apache 2.0, hexgrad/Kokoro-82M) lives in its own environment because
it pulls in torch, which must never share .venv with the pinned anki library.
Reads one JSON object on stdin:

    {"voice": "af_heart", "lang": "a", "items": [{"text": "...", "out": "/x.wav"}]}

and writes a 24 kHz WAV per item, loading the model once for the batch. The
model downloads from Hugging Face on first use (~330 MB), then runs offline.
"""

import json
import sys
import warnings

warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
from kokoro import KPipeline  # noqa: E402

RATE = 24000


def main() -> None:
    job = json.load(sys.stdin)
    pipeline = KPipeline(lang_code=job["lang"], repo_id="hexgrad/Kokoro-82M")
    for i, item in enumerate(job["items"], 1):
        chunks = [audio for _, _, audio in pipeline(item["text"], voice=job["voice"])]
        sf.write(item["out"], np.concatenate([np.asarray(c) for c in chunks]), RATE)
        print(f"{i}/{len(job['items'])}", flush=True)


if __name__ == "__main__":
    main()
