"""Pronunciation audio for the app.

Single recordings: the app asks the API, the API fetches them from Wikimedia Commons.
Voice packs (every word in one file, tools/pronunciation/pack.py): the API streams them from
the project's "voice-packs" GitHub release; only pack file names are accepted.

The app's list (apps/client/src/data/pronunciations.json, made by tools/pronunciation/build.py)
names each recording by its path under upload.wikimedia.org/wikipedia/commons/. Only Russian
pronunciation files are served: Lingua Libre ("LL-Q7737_(rus)-...") and "Ru-..." files, in
the original or a Commons transcode, so this is not an open proxy.
"""

from __future__ import annotations

import re
from urllib.parse import quote, unquote

UPLOAD = "https://upload.wikimedia.org/wikipedia/commons/"
PREFIX = "/v1/audio/"
MAX_BYTES = 2 * 1024 * 1024
EXTENSIONS = (".wav", ".ogg", ".oga", ".mp3", ".flac", ".opus", ".webm")
CONTENT_TYPES = ("audio/", "application/ogg", "video/ogg", "video/webm")

_ORIGINAL = re.compile(r"^[0-9a-f]/[0-9a-f]{2}/(?P<name>[^/]+)$")
_TRANSCODED = re.compile(r"^transcoded/[0-9a-f]/[0-9a-f]{2}/(?P<name>[^/]+)/(?P=name)\.(?:mp3|ogg|oga|opus|webm)$")


def _russian_pronunciation(name: str) -> bool:
    lower = name.lower()
    return (name.startswith("LL-Q7737_(rus)-") or lower.startswith("ru-")) and lower.endswith(EXTENSIONS) \
        and ".." not in name and "\\" not in name


def target(request_path: str) -> str | None:
    """'/v1/audio/<path>' (percent-encoded) -> the Commons URL, or None if it is not a Russian
    pronunciation file."""
    if not request_path.startswith(PREFIX):
        return None
    path = unquote(request_path[len(PREFIX):])
    match = _ORIGINAL.match(path) or _TRANSCODED.match(path)
    if not match or not _russian_pronunciation(match.group("name")):
        return None
    return UPLOAD + quote(path, safe="/()_-.,~!*'")


PACK_PREFIX = "/v1/voice-packs/"
PACK_RELEASE = "https://github.com/Coder-Dostonbe/RuMorph/releases/download/voice-packs/"
_PACK = re.compile(r"^zabon-voice-[a-z0-9-]{1,40}-[0-9]{1,4}\.(?P<kind>bin|sample\.ogg)$")


def pack_target(request_path: str) -> tuple[str, str] | None:
    """'/v1/voice-packs/zabon-voice-vosk-f1-1.bin' -> (release URL, content type)."""
    if not request_path.startswith(PACK_PREFIX):
        return None
    match = _PACK.match(request_path[len(PACK_PREFIX):])
    if not match:
        return None
    content_type = "application/octet-stream" if match.group("kind") == "bin" else "audio/ogg"
    return PACK_RELEASE + match.group(0), content_type


def acceptable(content_type: str) -> bool:
    return content_type.split(";")[0].strip().lower().startswith(CONTENT_TYPES)
