"""Adds draft translations (not checked by anyone yet) to the file shipped with the app.

    python tools/translations/drafts.py drafts.tsv [more.tsv ...]

Each line of a draft file: lexeme_id, translation, then example pairs (Russian, Uzbek), separated
by tabs. Lines starting with # and empty lines are skipped.

A draft goes in with "verified": false (the app marks it "not checked") and an old date
(DRAFT_AT), so any entry the admin makes, now or later, wins over it. A word that already has a
checked translation in the shipped file is left alone. Everything is validated as in merge.py
(known lexeme ids, lengths, at most 3 examples) before anything is written.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import merge  # noqa: E402

DRAFT_AT = "2026-01-01T00:00:00.000Z"


def parse(path: Path) -> list[dict]:
    entries = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        cells = [c.strip() for c in line.split("\t")]
        if len(cells) < 2 or len(cells) % 2:
            raise merge.MergeError(f"{path}:{n}: expected lexeme_id, translation and example pairs")
        lexeme_id, translation, rest = cells[0], cells[1], cells[2:]
        entries.append({
            "lexeme_id": lexeme_id,
            "lemma": lexeme_id.split("|")[0],
            "translation": translation,
            "updated_at": DRAFT_AT,
            "examples": [{"ru": rest[i], "uz": rest[i + 1]} for i in range(0, len(rest), 2)],
            "verified": False,
        })
    return entries


def add_drafts(shipped: dict[str, dict], drafts: dict[str, dict]) -> tuple[dict[str, dict], int]:
    result = dict(shipped)
    added = 0
    for lexeme_id, entry in drafts.items():
        have = result.get(lexeme_id)
        if have is not None and have.get("verified", True):
            continue   # a checked translation stays
        result[lexeme_id] = entry
        added += 1
    return result, added


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args(argv)
    try:
        known = merge.lexeme_ids()
        shipped = merge.validate(merge.read(merge.SHIPPED)["translations"], known, str(merge.SHIPPED))
        raw = [e for path in args.files for e in parse(path)]
        drafts = merge.validate(raw, known, "drafts")
    except merge.MergeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    result, added = add_drafts(shipped, drafts)
    merge.SHIPPED.write_text(merge.render(result), encoding="utf-8")
    print(f"{len(result)} translations ({added} drafts written, {len(drafts) - added} kept as checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
