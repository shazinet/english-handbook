#!/usr/bin/env python3
"""Extract the source PDFs to plain text, one file per page.

Output goes to build/raw/ and is AUTHORING REFERENCE ONLY. It is never shipped
into cards unreviewed: the PDFs carry an OCR-derived text layer with no
ToUnicode maps, so IPA is unrecoverable (/brait/ comes out as "/bra1t/") and
digits/letters are occasionally confused in headings (5A -> SA).
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOURCES = ROOT / "resources"
OUT = ROOT / "build" / "raw"

SOURCES = {
    "grammar": "AEF 5 Student's Book - 3rd Edition [www.languagecentre.ir]-grammar.pdf",
    "vocab": "AEF 5 Student's Book - 3rd Edition [Hoomaan]-vocabulary.pdf",
}


def page_count(pdf: Path) -> int:
    out = subprocess.run(
        ["pdfinfo", str(pdf)], capture_output=True, text=True, check=True
    ).stdout
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    if not m:
        sys.exit(f"could not read page count from {pdf.name}")
    return int(m.group(1))


def extract(pdf: Path, stem: str) -> None:
    pages = page_count(pdf)
    for page in range(1, pages + 1):
        dest = OUT / f"{stem}-{page:02d}.txt"
        subprocess.run(
            ["pdftotext", "-layout", "-f", str(page), "-l", str(page),
             str(pdf), str(dest)],
            check=True,
        )
        print(f"  {dest.relative_to(ROOT)}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for stem, filename in SOURCES.items():
        pdf = RESOURCES / filename
        if not pdf.exists():
            sys.exit(f"missing source PDF: {pdf}")
        print(f"{stem}: {pdf.name}")
        extract(pdf, stem)


if __name__ == "__main__":
    main()
