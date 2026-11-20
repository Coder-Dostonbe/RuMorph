"""Engine tests: normalisation, lexicon integrity, analysis and paradigm tables."""

import json

import pytest

from tilsim_core.engine import AMBIGUOUS, ERROR, OK, Lexicon, analyze, default_lexicon, normalize_word, paradigm_table
from tilsim_core.engine.grammemes import GRAMMEMES
from tilsim_core.engine.normalize import lookup_key


@pytest.fixture(scope="module")
def lexicon():
    return default_lexicon()


# --- normalisation --------------------------------------------------------------------------------

def test_stress_mark_is_recorded_and_removed():
    n = normalize_word("сто́л")
    assert n.word == "стол" and n.stress_index == 2 and n.error is None


def test_case_is_folded_and_yo_kept_but_folded_in_key():
    n = normalize_word("  Ёлка ")
    assert n.word == "ёлка" and n.key == "елка"


def test_latin_lookalikes_are_fixed_with_a_warning():
    n = normalize_word("cтoл")  # Latin c and o
    assert n.word == "стол" and [w.code for w in n.warnings] == ["latin_replaced"]
    assert "Lotin" in n.warnings[0].text("uz") and "раскладку" in n.warnings[0].text("ru")


@pytest.mark.parametrize(
    ("text", "code"),
    [("", "empty"), ("   ", "empty"), ("два слова", "several_words"), ("qalam", "latin_script"),
     ("қалам", "uzbek_letters"), ("ўзбек", "uzbek_letters"), ("stол", "mixed_script"),
     ("сто1", "invalid_characters"), ("а" * 61, "too_long")],
)
def test_invalid_input_is_refused_with_a_code(text, code):
    n = normalize_word(text)
    assert n.error and n.error_code == code


def test_hyphenated_words_and_dashes():
    assert normalize_word("кто‑то").word == "кто-то"


def test_lookup_key_folds_yo():
    assert lookup_key("ЁЖ") == "еж"


# --- lexicon --------------------------------------------------------------------------------------

def test_bundled_lexicon_names_its_source(lexicon):
    info = lexicon.info()
    source = info["packages"][0]["source"]
    assert source["name"] == "OpenCorpora" and source["license"] == "CC BY-SA 3.0"
    assert info["lexemes"] > 300 and info["forms"] > 9000


def test_every_lexeme_is_well_formed(lexicon):
    for lexeme in lexicon.lexemes.values():
        assert lexeme.forms, lexeme.id
        assert all(f.text and f.text == f.text.lower() for f in lexeme.forms), lexeme.id
        assert lexeme.pos in GRAMMEMES, (lexeme.id, lexeme.pos)


def test_every_grammeme_in_the_data_has_a_name(lexicon):
    codes = {g for lx in lexicon.lexemes.values() for f in lx.forms for g in f.tag.grammemes}
    assert codes - set(GRAMMEMES) == set()


def test_invalid_package_is_refused():
    from tilsim_core.engine.lexicon import LexiconError

    with pytest.raises(LexiconError):
        Lexicon.from_package({"package": "x", "tags": [], "paradigms": [[[0, "", 5]]], "lexemes": [["a", 0]]})


def test_packages_merge_without_id_clashes(lexicon):
    data = {"package": "user", "tags": ["NOUN,inan,masc sing,nomn"], "paradigms": [[["", "", 0]]],
            "lexemes": [["тест", 0]]}
    merged = Lexicon.from_package(json.loads(json.dumps(data)))
    assert merged.lookup("тест")[0][0].id == "user:0"


# --- analysis -------------------------------------------------------------------------------------

def test_single_reading_is_ok(lexicon):
    a = analyze("столом", lexicon)
    assert a.status == OK and a.lemmas == ["стол"]
    r = a.readings[0]
    assert r.form.tag.case == "ablt" and r.form.tag.number == "sing"
    assert r.to_dict()["description"] == "ot · jonsiz · erkak jinsi · birlik · vosita kelishigi"


def test_syncretic_forms_are_ambiguous_and_all_listed(lexicon):
    a = analyze("книги", lexicon)
    assert a.status == AMBIGUOUS and a.lemmas == ["книга"]
    cases = {(r.form.tag.number, r.form.tag.case) for r in a.readings}
    assert cases == {("sing", "gent"), ("plur", "nomn"), ("plur", "accs")}


def test_homonyms_from_different_lexemes(lexicon):
    a = analyze("есть", lexicon)
    assert a.status == AMBIGUOUS
    assert {r.form.tag.pos for r in a.readings} >= {"INFN"}


def test_unknown_word_is_an_error_with_suggestions_not_a_guess(lexicon):
    a = analyze("книгу", lexicon)
    assert a.status == OK
    typo = analyze("кнгиа", lexicon)
    assert typo.status == ERROR and typo.readings == []
    assert typo.errors[0].code == "unknown_word"
    assert "книга" in typo.suggestions


def test_missing_yo_is_reported(lexicon):
    a = analyze("ребенок", lexicon)
    assert a.lemmas == ["ребёнок"]
    assert any(n.code == "spelled_with_yo" for r in a.readings for n in r.notes)
    assert "с ё" in a.to_dict("ru")["readings"][0]["notes"][0]


def test_written_yo_narrows_the_readings(lexicon):
    # "всё" (everything) and "все" (all) differ only by ё.
    with_yo = analyze("всё", lexicon)
    without = analyze("все", lexicon)
    assert all(r.form.text == "всё" for r in with_yo.readings)
    assert len(without.readings) > len(with_yo.readings)


def test_rare_forms_are_flagged_and_listed_last(lexicon):
    a = analyze("деньги", lexicon)
    assert a.lemmas == ["деньги"]
    assert a.readings[-1].to_dict()["rules"][-1] == "lexicon.rare_form"
    assert not any("Infr" in r.form.tag for r in a.readings[:2])


def test_stress_and_warnings_reach_the_result(lexicon):
    a = analyze("cто́л", lexicon)
    assert a.stress_index == 2 and a.warnings and a.lemmas == ["стол"]


@pytest.mark.parametrize("lang", ["uz", "ru", "en"])
def test_result_is_json_serialisable_in_every_language(lexicon, lang):
    for word in ("книги", "деньги", "ребенок", "cтол", "кнгиа", "qalam"):
        json.dumps(analyze(word, lexicon).to_dict(lang))


def test_every_message_has_three_languages():
    from tilsim_core.engine.messages import TEXTS

    for code, texts in TEXTS.items():
        assert set(texts) == {"uz", "ru", "en"} and all(texts.values()), code


# --- paradigm tables ------------------------------------------------------------------------------

def cell(table, row_key, column):
    row = next(r for r in table["rows"] if r["key"] == row_key)
    return [c["form"] for c in row["cells"][table["columns"].index(column)]]


def _only(lexicon, lemma, pos):
    (lexeme,) = [lx for lx in lexicon.by_lemma(lemma) if lx.pos == pos]
    return lexeme


def test_noun_table(lexicon):
    (lexeme,) = [lx for lx in lexicon.by_lemma("книга")]
    t = paradigm_table(lexeme)
    assert t["kind"] == "noun" and t["columns"] == ["sing", "plur"]
    assert cell(t, "gent", "sing") == ["книги"] and cell(t, "gent", "plur") == ["книг"]
    assert cell(t, "ablt", "sing")[0] == "книгой"


def test_noun_table_keeps_second_locative(lexicon):
    (lexeme,) = [lx for lx in lexicon.by_lemma("лес")]
    t = paradigm_table(lexeme)
    assert cell(t, "loc2", "sing") == ["лесу"] and cell(t, "loct", "sing") == ["лесе"]


def test_plural_only_noun_has_no_singular_column(lexicon):
    (lexeme,) = [lx for lx in lexicon.by_lemma("ножницы")]
    assert paradigm_table(lexeme)["columns"] == ["plur"]


def test_adjective_table_splits_animate_accusative(lexicon):
    (lexeme,) = [lx for lx in lexicon.by_lemma("новый")]
    t = paradigm_table(lexeme)
    assert t["kind"] == "adjective"
    assert cell(t, "accs.anim", "masc") == ["нового"] and cell(t, "accs.inan", "masc") == ["новый"]
    assert cell(t, "gent", "femn") == ["новой"]
    assert t["short"] and [c["form"] for c in t["short"][2]] == ["нова"]


def test_pronoun_table_has_a_column_for_forms_after_prepositions(lexicon):
    t = paradigm_table(_only(lexicon, "он", "NPRO"))
    assert t["kind"] == "pronoun" and t["columns"] == ["form", "after_prep"]
    rows = {r["key"]: [[c["form"] for c in cell] for cell in r["cells"]] for r in t["rows"]}
    assert rows["gent"] == [["его"], ["него"]]
    assert rows["loct"] == [[], ["нём"]]          # the prepositional case exists only after a preposition


def test_reflexive_pronoun_has_an_empty_nominative(lexicon):
    t = paradigm_table(_only(lexicon, "себя", "NPRO"))
    rows = {r["key"]: r["cells"] for r in t["rows"]}
    assert t["columns"] == ["form"] and rows["nomn"] == [[]]
    ablt = rows["ablt"][0]
    assert [c["form"] for c in ablt] == ["собой", "собою"] and [c["variant"] for c in ablt] == [False, True]


def test_short_only_adjective_has_no_full_form_rows(lexicon):
    t = paradigm_table(_only(lexicon, "рад", "ADJS"))
    assert t["kind"] == "adjective" and t["rows"] == []
    assert [[c["form"] for c in cell] for cell in t["short"]] == [["рад"], ["радо"], ["рада"], ["рады"]]


def test_distorted_forms_are_rare(lexicon):
    # OpenCorpora "Dist" marks distorted spellings (ети for эти); they must not look like normal forms.
    result = analyze("ети", lexicon)
    assert result.readings and all("lexicon.rare_form" in r.to_dict()["rules"] for r in result.readings)


def _forms(cells):
    return [c["form"] for c in cells]


def test_imperfective_verb_table(lexicon):
    t = paradigm_table(_only(lexicon, "писать", "INFN"), lexicon)
    assert t["kind"] == "verb" and t["aspect"] == "impf" and t["transitivity"] == "tran"
    (present,) = t["nonpast"]
    assert present["tense"] == "pres"
    rows = {r["key"]: [_forms(c) for c in r["cells"]] for r in present["rows"]}
    assert rows == {"1per": [["пишу"], ["пишем"]], "2per": [["пишешь"], ["пишете"]], "3per": [["пишет"], ["пишут"]]}
    future = {r["key"]: [_forms(c) for c in r["cells"]] for r in t["future_compound"]}
    assert future["1per"] == [["буду писать"], ["будем писать"]]
    assert all(c["constructed"] and c["rule"] == "verb.future_compound" and "index" not in c
               for r in t["future_compound"] for cell in r["cells"] for c in cell)
    assert [_forms(c) for c in t["past"]["cells"]] == [["писал"], ["писала"], ["писало"], ["писали"]]
    assert [_forms(c) for c in t["imperative"][0]["cells"]] == [["пиши"], ["пишите"]]
    participles = {p["key"]: _forms(p["lemma"]) for p in t["participles"]}
    assert participles["pres.actv"] == ["пишущий"] and participles["past.pssv"] == ["писанный"]


def test_perfective_verb_has_a_simple_future_and_no_compound_one(lexicon):
    t = paradigm_table(_only(lexicon, "сделать", "INFN"), lexicon)
    assert t["aspect"] == "perf" and [n["tense"] for n in t["nonpast"]] == ["futr"]
    assert t["future_compound"] is None
    assert {r["key"] for r in t["imperative"]} == {"excl", "incl"}


def test_byt_has_present_and_future_and_no_compound_future(lexicon):
    t = paradigm_table(_only(lexicon, "быть", "INFN"), lexicon)
    assert [n["tense"] for n in t["nonpast"]] == ["pres", "futr"] and t["future_compound"] is None


def test_two_aspect_verb_keeps_every_form(lexicon):
    t = paradigm_table(_only(lexicon, "бежать", "INFN"), lexicon)
    assert t["aspect"] == "both" and [n["tense"] for n in t["nonpast"]] == ["pres", "futr"]
    assert t["infinitive"][0]["form"] == "бежать" and t["infinitive"][0]["also"]


def test_compound_future_needs_the_lexicon(lexicon):
    # Without a lexicon to take быть from, the compound future is left out rather than made up.
    assert paradigm_table(_only(lexicon, "писать", "INFN"))["future_compound"] is None


def _indices(node):
    """Every form index anywhere in a table (cells are dicts with "index")."""
    if isinstance(node, dict):
        found = ({node["index"], *node.get("also", ())} if "index" in node else set())
        return found.union(*(_indices(v) for v in node.values()))
    if isinstance(node, list):
        return set().union(*(_indices(v) for v in node))
    return set()


def test_every_form_appears_in_some_table(lexicon):
    for lexeme in lexicon.lexemes.values():
        t = paradigm_table(lexeme, lexicon)
        assert _indices(t) == {f.index for f in lexeme.forms}, lexeme.lemma


def test_no_form_appears_twice_in_a_table(lexicon):
    def cells(node):
        if isinstance(node, dict):
            yield from ([node["index"], *node.get("also", ())] if "index" in node else [])
            for v in node.values():
                yield from cells(v)
        elif isinstance(node, list):
            for v in node:
                yield from cells(v)
    for lexeme in lexicon.lexemes.values():
        t = paradigm_table(lexeme, lexicon)
        seen = list(cells({k: v for k, v in t.items() if k != "extra"}))
        assert not set(seen) & {e["index"] for e in t["extra"]}, lexeme.lemma
