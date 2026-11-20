"""JSON bridge between the TypeScript app and tilsim_core.

The app sends one request at a time as a JSON string and gets one JSON string
back, the same way ArabMorph's desktop shell talks to its sidecar. Under
Pyodide the request arrives from a Web Worker; on the server the API calls
`dispatch` directly.

Request:  {"id": <str|int>, "op": <str>, "args": {...}}
Reply:    {"id": ..., "ok": true,  "result": ...}
       or {"id": ..., "ok": false, "error": {"code": <str>, "message": <str>}}

Every request is validated here rather than trusted. An unexpected exception
never leaks a traceback to the caller: the reply says "internal" and the
traceback goes to stderr, where the host can log it.
"""

from __future__ import annotations

import json
import platform
import sys
import traceback
from collections.abc import Callable
from typing import Any

from . import PROTOCOL_VERSION, __version__

MAX_REQUEST_BYTES = 1_000_000


class BridgeError(Exception):
    """An error the caller can act on; its code and message are returned as they are."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _op_version(args: dict[str, Any]) -> dict[str, Any]:
    _expect_no_args(args)
    return {
        "core": __version__,
        "protocol": PROTOCOL_VERSION,
        "python": platform.python_version(),
        # "emscripten" under Pyodide (app), "linux" / "win32" / … under CPython.
        "platform": sys.platform,
    }


def _op_echo(args: dict[str, Any]) -> dict[str, Any]:
    """Round-trip check used by the app's start-up self test."""
    text = args.get("text")
    if not isinstance(text, str):
        raise BridgeError("invalid_args", "'text' must be a string")
    if len(text) > 1000:
        raise BridgeError("invalid_args", "'text' is longer than 1000 characters")
    return {"text": text}


LANGS = ("uz", "ru", "en")


def _lang(args: dict[str, Any]) -> str:
    lang = args.get("lang", "uz")
    if lang not in LANGS:
        raise BridgeError("invalid_args", "'lang' must be one of: uz, ru, en")
    return lang


def _only(args: dict[str, Any], *allowed: str) -> None:
    extra = set(args) - set(allowed)
    if extra:
        raise BridgeError("invalid_args", f"unexpected arguments: {', '.join(sorted(extra))}")


def _string(args: dict[str, Any], name: str, limit: int = 200) -> str:
    value = args.get(name)
    if not isinstance(value, str):
        raise BridgeError("invalid_args", f"'{name}' must be a string")
    if len(value) > limit:
        raise BridgeError("invalid_args", f"'{name}' is longer than {limit} characters")
    return value


def _op_analyze(args: dict[str, Any]) -> dict[str, Any]:
    """Every reading of one word. Unknown or invalid words come back as status "error", not as a guess."""
    from .engine import analyze

    _only(args, "word", "lang")
    return analyze(_string(args, "word")).to_dict(_lang(args))


def _op_lexeme(args: dict[str, Any]) -> dict[str, Any]:
    """Paradigm table and classification for one lexeme id (taken from an analyze reading)."""
    from .engine import Tag, classify, default_lexicon, paradigm_table

    _only(args, "id", "lang")
    lang = _lang(args)
    lexicon = default_lexicon()
    lexeme = lexicon.lexemes.get(_string(args, "id"))
    if lexeme is None:
        raise BridgeError("not_found", "no lexeme with this id")
    profile = classify(lexeme)
    return {
        "id": lexeme.id,
        "lemma": lexeme.headword,
        "pos": lexeme.pos,
        # What holds for the whole word (part of speech, gender, aspect …), not the lemma form's case.
        "description": Tag(",".join(lexeme.lemma_tag.lexical)).describe(lang),
        "source": lexeme.source,
        "profile": profile.to_dict() if profile else None,
        "table": _describe_extra(paradigm_table(lexeme, lexicon), lang),
    }


def _describe_extra(table: dict[str, Any], lang: str) -> dict[str, Any]:
    """Forms outside the grid carry only their tag; add its description in the reader's language."""
    from .engine import Tag

    for entry in table.get("extra", []):
        entry["description"] = Tag(entry["tag"]).describe(lang)
    return table


def _op_grammemes(args: dict[str, Any]) -> dict[str, Any]:
    """Names of every grammeme code in one language, for table headers and labels."""
    from .engine.grammemes import CATEGORIES, GRAMMEMES

    _only(args, "lang")
    lang = _lang(args)
    return {"categories": list(CATEGORIES),
            "grammemes": {code: {"name": g.name(lang), "category": g.category} for code, g in GRAMMEMES.items()}}


def _op_rules(args: dict[str, Any]) -> list[dict[str, Any]]:
    from .engine import RULES

    _only(args, "lang", "ids")
    lang = _lang(args)
    ids = args.get("ids")
    if ids is not None and not (isinstance(ids, list) and all(isinstance(i, str) for i in ids)):
        raise BridgeError("invalid_args", "'ids' must be a list of strings")
    wanted = RULES if ids is None else {i: RULES[i] for i in ids if i in RULES}
    return [rule.to_dict(lang) for rule in wanted.values()]


def _op_lexicon_info(args: dict[str, Any]) -> dict[str, Any]:
    from .engine import default_lexicon

    _expect_no_args(args)
    return default_lexicon().info()


def _op_phrase(args: dict[str, Any]) -> dict[str, Any]:
    """A preposition and the word after it: the word's readings narrowed to the cases it governs."""
    from .engine import analyze_after

    _only(args, "preposition", "word", "lang")
    return analyze_after(_string(args, "preposition", limit=20), _string(args, "word")).to_dict(_lang(args))


def _op_inflect(args: dict[str, Any]) -> dict[str, Any]:
    """The forms of a lexeme with the given grammemes (lemma → form, the reverse of analyze).
    An empty list means the dictionary has no such form; nothing is generated by rule."""
    from .engine import default_lexicon
    from .engine.grammemes import GRAMMEMES, RARE_USAGE

    _only(args, "id", "grammemes", "lang")
    lang = _lang(args)
    lexeme = default_lexicon().lexemes.get(_string(args, "id"))
    if lexeme is None:
        raise BridgeError("not_found", "no lexeme with this id")
    grammemes = args.get("grammemes")
    if not (isinstance(grammemes, list) and 0 < len(grammemes) <= 10
            and all(isinstance(g, str) and g in GRAMMEMES for g in grammemes)):
        raise BridgeError("invalid_args", "'grammemes' must be a list of 1–10 known grammeme codes")
    return {
        "id": lexeme.id,
        "lemma": lexeme.headword,
        "forms": [{"form": f.text, "index": f.index, "tag": f.tag.to_dict(), "description": f.tag.describe(lang),
                   "rare": bool(RARE_USAGE & f.tag.grammemes)} for f in lexeme.find(*grammemes)],
    }


def _op_warmup(args: dict[str, Any]) -> dict[str, Any]:
    """Load the lexicon and build its index. The app calls this before taking the memory snapshot,
    so a restored start already has the lexicon in memory."""
    from .engine import analyze, default_lexicon

    _expect_no_args(args)
    lexicon = default_lexicon()
    analyze("слово", lexicon)
    return {"lexemes": len(lexicon.lexemes), "keys": len(lexicon.index)}


def _expect_no_args(args: dict[str, Any]) -> None:
    if args:
        raise BridgeError("invalid_args", f"unexpected arguments: {', '.join(sorted(args))}")


OPS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "version": _op_version,
    "echo": _op_echo,
    "analyze": _op_analyze,
    "lexeme": _op_lexeme,
    "phrase": _op_phrase,
    "inflect": _op_inflect,
    "rules": _op_rules,
    "grammemes": _op_grammemes,
    "lexicon_info": _op_lexicon_info,
    "warmup": _op_warmup,
}


def dispatch(op: str, args: dict[str, Any] | None = None) -> Any:
    """Run one operation and return its result, raising BridgeError for caller errors."""
    handler = OPS.get(op)
    if handler is None:
        raise BridgeError("unknown_op", f"unknown operation: {op!r}")
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise BridgeError("invalid_args", "'args' must be an object")
    return handler(args)


def handle(raw: str) -> str:
    """Handle one JSON request string and return the JSON reply string."""
    request_id: Any = None
    try:
        if not isinstance(raw, str):
            raise BridgeError("invalid_request", "the request must be a JSON string")
        if len(raw.encode("utf-8")) > MAX_REQUEST_BYTES:
            raise BridgeError("invalid_request", "the request is too large")
        try:
            request = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BridgeError("invalid_request", f"the request is not valid JSON: {exc.msg}") from None
        if not isinstance(request, dict):
            raise BridgeError("invalid_request", "the request must be a JSON object")
        request_id = request.get("id")
        if not isinstance(request_id, (str, int)) or isinstance(request_id, bool):
            request_id = None
            raise BridgeError("invalid_request", "'id' must be a string or an integer")
        op = request.get("op")
        if not isinstance(op, str):
            raise BridgeError("invalid_request", "'op' must be a string")
        result = dispatch(op, request.get("args"))
        reply: dict[str, Any] = {"id": request_id, "ok": True, "result": result}
    except BridgeError as exc:
        reply = {"id": request_id, "ok": False, "error": {"code": exc.code, "message": exc.message}}
    except Exception:  # noqa: BLE001 — the boundary must never raise
        traceback.print_exc(file=sys.stderr)
        reply = {"id": request_id, "ok": False,
                 "error": {"code": "internal", "message": "internal error in tilsim_core"}}
    return json.dumps(reply, ensure_ascii=False)
