"""Finds a recorded pronunciation on Wikimedia Commons for every word of the app's lexicon.

    python tools/pronunciation/build.py               # writes apps/client/src/data/pronunciations.json
    python tools/pronunciation/build.py --out FILE
    python tools/pronunciation/build.py --check       # validates the shipped file (CI, offline)

Sources (license approved by the project owner, docs/DECISIONS.md, 2026-11-25):

- Lingua Libre recordings, files named "LL-Q7737 (rus)-<speaker>-<word>.<ext>";
- older Commons files named "Ru-<word>.ogg".

Only files under a free license that allows redistribution are kept (CC BY-SA, CC BY, CC0,
public domain). The audio is not copied here: the file stores where each recording is on
upload.wikimedia.org and who recorded it under which license, so the app can credit the
speaker. The API serves the audio from there (apps/api, /v1/audio/...).

For each word the recording of the speaker who covers most of the lexicon is preferred, so the
voices change as little as possible. Words whose spelling has two pronunciations (stress
homographs) get no recording: a recording of the other word would teach a wrong stress.

Standard library only. Needs internet (Commons API) except with --check.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHIPPED = ROOT / "apps" / "client" / "src" / "data" / "pronunciations.json"
API = "https://commons.wikimedia.org/w/api.php"
UPLOAD = "https://upload.wikimedia.org/wikipedia/commons/"
USER_AGENT = "ZabonPronunciations/1.0 (https://github.com/Coder-Dostonbe/RuMorph)"
FORMAT = "zabon-pronunciations"
VERSION = 1
LL_PREFIX = "LL-Q7737 (rus)-"
EXTENSIONS = (".wav", ".ogg", ".oga", ".mp3", ".flac", ".opus", ".webm")

# Same spelling, different stress: за́мок / замо́к, о́рган / орга́н, про́пасть / пропа́сть.
HOMOGRAPHS = {"замок", "орган", "пропасть"}

# Licenses that allow redistributing the file with attribution. Normalised by `license_code`.
LICENSES = {
    "CC BY-SA 4.0", "CC BY-SA 3.0", "CC BY-SA 2.5", "CC BY-SA 2.0", "CC BY-SA 1.0",
    "CC BY 4.0", "CC BY 3.0", "CC BY 2.5", "CC BY 2.0", "CC BY 1.0",
    "CC0", "Public domain",
}

# A path under UPLOAD: "a/ab/Name.ext" or "transcoded/a/ab/Name.ext/Name.ext.mp3".
PATH_RE = re.compile(r"^(?:transcoded/)?[0-9a-f]/[0-9a-f]{2}/[^/]+(?:/[^/]+)?$")


class BuildError(Exception):
    pass


# --- pure helpers (tested in test_build.py) ------------------------------------------------------

def normalize(word: str) -> str:
    """Lowercase, no stress marks; ё stays ё."""
    return word.replace("́", "").replace("̀", "").strip().lower()


def index(words: set[str]) -> dict[str, str]:
    """Spelling in a file name -> lexicon word. A file without ё ('еж') stands for the word with
    ё ('ёж'): the letter is often left out, the pronunciation is the same."""
    keys = {w.replace("ё", "е"): w for w in words if "ё" in w}
    keys.update({w: w for w in words})
    return keys


def parse_ll(name: str, keys: dict[str, str]) -> tuple[str, str] | None:
    """'LL-Q7737 (rus)-Infovarius-кто-то.wav' -> ('Infovarius', 'кто-то') when the word is ours.
    Speaker names and words may both contain '-', so every split point is tried, the
    shortest speaker name first. A longer "speaker" with Cyrillic in it is a compound word
    ('Cinemantique-ковид-тест' is not 'тест'), and a word written with a leading hyphen is a
    suffix ('-либо'), not the word."""
    if not name.startswith(LL_PREFIX):
        return None
    stem, dot, ext = name[len(LL_PREFIX):].rpartition(".")
    if not dot or "." + ext.lower() not in EXTENSIONS:
        return None
    for position, char in enumerate(stem):
        if char == "-" and position > 0:
            if "-" in stem[:position] and re.search(r"[\u0400-\u04ff]", stem[:position]):
                break
            if stem[position - 1] == "-":
                continue  # 'Lvova--либо': the word is the suffix '-либо'
            word = keys.get(normalize(stem[position + 1:]))
            if word:
                return stem[:position], word
    return None


def parse_ru(name: str, keys: dict[str, str]) -> str | None:
    """'Ru-книга.ogg' -> 'книга' when the word is ours."""
    if not name.lower().startswith("ru-"):
        return None
    stem, dot, ext = name[3:].rpartition(".")
    if not dot or "." + ext.lower() not in EXTENSIONS:
        return None
    return keys.get(normalize(stem))


def license_code(short_name: str) -> str | None:
    text = re.sub(r"\s+", " ", html.unescape(short_name or "")).strip()
    upper = text.upper().replace("-", " ").replace("_", " ")
    if upper in ("CC0", "CC0 1.0", "CC ZERO"):
        return "CC0"
    if upper.startswith("PUBLIC DOMAIN") or upper == "PD":
        return "Public domain"
    m = re.match(r"^CC (BY SA|BY) (\d\.\d)(?: ([A-Z]{2}))?$", upper)
    if not m:
        return None
    code = f"CC {m.group(1).replace(' ', '-')} {m.group(2)}"
    if code not in LICENSES:
        return None
    # A ported license ("CC BY 2.0 FR") keeps its jurisdiction in the credit.
    return f"{code} {m.group(3)}" if m.group(3) else code


def license_base(code: object) -> str | None:
    """'CC BY 2.0 FR' -> 'CC BY 2.0'."""
    if not isinstance(code, str):
        return None
    return re.sub(r" [A-Z]{2}$", "", code) if code.startswith("CC ") else code


def plain_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", html.unescape(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def credit(speaker: str, meta: dict) -> str:
    """Who to credit. Lingua Libre: the speaker in the file name (its "Artist" field reads
    "Speaker: X Recorder: X"). Other files: their attribution line, else the author."""
    if speaker != "Ru":
        return speaker
    for key in ("Attribution", "Artist", "Credit"):
        text = plain_text(meta.get(key, {}).get("value", ""))
        # "Audio sample provided by The Shtooka Project." -> "The Shtooka Project"
        text = re.sub(r"^(audio sample )?provided by\s+", "", text, flags=re.I).rstrip(". ")
        if text:
            return text
    return ""


def upload_path(url: str) -> str | None:
    if not url.startswith(UPLOAD):
        return None
    path = urllib.parse.unquote(url[len(UPLOAD):])
    return path if PATH_RE.match(path) else None


def choose(candidates: dict[str, list[tuple[str, str]]]) -> dict[str, tuple[str, str]]:
    """word -> [(speaker, title), ...]  =>  word -> (speaker, title): the speaker who covers
    the most words wins, then the alphabetically first title (stable output)."""
    coverage: dict[str, int] = {}
    for options in candidates.values():
        for speaker in {s for s, _ in options}:
            coverage[speaker] = coverage.get(speaker, 0) + 1
    chosen = {}
    for word, options in candidates.items():
        chosen[word] = min(options, key=lambda o: (-coverage[o[0]], o[1]))
    return chosen


def validate(data: dict, words: set[str]) -> None:
    if data.get("format") != FORMAT or data.get("version") != VERSION:
        raise BuildError("not a pronunciations file of this version")
    entries = data.get("words")
    if not isinstance(entries, dict):
        raise BuildError("'words' must be an object")
    for word, entry in entries.items():
        where = f"words[{word!r}]"
        if word not in words:
            raise BuildError(f"{where}: not in the lexicon")
        if word in HOMOGRAPHS:
            raise BuildError(f"{where}: a stress homograph must not have a recording")
        if not isinstance(entry, dict):
            raise BuildError(f"{where}: must be an object")
        path = entry.get("path")
        if not isinstance(path, str) or not PATH_RE.match(path):
            raise BuildError(f"{where}: bad path")
        if license_base(entry.get("license")) not in LICENSES:
            raise BuildError(f"{where}: license not allowed")
        for key in ("file", "author"):
            value = entry.get(key)
            if not isinstance(value, str) or not value.strip() or len(value) > 300:
                raise BuildError(f"{where}: bad {key}")


# --- Commons API ---------------------------------------------------------------------------------

def api(params: dict) -> dict:
    query = urllib.parse.urlencode({**params, "format": "json", "formatversion": "2", "maxlag": "5"})
    request = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.load(response)
        except OSError as exc:
            print(f"  retry after {exc!r}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
            continue
        if data.get("error", {}).get("code") == "maxlag":
            time.sleep(5 * (attempt + 1))
            continue
        if "error" in data:
            raise BuildError(f"Commons API: {data['error']}")
        time.sleep(0.2)
        return data
    raise BuildError("Commons API did not answer")


def lingua_libre(words: set[str]) -> dict[str, list[tuple[str, str]]]:
    found: dict[str, list[tuple[str, str]]] = {}
    keys = index(words)
    params = {"action": "query", "list": "allimages", "aiprefix": LL_PREFIX.replace(" ", "_"), "ailimit": "500"}
    total = 0
    while True:
        data = api(params)
        for image in data.get("query", {}).get("allimages", []):
            total += 1
            name = image["name"].replace("_", " ")
            parsed = parse_ll(name, keys)
            if parsed:
                speaker, word = parsed
                found.setdefault(word, []).append((speaker, "File:" + name))
        if "continue" not in data:
            break
        params.update(data["continue"])
        print(f"  Lingua Libre: {total} files read, {len(found)} words", file=sys.stderr)
    print(f"Lingua Libre: {total} Russian files, {len(found)} of our words", file=sys.stderr)
    return found


def old_ru_files(words: list[str]) -> dict[str, list[tuple[str, str]]]:
    found: dict[str, list[tuple[str, str]]] = {}
    keys = index(set(words))
    titles = [f"File:Ru-{w}.ogg" for w in words]
    for start in range(0, len(titles), 50):
        data = api({"action": "query", "titles": "|".join(titles[start:start + 50])})
        for page in data.get("query", {}).get("pages", []):
            if page.get("missing") or page.get("invalid"):
                continue
            word = parse_ru(page["title"][len("File:"):], keys)
            if word:
                found.setdefault(word, []).append(("Ru", page["title"]))
    print(f"Ru-*.ogg: {len(found)} more words", file=sys.stderr)
    return found


def file_info(titles: list[str]) -> dict[str, dict]:
    info = {}
    for start in range(0, len(titles), 50):
        data = api({
            "action": "query", "titles": "|".join(titles[start:start + 50]), "prop": "videoinfo",
            "viprop": "url|mime|user|extmetadata|derivatives",
            "viextmetadatafilter": "Artist|Attribution|Credit|LicenseShortName",
        })
        for page in data.get("query", {}).get("pages", []):
            items = page.get("videoinfo") or []
            if items:
                info[page["title"]] = items[0]
    return info


def best_path(item: dict) -> str | None:
    """A small file the webviews play: the MP3 or Ogg transcode, else the original."""
    derivatives = item.get("derivatives") or []
    for wanted in ("audio/mpeg", "audio/ogg"):
        for derivative in derivatives:
            if str(derivative.get("type", "")).startswith(wanted):
                path = upload_path(derivative.get("src", ""))
                if path:
                    return path
    if item.get("mime") in ("audio/mpeg", "audio/ogg", "audio/wav", "audio/x-wav", "audio/webm"):
        return upload_path(item.get("url", ""))
    return None


def build(words_list: list[str]) -> dict:
    words = set(words_list) - HOMOGRAPHS
    candidates = lingua_libre(words)
    missing = sorted(w for w in words if w not in candidates)
    for word, options in old_ru_files(missing).items():
        candidates.setdefault(word, []).extend(options)

    entries: dict[str, dict] = {}
    rejected: dict[str, int] = {}
    pending = dict(candidates)
    # Try the preferred speaker first; when that file is not usable, the next one.
    while pending:
        chosen = choose(pending)
        info = file_info([title for _, title in chosen.values()])
        retry = {}
        for word, (speaker, title) in chosen.items():
            item = info.get(title)
            meta = (item or {}).get("extmetadata", {})
            license = license_code(meta.get("LicenseShortName", {}).get("value", ""))
            author = credit(speaker, meta)
            path = best_path(item) if item else None
            if item and license and author and path:
                entries[word] = {"file": title[len("File:"):], "path": path, "author": author[:300], "license": license}
                continue
            reason = "no_info" if not item else "license" if not license else "author" if not author else "format"
            rejected[reason] = rejected.get(reason, 0) + 1
            if rejected[reason] <= 5:
                print(f"  rejected ({reason}): {title}", file=sys.stderr)
            rest = [o for o in pending[word] if o[1] != title]
            if rest:
                retry[word] = rest
        pending = retry

    print(f"usable recordings: {len(entries)} of {len(words_list)} words; rejected files: {rejected}", file=sys.stderr)
    return {
        "format": FORMAT,
        "version": VERSION,
        "source": "Wikimedia Commons (Lingua Libre)",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "homographs": sorted(HOMOGRAPHS & set(words_list)),
        "words": dict(sorted(entries.items())),
    }


def lexicon_words() -> list[str]:
    sys.path.insert(0, str(ROOT / "core" / "src"))
    from tilsim_core.engine.lexicon import default_lexicon

    return sorted({lexeme_id.split("|")[0] for lexeme_id in default_lexicon().lexemes})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=SHIPPED)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    words = lexicon_words()
    try:
        if args.check:
            data = json.loads(SHIPPED.read_text(encoding="utf-8"))
            validate(data, set(words))
            print(f"{SHIPPED.relative_to(ROOT)}: {len(data['words'])} recordings, ok")
            return 0
        data = build(words)
        validate(data, set(words))
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    text = json.dumps(data, ensure_ascii=False, indent=0, separators=(",", ":")) + "\n"
    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out} ({len(data['words'])} recordings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
