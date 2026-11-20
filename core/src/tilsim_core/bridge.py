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
    from .engine.search import ranks

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
        "frequency": lexeme.freq,
        "rank": ranks(lexicon).get(lexeme.id),
        "profile": profile.to_dict() if profile else None,
        "table": _describe_extra(paradigm_table(lexeme, lexicon), lang),
    }


def _describe_extra(table: dict[str, Any], lang: str) -> dict[str, Any]:
    """Forms outside the grid carry only their tag; add its description in the reader's language."""
    from .engine import Tag

    for entry in table.get("extra", []):
        entry["description"] = Tag(entry["tag"]).describe(lang)
    return table


def _summary(lexeme: Any, lang: str, rank: int | None) -> dict[str, Any]:
    from .engine import Tag

    return {
        "id": lexeme.id,
        "lemma": lexeme.headword,
        "pos": lexeme.pos,
        "description": Tag(",".join(lexeme.lemma_tag.lexical)).describe(lang),
        "frequency": lexeme.freq,
        "rank": rank,
    }


def _op_search(args: dict[str, Any]) -> dict[str, Any]:
    """Dictionary search: a form, the beginning of a word, or nothing (browse by frequency)."""
    from .engine.search import POS_FILTERS, search

    _only(args, "query", "pos", "limit", "offset", "lang")
    lang = _lang(args)
    query = args.get("query", "")
    if not isinstance(query, str) or len(query) > 60:
        raise BridgeError("invalid_args", "'query' must be a string of at most 60 characters")
    pos = args.get("pos")
    if pos is not None and pos not in POS_FILTERS:
        raise BridgeError("invalid_args", f"'pos' must be one of {', '.join(POS_FILTERS)}")
    limit, offset = args.get("limit", 30), args.get("offset", 0)
    if not (isinstance(limit, int) and 1 <= limit <= 200 and isinstance(offset, int) and offset >= 0):
        raise BridgeError("invalid_args", "'limit' must be 1–200 and 'offset' at least 0")
    total, hits = search(query, pos=pos, limit=limit, offset=offset)
    return {"total": total, "items": [{**_summary(h.lexeme, lang, h.rank), "match": h.match} for h in hits]}


def _op_words(args: dict[str, Any]) -> dict[str, Any]:
    """Summaries and principal parts of several lexemes (for flashcards). Unknown ids are left out,
    so the app can tell that a saved word is no longer in the lexicon."""
    from .engine import default_lexicon
    from .engine.search import ranks
    from .engine.tables import key_forms

    _only(args, "ids", "lang")
    lang = _lang(args)
    ids = args.get("ids")
    if not (isinstance(ids, list) and len(ids) <= 2000 and all(isinstance(i, str) for i in ids)):
        raise BridgeError("invalid_args", "'ids' must be a list of at most 2000 strings")
    lexicon = default_lexicon()
    rank = ranks(lexicon)
    out = {}
    for lexeme_id in ids:
        lexeme = lexicon.lexemes.get(lexeme_id)
        if lexeme is not None:
            out[lexeme_id] = {**_summary(lexeme, lang, rank.get(lexeme_id)), "key_forms": key_forms(lexeme)}
    return out


def _card(value: Any) -> Any:
    from .srs import CardState

    if not isinstance(value, dict):
        raise BridgeError("invalid_args", "'card' must be an object")
    try:
        return CardState.from_dict(value)
    except (KeyError, TypeError, ValueError) as exc:
        raise BridgeError("invalid_args", f"bad card: {exc}") from None


def _now(args: dict[str, Any]) -> str:
    from .srs import parse_time

    now = args.get("now")
    try:
        parse_time(now)  # type: ignore[arg-type]
    except (TypeError, ValueError, AttributeError):
        raise BridgeError("invalid_args", "'now' must be an ISO 8601 time with a time zone") from None
    return now  # type: ignore[return-value]


def _op_srs_review(args: dict[str, Any]) -> dict[str, Any]:
    """The card after an answer graded 0–3, and when each grade would bring it back next time."""
    from .srs import GRADES, review

    _only(args, "card", "grade", "now")
    grade = args.get("grade")
    if grade not in GRADES or isinstance(grade, bool):
        raise BridgeError("invalid_args", "'grade' must be 0, 1, 2 or 3")
    card = review(_card(args.get("card")), grade, _now(args))
    return {"card": card.to_dict()}


def _op_srs_preview(args: dict[str, Any]) -> dict[str, Any]:
    from .srs import preview

    _only(args, "card", "now")
    return {"days": {str(g): d for g, d in preview(_card(args.get("card")), _now(args)).items()}}


def _op_srs_queue(args: dict[str, Any]) -> dict[str, Any]:
    from .srs import queue

    _only(args, "cards", "now", "new_limit", "new_seen_today")
    cards = args.get("cards")
    if not (isinstance(cards, list) and len(cards) <= 20000 and all(isinstance(c, dict) and isinstance(c.get("id"), str)
                                                                    for c in cards)):
        raise BridgeError("invalid_args", "'cards' must be a list of card objects with an 'id'")
    new_limit, seen = args.get("new_limit", 20), args.get("new_seen_today", 0)
    if not (isinstance(new_limit, int) and 0 <= new_limit <= 1000 and isinstance(seen, int) and seen >= 0):
        raise BridgeError("invalid_args", "'new_limit' must be 0–1000 and 'new_seen_today' at least 0")
    return {"ids": queue([(c["id"], _card(c)) for c in cards], _now(args), new_limit=new_limit, new_seen_today=seen)}


def _op_grammar(args: dict[str, Any]) -> dict[str, Any]:
    """The grammar catalog: rules in groups, each with how many dictionary words it explains."""
    from .engine import RULES
    from .engine.catalog import GROUPS, group_of, rule_index

    _only(args, "lang")
    lang = _lang(args)
    index = rule_index()
    groups: dict[str, list[dict[str, Any]]] = {g: [] for g in GROUPS}
    for rule in RULES.values():
        group = group_of(rule.id)
        if group is not None:
            groups[group].append({**rule.to_dict(lang), "words": len(index.get(rule.id, ()))})
    return {"groups": [{"id": g, "rules": rules} for g, rules in groups.items()]}


def _op_rule_examples(args: dict[str, Any]) -> dict[str, Any]:
    """Dictionary words a rule explains, most frequent first, each with its own example."""
    from .engine import RULES, default_lexicon
    from .engine.catalog import rule_index
    from .engine.search import ranks

    _only(args, "rule", "limit", "offset", "lang")
    lang = _lang(args)
    rule = _string(args, "rule", limit=80)
    if rule not in RULES:
        raise BridgeError("not_found", "no rule with this id")
    limit, offset = args.get("limit", 20), args.get("offset", 0)
    if not (isinstance(limit, int) and 1 <= limit <= 200 and isinstance(offset, int) and offset >= 0):
        raise BridgeError("invalid_args", "'limit' must be 1–200 and 'offset' at least 0")
    entries = rule_index().get(rule, [])
    rank = ranks(default_lexicon())
    return {"total": len(entries),
            "items": [{**_summary(lx, lang, rank.get(lx.id)), "detail": detail}
                      for lx, detail in entries[offset:offset + limit]]}


def _op_prepositions(args: dict[str, Any]) -> list[dict[str, Any]]:
    """Every preposition with the cases it takes and their meanings."""
    from .engine.prepositions import PREPOSITIONS

    _only(args, "lang")
    lang = _lang(args)
    return [{"preposition": p, "governs": [g.to_dict(lang) for g in governs]}
            for p, governs in sorted(PREPOSITIONS.items())]


def _op_exercises(args: dict[str, Any]) -> list[dict[str, Any]]:
    """Multiple-choice questions of one kind, made from the dictionary (tilsim_core/exercises.py)."""
    from .exercises import KINDS, generate

    _only(args, "kind", "count", "seed", "max_rank", "vocabulary")
    kind = args.get("kind")
    if kind not in KINDS:
        raise BridgeError("invalid_args", f"'kind' must be one of {', '.join(KINDS)}")
    count, seed, max_rank = args.get("count", 10), args.get("seed", 0), args.get("max_rank", 1000)
    if not (isinstance(count, int) and 1 <= count <= 100 and isinstance(seed, int)
            and isinstance(max_rank, int) and 10 <= max_rank <= 100000):
        raise BridgeError("invalid_args", "'count' must be 1–100, 'seed' an integer, 'max_rank' 10–100000")
    vocabulary = args.get("vocabulary", [])
    if not (isinstance(vocabulary, list) and len(vocabulary) <= 5000 and all(
            isinstance(v, dict) and all(isinstance(v.get(k), str) for k in ("lexeme_id", "lemma", "translation"))
            for v in vocabulary)):
        raise BridgeError("invalid_args", "'vocabulary' must be a list of {lexeme_id, lemma, translation}")
    return [q.to_dict() for q in generate(kind, count, seed, max_rank=max_rank, vocabulary=vocabulary)]


def _op_spellcheck(args: dict[str, Any]) -> dict[str, Any]:
    """Spell and grammar check of a text (tilsim_core/spell.py)."""
    from .spell import MAX_TEXT, check

    _only(args, "text", "lang")
    return check(_string(args, "text", limit=MAX_TEXT)).to_dict(_lang(args))


def _op_reading(args: dict[str, Any]) -> dict[str, Any]:
    """A text's words linked to the dictionary, and its measured difficulty (tilsim_core/reading.py)."""
    from .reading import MAX_TEXT, prepare

    _only(args, "text")
    return prepare(_string(args, "text", limit=MAX_TEXT))


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
    "search": _op_search,
    "reading": _op_reading,
    "spellcheck": _op_spellcheck,
    "exercises": _op_exercises,
    "grammar": _op_grammar,
    "rule_examples": _op_rule_examples,
    "prepositions": _op_prepositions,
    "words": _op_words,
    "srs_review": _op_srs_review,
    "srs_preview": _op_srs_preview,
    "srs_queue": _op_srs_queue,
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
