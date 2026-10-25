#!/usr/bin/env python3
"""A CEFR-tagged word table from open word lists, and what the deck is missing.

    ./english vocab --fetch          download the lists into data/lexicon/ (once)
    ./english vocab                  most frequent words at your level with no card
    ./english vocab --level B2 -n 60 one level only, longer list
    ./english vocab --spoken         only the NGSL-Spoken list (conversation core)
    ./english vocab --word deposit   one word: level, frequency, cards that test it

Sources, all free to use with attribution (credits in content/LICENSE):

    NGSL 1.2, NGSL-Spoken 1.2    Browne & Culligan, CC BY-SA 4.0 — frequency ranks
                                 and inflected forms
    CEFR-J Wordlist 1.5          Tono, TUFS — A1–B2 levels; commercial use allowed
                                 with citation, redistribution not granted
    Octanove C1/C2 profile 1.0   Octanove Labs, CC BY-SA 4.0 — C1/C2 levels

The files are downloaded, never committed, because the CEFR-J terms don't grant
redistribution. Everything here degrades to "not fetched yet" without them, so
the build and the rest of the app never depend on the network.

A word counts as *tested* when it appears inside a cloze answer, the part the
learner must produce, and *seen* when it is only elsewhere in a card's sentence.
Only tested words close a gap: recognising a word is not the goal (CLAUDE.md
rule 1).
"""

import argparse
import csv
import re
import sys
import urllib.request
from collections import Counter
from functools import lru_cache

from paths import CEFR, LEXICON, content_files, level_index, load_profile

CEFRJ = "https://raw.githubusercontent.com/openlanguageprofiles/olp-en-cefrj/master/"
NGSL = "https://www.newgeneralservicelist.com/s/"
SOURCES = {
    "ngsl-rank.csv": NGSL + "NGSL_12_stats.csv",
    "ngsl-forms.csv": NGSL + "NGSL_12_lemmatized_for_teaching.csv",
    "spoken-rank.csv": NGSL + "NGSL-Spoken_12_stats.csv",
    "spoken-forms.csv": NGSL + "NGSL-Spoken_12_lemmatized_for_teaching.csv",
    "cefrj-vocab.csv": CEFRJ + "cefrj-vocabulary-profile-1.5.csv",
    "octanove-c1c2.csv": CEFRJ + "octanove-vocabulary-profile-c1c2-1.0.csv",
    # Not used here: a reference for which structures exist at which level,
    # for choosing new grammar topics (see CLAUDE.md, Open data).
    "cefrj-grammar.csv": CEFRJ + "cefrj-grammar-profile-20180315.csv",
}
TABLE = LEXICON / "words.tsv"
# Transcription tags from the spoken corpora behind NGSL ([pause], [laughter]),
# counted as words: their ranks say nothing about how often people say them.
ANNOTATIONS = {"pause", "unclear", "laughter", "cough", "breath"}

CLOZE_RE = re.compile(r"\{\{c\d+::(.+?)(?:::.+?)?\}\}")
TOKEN_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")
# Regular inflections, tried in order when a form isn't in the NGSL form lists.
SUFFIXES = (("ies", "y"), ("ied", "y"), ("ing", ""), ("ing", "e"), ("ed", ""), ("ed", "e"),
            ("es", ""), ("s", ""), ("er", ""), ("est", ""), ("ly", ""))


def fetch() -> None:
    LEXICON.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        dest = LEXICON / name
        req = urllib.request.Request(url, headers={"User-Agent": "english-handbook"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
        print(f"  {name:<20} {dest.stat().st_size // 1024:>5} KB")
    load.cache_clear()
    table = load()
    write_table(table["words"])
    print(f"Built {TABLE.relative_to(LEXICON.parent.parent)} — {len(table['words'])} words.")


def _rows(name: str) -> list[list[str]]:
    with open(LEXICON / name, newline="", encoding="utf-8-sig", errors="replace") as f:
        return [r for r in csv.reader(f) if r and r[0].strip() and not r[0].startswith("##")]


@lru_cache(maxsize=1)
def load() -> dict | None:
    """{'words': {lemma: info}, 'forms': {form: lemma}}, or None if not fetched.

    info = {cefr, ngsl_rank, spoken_rank, forms}. CEFR is the lowest level any
    part of speech of the word has; frequency ranks are NGSL's (1 = commonest).
    """
    if not all((LEXICON / n).exists() for n in SOURCES):
        return None
    words: dict[str, dict] = {}

    def entry(lemma: str) -> dict:
        return words.setdefault(lemma, {"cefr": None, "ngsl_rank": None,
                                        "spoken_rank": None, "forms": {lemma}})

    for name, key in (("ngsl-rank.csv", "ngsl_rank"), ("spoken-rank.csv", "spoken_rank")):
        for row in _rows(name)[1:]:
            lm = row[0].strip().lower()
            # the spoken list has a stray "#N/A" row
            if row[1].strip().isdigit() and lm not in ANNOTATIONS:
                entry(lm)[key] = int(row[1])
    for name in ("ngsl-forms.csv", "spoken-forms.csv"):
        for row in _rows(name):
            forms = [f.strip().lower() for f in row if f.strip()]
            entry(forms[0])["forms"].update(forms)
    for name in ("cefrj-vocab.csv", "octanove-c1c2.csv"):
        rows = _rows(name)
        col = rows[0].index("CEFR")
        for row in rows[1:]:
            level = row[col].strip().upper()
            if level not in CEFR:
                continue
            # "adviser/advisor", "a.m./A.M./am/AM": spelling variants of one word
            variants = [v.strip().lower() for v in row[0].split("/") if v.strip()]
            for v in variants:
                e = entry(v)
                if e["cefr"] is None or level_index(level) < level_index(e["cefr"]):
                    e["cefr"] = level
            for v in variants[1:]:
                entry(variants[0])["forms"].add(v)

    forms: dict[str, str] = {}
    # Commonest lemma wins a shared form ("left": leave, not left).
    for lemma, info in sorted(words.items(), key=lambda kv: kv[1]["ngsl_rank"] or 10**6, reverse=True):
        for f in info["forms"]:
            forms[f] = lemma
    return {"words": words, "forms": forms}


def write_table(words: dict) -> None:
    with open(TABLE, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["word", "cefr", "ngsl_rank", "spoken_rank", "forms"])
        for lemma, i in sorted(words.items(), key=lambda kv: (kv[1]["ngsl_rank"] or 10**6, kv[0])):
            w.writerow([lemma, i["cefr"] or "", i["ngsl_rank"] or "", i["spoken_rank"] or "",
                        " ".join(sorted(i["forms"] - {lemma}))])


def lemma(token: str, table: dict) -> str | None:
    forms, words = table["forms"], table["words"]
    if token in forms:
        return forms[token]
    for suffix, repl in SUFFIXES:
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            stem = token[: -len(suffix)] + repl
            if stem in words:
                return stem
    return None


def lemmas(text: str, table: dict) -> set[str]:
    """Lemmas of every listed word in `text`, single words and multi-word entries."""
    low = text.lower()
    found = {lm for t in TOKEN_RE.findall(low) if (lm := lemma(t, table))}
    for phrase in phrases(table):
        if phrase in low and re.search(rf"\b{re.escape(phrase)}\b", low):
            found.add(phrase)
    return found


def phrases(table: dict) -> tuple[str, ...]:
    if "phrases" not in table:
        table["phrases"] = tuple(w for w in table["words"] if " " in w)
    return table["phrases"]


def deck_coverage(table: dict) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """({lemma: card ids testing it}, {lemma: card ids where it's only in the sentence})
    across shared and own cards, whether or not the learner's level includes them."""
    tested: dict[str, list[str]] = {}
    seen: dict[str, list[str]] = {}
    for _, data, _ in content_files():
        for card in data.get("cards", []):
            text = card.get("text", "")
            answers = " ".join(m.group(1) for m in CLOZE_RE.finditer(text))
            hit = lemmas(answers, table)
            for lm in hit:
                tested.setdefault(lm, []).append(card["id"])
            for lm in lemmas(CLOZE_RE.sub(r"\1", text), table) - hit:
                seen.setdefault(lm, []).append(card["id"])
    return tested, seen


def frequency_key(info: dict) -> tuple:
    """Spoken-list words first (conversation is the goal), then by general rank."""
    if info["spoken_rank"]:
        return (0, info["spoken_rank"])
    return (1, info["ngsl_rank"] or 10**6)


def default_levels(profile: dict) -> list[str]:
    """One band below the learner's level up to one above, capped at max_level:
    a B2 learner gets B1–C1. Below that is assumed known; above it, too far."""
    level = profile.get("level") or "B1"
    cap = level_index(profile["deck"].get("max_level") or "C1")
    i = level_index(level) if level in CEFR else 2
    return [CEFR[j] for j in range(max(0, i - 1), min(i + 1, cap) + 1)]


def gaps(table: dict, levels: list[str], spoken_only: bool = False,
         listed_only: bool = True) -> list[tuple[str, dict, list[str]]]:
    """(lemma, info, ids where it's only seen) for words at `levels` that no card
    tests, most frequent first. listed_only keeps words from the NGSL lists, so
    the ranking means something."""
    tested, seen = deck_coverage(table)
    out = []
    for lm, info in table["words"].items():
        if info["cefr"] not in levels or lm in tested:
            continue
        if spoken_only and not info["spoken_rank"]:
            continue
        if listed_only and not (info["ngsl_rank"] or info["spoken_rank"]):
            continue
        out.append((lm, info, seen.get(lm, [])))
    return sorted(out, key=lambda r: frequency_key(r[1]))


def text_profile(texts: list[str]) -> dict | None:
    """Distinct listed words in the learner's writing by CEFR level, and the share
    above B1. Counts types, not tokens, so repeating one word doesn't inflate it.
    Numbers only — never the words — so report.py can carry it."""
    table = load()
    if not table:
        return None
    found: set[str] = set()
    for t in texts:
        found |= lemmas(t, table)
    by_level = Counter(table["words"][lm]["cefr"] for lm in found if table["words"][lm]["cefr"])
    n = sum(by_level.values())
    if not n:
        return None
    above = sum(v for lv, v in by_level.items() if level_index(lv) > level_index("B1"))
    return {"types": n, "above_b1": round(above / n, 3),
            "by_level": {lv: by_level[lv] for lv in CEFR if by_level[lv]}}


# --- terminal ----------------------------------------------------------------


def show_word(word: str, table: dict) -> None:
    lm = lemma(word.lower(), table) or word.lower()
    info = table["words"].get(lm)
    if not info:
        print(f"'{word}' isn't in the word lists.")
        return
    tested, seen = deck_coverage(table)
    rank = f"NGSL #{info['ngsl_rank']}" if info["ngsl_rank"] else "not in NGSL"
    spoken = f", spoken #{info['spoken_rank']}" if info["spoken_rank"] else ""
    print(f"{lm}  {info['cefr'] or '?'}  ({rank}{spoken})")
    if info["forms"] - {lm}:
        print(f"  forms: {', '.join(sorted(info['forms'] - {lm}))}")
    print(f"  tested by: {', '.join(tested.get(lm, [])) or 'no card'}")
    if seen.get(lm):
        print(f"  seen in:   {', '.join(seen[lm][:8])}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", action="store_true", help="download the word lists")
    ap.add_argument("--level", help="comma-separated CEFR levels (default: around yours)")
    ap.add_argument("--spoken", action="store_true", help="only NGSL-Spoken words")
    ap.add_argument("-n", type=int, default=40, help="how many gaps to list (default 40)")
    ap.add_argument("--word", help="look up one word")
    ap.add_argument("--tsv", action="store_true", help="machine-readable gap list")
    args = ap.parse_args()

    if args.fetch:
        fetch()
        return 0
    table = load()
    if not table:
        print("Word lists not downloaded yet. Run: ./english vocab --fetch", file=sys.stderr)
        return 1
    if args.word:
        show_word(args.word, table)
        return 0

    profile = load_profile()
    levels = ([lv.strip().upper() for lv in args.level.split(",")] if args.level
              else default_levels(profile))
    if bad := [lv for lv in levels if lv not in CEFR]:
        sys.exit(f"unknown level(s): {', '.join(bad)}")
    rows = gaps(table, levels, args.spoken)

    if args.tsv:
        print("word\tcefr\tngsl_rank\tspoken_rank\tseen_in")
        for lm, i, seen in rows[: args.n]:
            print(f"{lm}\t{i['cefr']}\t{i['ngsl_rank'] or ''}\t{i['spoken_rank'] or ''}\t{','.join(seen)}")
        return 0

    tested, _ = deck_coverage(table)
    print(f"Words at {'/'.join(levels)}{' (spoken list)' if args.spoken else ''} "
          f"that no card makes you produce: {len(rows)}")
    for lv in levels:
        pool = [lm for lm, i in table["words"].items() if i["cefr"] == lv
                and (i["ngsl_rank"] or i["spoken_rank"]) and (not args.spoken or i["spoken_rank"])]
        if pool:
            done = sum(1 for lm in pool if lm in tested)
            print(f"  {lv}: {done}/{len(pool)} frequent words tested ({100 * done // len(pool)}%)")
    print(f"\nMost frequent {min(args.n, len(rows))}, commonest first (* = spoken list,"
          f" ~ = already in a card sentence but not as an answer):")
    for lm, i, seen in rows[: args.n]:
        mark = ("*" if i["spoken_rank"] else " ") + ("~" if seen else " ")
        print(f"  {mark} {lm:<18} {i['cefr']}  #{i['ngsl_rank'] or '—'}")
    print("\n/mine vocab turns these into cards about your own life.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
