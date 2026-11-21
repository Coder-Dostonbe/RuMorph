"""Builds the translations file shipped with the app from the admin panel's exports.

    python tools/translations/merge.py Tilsim-tarjimalar.json [more exports...]
    python tools/translations/merge.py --check

The admin enters translations on a device and exports them ("Tilsim-tarjimalar.json": every
translation that device knows, the shipped ones included). This merges one or more exports into
apps/client/src/data/translations.json:

- for every word the newest entry wins (updated_at);
- an export also lists the words whose translation the admin removed ("removed"); such a word
  is dropped if the removal is newer than its entry. A word merely missing from an export (a
  device with an older build) is kept;
- every lexeme id must exist in the app's lexicon, and every text must be non-empty and at most
  200 characters, or nothing is written.

--check only validates the shipped file (CI). Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHIPPED = ROOT / "apps" / "client" / "src" / "data" / "translations.json"
MAX_LENGTH = 200
FORMAT = "tilsim-translations"


class MergeError(Exception):
    pass


def lexeme_ids() -> set[str]:
    sys.path.insert(0, str(ROOT / "core" / "src"))
    from tilsim_core.engine.lexicon import default_lexicon

    return set(default_lexicon().lexemes)


def read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise MergeError(f"{path}: cannot read: {e}") from e
    if not isinstance(data, dict) or data.get("format") != FORMAT or data.get("version") != 1:
        raise MergeError(f"{path}: not a {FORMAT} version 1 file")
    if not isinstance(data.get("translations"), list):
        raise MergeError(f"{path}: no translations list")
    return data


def validate(entries: list, known: set[str], where: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise MergeError(f"{where}: entry {i} is not an object")
        lexeme_id, lemma, text, at = (e.get(k) for k in ("lexeme_id", "lemma", "translation", "updated_at"))
        if not all(isinstance(v, str) for v in (lexeme_id, lemma, text, at)):
            raise MergeError(f"{where}: entry {i} needs lexeme_id, lemma, translation, updated_at as text")
        text = text.strip()
        if lexeme_id not in known:
            raise MergeError(f"{where}: unknown lexeme {lexeme_id!r}")
        if not text or len(text) > MAX_LENGTH:
            raise MergeError(f"{where}: translation of {lexeme_id!r} must be 1-{MAX_LENGTH} characters")
        if lexeme_id in out:
            raise MergeError(f"{where}: {lexeme_id!r} appears twice")
        out[lexeme_id] = {"lexeme_id": lexeme_id, "lemma": lemma, "translation": text, "updated_at": at}
    return out


def validate_removed(items: list, where: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for i, e in enumerate(items):
        if not isinstance(e, dict) or not isinstance(e.get("lexeme_id"), str) or not isinstance(e.get("updated_at"), str):
            raise MergeError(f"{where}: removed entry {i} needs lexeme_id and updated_at as text")
        out[e["lexeme_id"]] = e["updated_at"]
    return out


def merge(shipped: dict[str, dict], exports: list[tuple[dict[str, dict], dict[str, str]]]) -> dict[str, dict]:
    """exports: (entries, removed: lexeme id -> time of removal) of each export file."""
    result = dict(shipped)
    newest_removal: dict[str, str] = {}
    for entries, removed in exports:
        for lexeme_id, entry in entries.items():
            have = result.get(lexeme_id)
            if have is None or entry["updated_at"] >= have["updated_at"]:
                result[lexeme_id] = entry
        for lexeme_id, at in removed.items():
            newest_removal[lexeme_id] = max(at, newest_removal.get(lexeme_id, ""))
    for lexeme_id, at in newest_removal.items():
        if lexeme_id in result and at >= result[lexeme_id]["updated_at"]:
            del result[lexeme_id]
    return result


def render(entries: dict[str, dict]) -> str:
    data = {"format": FORMAT, "version": 1, "translations": [entries[k] for k in sorted(entries)]}
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("exports", nargs="*", type=Path)
    parser.add_argument("--check", action="store_true", help="only validate the shipped file")
    args = parser.parse_args(argv)
    try:
        known = lexeme_ids()
        shipped = validate(read(SHIPPED)["translations"], known, str(SHIPPED))
        if args.check:
            print(f"{SHIPPED.relative_to(ROOT)}: {len(shipped)} translations, valid")
            return 0
        if not args.exports:
            parser.error("give at least one export file, or --check")
        exports = []
        for path in args.exports:
            data = read(path)
            removed = data.get("removed", [])
            if not isinstance(removed, list):
                raise MergeError(f"{path}: removed must be a list")
            exports.append((validate(data["translations"], known, str(path)), validate_removed(removed, str(path))))
        result = merge(shipped, exports)
    except MergeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    SHIPPED.write_text(render(result), encoding="utf-8")
    added = len(set(result) - set(shipped))
    removed = len(set(shipped) - set(result))
    changed = sum(1 for k in set(result) & set(shipped) if result[k] != shipped[k])
    print(f"{len(result)} translations ({added} added, {changed} changed, {removed} removed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
