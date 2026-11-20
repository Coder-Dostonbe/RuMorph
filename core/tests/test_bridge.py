import json

import pytest

from tilsim_core import PROTOCOL_VERSION, __version__, bridge


def call(payload) -> dict:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return json.loads(bridge.handle(raw))


def test_version_reports_core_and_protocol():
    reply = call({"id": 1, "op": "version"})
    assert reply["ok"] is True and reply["id"] == 1
    assert reply["result"]["core"] == __version__
    assert reply["result"]["protocol"] == PROTOCOL_VERSION
    assert reply["result"]["python"].count(".") == 2


def test_echo_round_trips_cyrillic_and_uzbek():
    text = "Привет, o'zbekcha ғ қ ў ҳ"
    reply = call({"id": "a", "op": "echo", "args": {"text": text}})
    assert reply == {"id": "a", "ok": True, "result": {"text": text}}


def test_reply_keeps_non_ascii_unescaped():
    assert "Привет" in bridge.handle(json.dumps({"id": 1, "op": "echo", "args": {"text": "Привет"}}))


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ("not json", "invalid_request"),
        ("[1, 2]", "invalid_request"),
        ({"op": "version"}, "invalid_request"),
        ({"id": True, "op": "version"}, "invalid_request"),
        ({"id": 1.5, "op": "version"}, "invalid_request"),
        ({"id": 1}, "invalid_request"),
        ({"id": 1, "op": "nope"}, "unknown_op"),
        ({"id": 1, "op": "version", "args": []}, "invalid_args"),
        ({"id": 1, "op": "version", "args": {"x": 1}}, "invalid_args"),
        ({"id": 1, "op": "echo", "args": {"text": 5}}, "invalid_args"),
        ({"id": 1, "op": "echo", "args": {"text": "x" * 1001}}, "invalid_args"),
    ],
)
def test_bad_requests_get_a_code_not_an_exception(payload, code):
    reply = call(payload)
    assert reply["ok"] is False
    assert reply["error"]["code"] == code
    assert reply["error"]["message"]


def test_id_is_echoed_on_errors_when_valid():
    assert call({"id": 7, "op": "nope"})["id"] == 7


def test_oversized_request_is_refused():
    raw = json.dumps({"id": 1, "op": "echo", "args": {"text": "x" * (bridge.MAX_REQUEST_BYTES + 1)}})
    assert call(raw)["error"]["code"] == "invalid_request"


def test_internal_errors_are_generic(monkeypatch, capsys):
    def boom(args):
        raise RuntimeError("secret detail")

    monkeypatch.setitem(bridge.OPS, "boom", boom)
    reply = call({"id": 3, "op": "boom"})
    assert reply == {"id": 3, "ok": False,
                     "error": {"code": "internal", "message": "internal error in tilsim_core"}}
    assert "secret detail" in capsys.readouterr().err


def test_non_string_request_is_refused():
    assert json.loads(bridge.handle(b"{}"))["error"]["code"] == "invalid_request"  # type: ignore[arg-type]


# --- grammar ops ----------------------------------------------------------------------------------

def ok(op, **args):
    reply = call({"id": 1, "op": op, "args": args})
    assert reply["ok"] is True, reply
    return reply["result"]


def test_analyze_op():
    result = ok("analyze", word="книги")
    assert result["status"] == "ambiguous" and result["lemmas"] == ["книга"]
    assert len(result["readings"]) == 3


def test_analyze_op_unknown_word_is_an_error_status_not_a_bridge_error():
    result = ok("analyze", word="кнгиа")
    assert result["status"] == "error" and result["errors"][0]["code"] == "unknown_word"


def test_analyze_op_in_russian():
    result = ok("analyze", word="столом", lang="ru")
    assert "творительный" in result["readings"][0]["description"]


def test_lexeme_op_returns_table_and_profile():
    reading = ok("analyze", word="день")["readings"][0]
    result = ok("lexeme", id=reading["lexeme"])
    assert result["lemma"] == "день" and result["table"]["kind"] == "noun"
    assert result["profile"]["kind"] == "noun" and result["profile"]["category"] == "noun.decl.2"
    assert result["description"] == "ot · jonsiz · erkak jinsi"      # the word's, not the lemma form's case
    assert {f["rule"] for f in result["profile"]["findings"]} == {"noun.fleeting_vowel", "noun.loc2"}


def test_lexeme_op_for_a_pronoun_and_an_adjective():
    pronoun = ok("lexeme", id=ok("analyze", word="него")["readings"][0]["lexeme"])
    assert pronoun["lemma"] == "он" and pronoun["table"]["kind"] == "pronoun"
    assert pronoun["profile"]["category"] == "pron.personal"
    readings = ok("analyze", word="лучше")["readings"]
    adjective = ok("lexeme", id=next(r["lexeme"] for r in readings if r["pos"] == "COMP"))
    assert adjective["lemma"] == "хороший" and adjective["profile"]["kind"] == "adjective"
    assert "adj.comparative_suppletive" in {f["rule"] for f in adjective["profile"]["findings"]}


def test_lexeme_ids_are_stable_names():
    reading = ok("analyze", word="книгой")["readings"][0]
    assert reading["lexeme"] == "книга|NOUN,inan,femn"
    assert reading["frequency"] > 4.5                       # wordfreq Zipf


def test_lexeme_op_for_a_verb():
    reading = next(r for r in ok("analyze", word="пишу")["readings"])
    result = ok("lexeme", id=reading["lexeme"], lang="en")
    assert result["lemma"] == "писать" and result["pos"] == "INFN" and result["table"]["kind"] == "verb"
    assert result["profile"]["category"] == "verb.conj.1"
    assert result["table"]["future_compound"][0]["cells"][0][0]["form"] == "буду писать"


def test_lexeme_op_without_a_profile():
    reading = ok("analyze", word="очень")["readings"][0]
    assert ok("lexeme", id=reading["lexeme"])["profile"] is None


def test_phrase_op():
    result = ok("phrase", preposition="без", word="книги", lang="en")
    assert result["status"] == "ok" and result["readings"][0]["government"]["case"] == "gent"
    assert [g["case"] for g in result["governs"]] == ["gent"]
    wrong = ok("phrase", preposition="в", word="школа")
    assert wrong["status"] == "error" and wrong["suggestions"] == ["в школу", "в школе"]


def test_inflect_op():
    lexeme = ok("analyze", word="книга")["readings"][0]["lexeme"]
    result = ok("inflect", id=lexeme, grammemes=["plur", "gent"])
    assert [f["form"] for f in result["forms"]] == ["книг"]
    assert ok("inflect", id=lexeme, grammemes=["past"])["forms"] == []     # a noun has no past tense


def test_grammemes_op():
    result = ok("grammemes", lang="ru")
    assert result["grammemes"]["gent"] == {"name": "родительный падеж", "category": "case"}
    assert "case" in result["categories"]


def test_extra_forms_are_described_in_the_language_asked():
    reading = ok("analyze", word="хороший")["readings"][0]
    extra = ok("lexeme", id=reading["lexeme"], lang="en")["table"]["extra"]
    assert extra and all(e["description"] for e in extra)


def test_rules_op():
    rules = ok("rules", lang="en", ids=["noun.decl.1", "nope"])
    assert [r["id"] for r in rules] == ["noun.decl.1"] and rules[0]["name"] == "1st declension"
    assert len(ok("rules")) > 15


def test_lexicon_info_and_warmup():
    assert ok("lexicon_info")["packages"][0]["source"]["name"] == "OpenCorpora"
    assert ok("warmup")["lexemes"] > 300


@pytest.mark.parametrize(
    ("op", "args", "code"),
    [("analyze", {}, "invalid_args"), ("analyze", {"word": 1}, "invalid_args"),
     ("analyze", {"word": "x" * 201}, "invalid_args"), ("analyze", {"word": "да", "lang": "de"}, "invalid_args"),
     ("analyze", {"word": "да", "extra": 1}, "invalid_args"), ("lexeme", {"id": "nope"}, "not_found"),
     ("rules", {"ids": "x"}, "invalid_args"), ("warmup", {"x": 1}, "invalid_args"),
     ("phrase", {"word": "книги"}, "invalid_args"), ("phrase", {"preposition": "в" * 21, "word": "a"}, "invalid_args"),
     ("inflect", {"id": "nope", "grammemes": ["gent"]}, "not_found"),
     ("inflect", {"id": "книга|NOUN,inan,femn", "grammemes": ["nope"]}, "invalid_args"),
     ("inflect", {"id": "книга|NOUN,inan,femn", "grammemes": []}, "invalid_args")],
)
def test_grammar_ops_validate_their_arguments(op, args, code):
    reply = call({"id": 1, "op": op, "args": args})
    assert reply["ok"] is False and reply["error"]["code"] == code
