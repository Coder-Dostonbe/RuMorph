"""Exports lexemes from the OpenCorpora dictionary into Tilsim's lexicon format.

Which lexemes: the hand-picked seed list (tools/lexicon/seed_lemmas.txt, with
the hard cases a learner meets early) plus the TOP_LEMMAS most frequent
lemmas of Russian by wordfreq. wordfreq counts word forms; a form's frequency
is shared among the lemmas it can belong to in proportion to pymorphy3's
probability estimate (стали: стать / сталь), and a lemma's frequency is the
sum over its forms. Proper names, abbreviations and forms the dictionary marks
as informal, archaic or erroneous are not counted.

Source: OpenCorpora (https://opencorpora.org), CC BY-SA 3.0, read through the
compiled copy in the PyPI package `pymorphy3-dicts-ru` (the opencorpora.org
download is not reachable from every build machine). pymorphy3 is used only
here, as a reader; the app's engine never imports it.

Output (core/src/tilsim_core/data/ru_core.json):

    {
      "package": "ru-core", "version": "...", "source": {...},
      "tags": ["NOUN,inan,masc sing,nomn", ...],          # shared tag table
      "paradigms": [[[prefix, suffix, tag_index], ...], ...],
      "lexemes": [[stem, paradigm_index], ...]
    }

A word form is prefix + stem + suffix. Form 0 of a paradigm is the lemma (the
dictionary form). Paradigms are shared by every lexeme that inflects the same
way, which keeps the file small.

Frequencies: wordfreq (https://github.com/rspeer/wordfreq), data CC BY-SA 4.0.
Each lexeme gets its Zipf value (log10 of occurrences per billion words) in
"freq", null when wordfreq has none of its forms.

Usage (from the repository root; versions as pinned in .github/workflows/ci.yml):
    uv run --with pymorphy3 --with pymorphy3-dicts-ru --with wordfreq python tools/lexicon/export_opencorpora.py
    uv run --with pymorphy3 --with pymorphy3-dicts-ru --with wordfreq python tools/lexicon/export_opencorpora.py --check
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = Path(__file__).with_name("seed_lemmas.txt")
ERRATA = Path(__file__).with_name("errata.txt")
OUT = ROOT / "core" / "src" / "tilsim_core" / "data" / "ru_core.json"
PACKAGE_VERSION = "0.3.0"
TOP_LEMMAS = 3000           # most frequent lemmas taken in addition to the seed list
TOP_FORMS = 40000           # wordfreq forms looked at to rank the lemmas
# Lemmas with these grammemes are not taken from the frequency list (names, abbreviations, …).
NOT_COUNTED = frozenset({"Name", "Surn", "Patr", "Geox", "Orgn", "Trad", "Abbr", "Init",
                         "Infr", "Slng", "Arch", "Erro", "Dist"})


def read_seed(path: Path) -> list[tuple[str, str | None, frozenset[str]]]:
    """Lines: lemma [POS [grammeme,grammeme…]]. The grammemes, if given, must all be in the
    lemma's tag; they pick one of several homonyms (писать VERB tran: to write, not пи́сать)."""
    seen: set[tuple[str, str | None, frozenset[str]]] = set()
    items: list[tuple[str, str | None, frozenset[str]]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) > 3:
            raise SystemExit(f"bad seed line: {line!r}")
        item = (parts[0], parts[1] if len(parts) > 1 else None,
                frozenset(parts[2].split(",")) if len(parts) > 2 else frozenset())
        if item not in seen:
            seen.add(item)
            items.append(item)
    return items


def read_errata(path: Path) -> dict[tuple[str, str, str], str]:
    """(lemma, tag, wrong form) → right form."""
    errata = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 5:
            raise SystemExit(f"bad errata line: {line!r}")
        errata[(parts[0], parts[1], parts[2])] = parts[3]
    return errata


def _dictionary_parses(morph, word: str) -> list:
    return [p for p in morph.parse(word) if type(p.methods_stack[0][0]).__name__ == "DictionaryAnalyzer"]


def form_shares(morph, word: str) -> dict[tuple[str, int], float]:
    """How a form's occurrences divide among lexemes (normal form, paradigm id)."""
    parses = _dictionary_parses(morph, word)
    total = sum(p.score for p in parses)
    shares: dict[tuple[str, int], float] = {}
    if total:
        for p in parses:
            key = (p.normal_form, p.methods_stack[0][2])
            shares[key] = shares.get(key, 0.0) + p.score / total
    return shares


def frequent_lemmas(morph, count: int) -> list[tuple[str, int]]:
    """The `count` most frequent lexemes (normal form, paradigm id) by wordfreq."""
    import wordfreq

    totals: dict[tuple[str, int], float] = {}
    excluded: set[tuple[str, int]] = set()
    for word in wordfreq.top_n_list("ru", TOP_FORMS):
        frequency = wordfreq.word_frequency(word, "ru")
        for p in _dictionary_parses(morph, word):
            if NOT_COUNTED & set(p.normalized.tag.grammemes):
                excluded.add((p.normal_form, p.methods_stack[0][2]))
        for key, share in form_shares(morph, word).items():
            totals[key] = totals.get(key, 0.0) + frequency * share
    ranked = sorted((k for k in totals if k not in excluded), key=lambda k: (-totals[k], k))
    return ranked[:count]


def lexeme_zipf(morph, forms: list[str], key: tuple[str, int]) -> float | None:
    """Zipf frequency of a lexeme: the sum of its forms' frequencies, each times this lexeme's share."""
    import wordfreq

    total = 0.0
    for form in set(forms):
        frequency = wordfreq.word_frequency(form, "ru")
        if frequency:
            total += frequency * form_shares(morph, form).get(key, 0.0)
    return round(math.log10(total * 1e9), 2) if total > 0 else None


def export(check: bool = False) -> dict:
    import pymorphy3

    morph = pymorphy3.MorphAnalyzer()
    dictionary = morph.dictionary
    meta = dict(dictionary.meta)

    tags: dict[str, int] = {}
    paradigms: dict[tuple, int] = {}
    lexemes: dict[tuple[str, int], str] = {}   # (stem, paradigm) -> lemma, for stable sorting
    zipf: dict[tuple[str, int], float | None] = {}
    missing: list[str] = []

    errata = read_errata(ERRATA)
    applied: set[tuple[str, str, str]] = set()

    def add(word: str, para_id: int, idx: int, lemma: str) -> None:
        stem = dictionary.build_stem(dictionary.paradigms[para_id], idx, word)
        rows = []
        forms = []
        for prefix, tag, suffix in dictionary.build_paradigm_info(para_id):
            right = errata.get((lemma, str(tag), prefix + stem + suffix))
            if right is not None:
                if not right.startswith(prefix + stem):
                    raise SystemExit(f"erratum for {lemma} must keep the stem {prefix + stem!r}")
                applied.add((lemma, str(tag), prefix + stem + suffix))
                suffix = right[len(prefix + stem):]
            rows.append((prefix, suffix, tags.setdefault(str(tag), len(tags))))
            forms.append(prefix + stem + suffix)
        paradigm_index = paradigms.setdefault(tuple(rows), len(paradigms))
        if (stem, paradigm_index) not in lexemes:
            lexemes[(stem, paradigm_index)] = lemma
            zipf[(stem, paradigm_index)] = lexeme_zipf(morph, forms, (lemma, para_id))

    for lemma, pos, required in read_seed(SEED):
        found = False
        for parse in morph.parse(lemma):
            analyzer, word, para_id, idx = parse.methods_stack[0]
            if type(analyzer).__name__ != "DictionaryAnalyzer" or parse.normal_form != lemma:
                continue
            # Verbs are listed by their infinitive (INFN); participles and gerunds share the lexeme.
            lemma_pos = parse.normalized.tag.POS
            if pos is not None and lemma_pos != pos and not (pos == "VERB" and lemma_pos == "INFN"):
                continue
            if required and not required <= set(parse.normalized.tag.grammemes):
                continue
            add(word, para_id, idx, lemma)
            found = True
        if not found:
            missing.append(" ".join([lemma, pos or "", ",".join(sorted(required))]).strip())

    if missing:
        print(f"not found in OpenCorpora ({len(missing)}): {', '.join(missing)}", file=sys.stderr)

    for normal_form, para_id in frequent_lemmas(morph, TOP_LEMMAS):
        # Paradigm row 0 is the lemma: build the lexeme from it.
        prefix, tag, suffix = dictionary.build_paradigm_info(para_id)[0]
        for p in morph.parse(normal_form):
            if p.methods_stack[0][2] == para_id and p.normal_form == normal_form:
                _, word, _, idx = p.methods_stack[0]
                add(word, para_id, idx, normal_form)
                break

    if set(errata) - applied:
        raise SystemExit(f"errata not found in the dictionary: {sorted(set(errata) - applied)}")

    ordered = sorted(lexemes.items(), key=lambda kv: (kv[1], kv[0][1], kv[0][0]))
    data = {
        "package": "ru-core",
        "version": PACKAGE_VERSION,
        "description": "Core Russian lexicon: the seed list and the most frequent lemmas, with full paradigms.",
        "source": {
            "name": "OpenCorpora",
            "url": "https://opencorpora.org",
            "license": "CC BY-SA 3.0",
            "version": meta.get("source_version"),
            "revision": meta.get("source_revision"),
            "via": f"pymorphy3-dicts-ru {importlib.metadata.version('pymorphy3-dicts-ru')}",
            "errata": len(applied),
        },
        "frequency": {
            "name": "wordfreq",
            "url": "https://github.com/rspeer/wordfreq",
            "license": "CC BY-SA 4.0",
            "version": importlib.metadata.version("wordfreq"),
            "top_lemmas": TOP_LEMMAS,
        },
        "tags": list(tags),
        "paradigms": [[list(row) for row in rows] for rows in paradigms],
        "lexemes": [[stem, paradigm_index] for (stem, paradigm_index), _ in ordered],
        "freq": [zipf[key] for key, _ in ordered],
    }
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current.strip() != text:
            raise SystemExit(f"{OUT} is out of date: run tools/lexicon/export_opencorpora.py")
        print("lexicon is up to date")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)}: {len(data['lexemes'])} lexemes, "
              f"{len(data['paradigms'])} paradigms, {len(data['tags'])} tags, {len(text) // 1024} KB")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail if the exported file is out of date")
    export(check=parser.parse_args().check)


if __name__ == "__main__":
    main()
