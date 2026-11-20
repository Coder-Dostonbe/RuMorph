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
