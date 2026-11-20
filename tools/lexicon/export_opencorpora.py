"""Exports lexemes from the OpenCorpora dictionary into Tilsim's lexicon format.

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

Usage (from the repository root):
    uv run --with pymorphy3 --with pymorphy3-dicts-ru python tools/lexicon/export_opencorpora.py
    uv run --with pymorphy3 --with pymorphy3-dicts-ru python tools/lexicon/export_opencorpora.py --check
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = Path(__file__).with_name("seed_lemmas.txt")
OUT = ROOT / "core" / "src" / "tilsim_core" / "data" / "ru_core.json"
PACKAGE_VERSION = "0.2.0"


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


def export(check: bool = False) -> dict:
    import pymorphy3

    morph = pymorphy3.MorphAnalyzer()
    dictionary = morph.dictionary
    meta = dict(dictionary.meta)

    tags: dict[str, int] = {}
    paradigms: dict[tuple, int] = {}
    lexemes: dict[tuple[str, int], str] = {}   # (stem, paradigm) -> lemma, for stable sorting
    missing: list[str] = []

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
            stem = dictionary.build_stem(dictionary.paradigms[para_id], idx, word)
            rows = []
            for prefix, tag, suffix in dictionary.build_paradigm_info(para_id):
                rows.append((prefix, suffix, tags.setdefault(str(tag), len(tags))))
            key = tuple(rows)
            paradigm_index = paradigms.setdefault(key, len(paradigms))
            lexemes[(stem, paradigm_index)] = lemma
            found = True
        if not found:
            missing.append(" ".join([lemma, pos or "", ",".join(sorted(required))]).strip())

    if missing:
        print(f"not found in OpenCorpora ({len(missing)}): {', '.join(missing)}", file=sys.stderr)

    ordered = sorted(lexemes.items(), key=lambda kv: (kv[1], kv[0][1], kv[0][0]))
    data = {
        "package": "ru-core",
        "version": PACKAGE_VERSION,
        "description": "Core Russian lexicon (A1-A2) with full inflection paradigms.",
        "source": {
            "name": "OpenCorpora",
            "url": "https://opencorpora.org",
            "license": "CC BY-SA 3.0",
            "version": meta.get("source_version"),
            "revision": meta.get("source_revision"),
            "via": f"pymorphy3-dicts-ru {importlib.metadata.version('pymorphy3-dicts-ru')}",
        },
        "tags": list(tags),
        "paradigms": [[list(row) for row in rows] for rows in paradigms],
        "lexemes": [[stem, paradigm_index] for (stem, paradigm_index), _ in ordered],
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
