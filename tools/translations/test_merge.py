import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import merge  # noqa: E402

KNOWN = {"книга|NOUN,inan,femn", "дом|NOUN,inan,masc", "идти|INFN,impf,intr"}


def entry(lexeme_id: str, text: str, at: str) -> dict:
    return {"lexeme_id": lexeme_id, "lemma": lexeme_id.split("|")[0], "translation": text, "updated_at": at}


def test_newest_entry_wins():
    shipped = {"книга|NOUN,inan,femn": entry("книга|NOUN,inan,femn", "kitob", "2026-01-01T00:00:00Z")}
    export = {"книга|NOUN,inan,femn": entry("книга|NOUN,inan,femn", "kitob, daftar", "2026-02-01T00:00:00Z"),
              "дом|NOUN,inan,masc": entry("дом|NOUN,inan,masc", "uy", "2026-02-01T00:00:00Z")}
    result = merge.merge(shipped, [(export, {})])
    assert result["книга|NOUN,inan,femn"]["translation"] == "kitob, daftar"
    assert result["дом|NOUN,inan,masc"]["translation"] == "uy"


def test_older_export_does_not_overwrite():
    shipped = {"книга|NOUN,inan,femn": entry("книга|NOUN,inan,femn", "kitob", "2026-03-01T00:00:00Z")}
    export = {"книга|NOUN,inan,femn": entry("книга|NOUN,inan,femn", "eski", "2026-01-01T00:00:00Z")}
    assert merge.merge(shipped, [(export, {})])["книга|NOUN,inan,femn"]["translation"] == "kitob"


def test_only_newer_removals_drop_a_word():
    shipped = {"книга|NOUN,inan,femn": entry("книга|NOUN,inan,femn", "kitob", "2026-01-01T00:00:00Z"),
               "дом|NOUN,inan,masc": entry("дом|NOUN,inan,masc", "uy", "2026-05-01T00:00:00Z"),
               "идти|INFN,impf,intr": entry("идти|INFN,impf,intr", "bormoq", "2026-01-01T00:00:00Z")}
    removed = {"книга|NOUN,inan,femn": "2026-02-01T00:00:00Z", "дом|NOUN,inan,masc": "2026-02-01T00:00:00Z"}
    result = merge.merge(shipped, [({}, removed)])
    assert "книга|NOUN,inan,femn" not in result   # removed after it was entered
    assert "дом|NOUN,inan,masc" in result          # entered again after the removal
    assert "идти|INFN,impf,intr" in result         # merely missing from the export


def test_validation():
    good = [entry("книга|NOUN,inan,femn", " kitob ", "2026-01-01T00:00:00Z")]
    assert merge.validate(good, KNOWN, "x")["книга|NOUN,inan,femn"]["translation"] == "kitob"
    for bad in ([entry("нет|NOUN", "yo'q", "t")], [entry("дом|NOUN,inan,masc", "  ", "t")],
                [entry("дом|NOUN,inan,masc", "x" * 201, "t")], [{"lexeme_id": "дом|NOUN,inan,masc"}],
                [entry("дом|NOUN,inan,masc", "uy", "t")] * 2):
        with pytest.raises(merge.MergeError):
            merge.validate(bad, KNOWN, "x")


def test_render_is_sorted_and_round_trips(tmp_path):
    entries = {k: entry(k, "t", "2026-01-01T00:00:00Z") for k in sorted(KNOWN, reverse=True)}
    path = tmp_path / "t.json"
    path.write_text(merge.render(entries), encoding="utf-8")
    data = merge.read(path)
    assert [e["lexeme_id"] for e in data["translations"]] == sorted(KNOWN)


def test_shipped_file_is_valid():
    data = merge.read(merge.SHIPPED)
    merge.validate(data["translations"], merge.lexeme_ids(), "shipped")
    assert json.loads(merge.SHIPPED.read_text(encoding="utf-8"))["format"] == "tilsim-translations"


def test_examples_and_drafts_are_kept():
    draft = {**entry("книга|NOUN,inan,femn", "kitob", "2026-01-01T00:00:00Z"),
             "examples": [{"ru": "Это книга.", "uz": "Bu kitob."}], "verified": False}
    out = merge.validate([draft], KNOWN, "x")
    assert out["книга|NOUN,inan,femn"]["verified"] is False
    assert out["книга|NOUN,inan,femn"]["examples"] == [{"ru": "Это книга.", "uz": "Bu kitob."}]
    # A checked entry carries no "verified" key at all.
    assert "verified" not in merge.validate([entry("дом|NOUN,inan,masc", "uy", "t")], KNOWN, "x")["дом|NOUN,inan,masc"]


@pytest.mark.parametrize("examples", [[{"ru": "a"}], [{"ru": "a", "uz": " "}], [{"ru": "a", "uz": "b"}] * 4, "x"])
def test_bad_examples_are_refused(examples):
    with pytest.raises(merge.MergeError):
        merge.validate([{**entry("дом|NOUN,inan,masc", "uy", "t"), "examples": examples}], KNOWN, "x")


def test_drafts_never_replace_a_checked_translation(tmp_path):
    import drafts

    f = tmp_path / "d.tsv"
    f.write_text("# comment\nкнига|NOUN,inan,femn\tkitob\tЭто книга.\tBu kitob.\tГде книга?\tKitob qayerda?\n"
                 "дом|NOUN,inan,masc\tuy\n", encoding="utf-8")
    parsed = drafts.parse(f)
    assert parsed[0]["examples"][1] == {"ru": "Где книга?", "uz": "Kitob qayerda?"}
    assert parsed[0]["verified"] is False and parsed[0]["updated_at"] == drafts.DRAFT_AT
    checked = {"дом|NOUN,inan,masc": entry("дом|NOUN,inan,masc", "uy, bino", "2026-11-24T00:00:00Z")}
    result, added = drafts.add_drafts(checked, merge.validate(parsed, KNOWN, "d"))
    assert added == 1
    assert result["дом|NOUN,inan,masc"]["translation"] == "uy, bino"
    assert result["книга|NOUN,inan,femn"]["verified"] is False


def test_draft_lines_need_pairs(tmp_path):
    import drafts

    f = tmp_path / "d.tsv"
    f.write_text("книга|NOUN,inan,femn\tkitob\tЭто книга.\n", encoding="utf-8")
    with pytest.raises(merge.MergeError):
        drafts.parse(f)
