"""Decides which rules explain a lexeme: its class (declension, stem type, kind
of pronoun) and its exceptions.

The lexicon already holds the correct forms. Here they are compared with each
other (nominative with genitive, singular with plural, full with short form, …)
to find what a learner needs to be told: a fleeting vowel, a plural on another
stem, a spelling rule. Each finding names a rule from rules.py and gives the
concrete example from this word. A check that cannot decide says nothing
rather than guess; a lexeme the engine has no classification for gets
category None.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .grammemes import NOT_MAIN
from .lexicon import Lexeme

VOWELS = "аеёиоуыэюя"
HUSHING_GKH = "гкхжшщч"
SIBILANTS_C = "жшщчц"
FLEETING = "оеё"


@dataclass(frozen=True)
class Finding:
    rule_id: str
    detail: str            # this word's own example, e.g. "день → дня"

    def to_dict(self) -> dict:
        return {"rule": self.rule_id, "detail": self.detail}


@dataclass
class Profile:
    kind: str                              # "noun" | "adjective" | "pronoun" | "verb"
    category: str | None                   # rule id of the class, None if the engine cannot tell
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"kind": self.kind, "category": self.category, "findings": [f.to_dict() for f in self.findings]}


def _main(lexeme: Lexeme, *grammemes: str, exclude: tuple[str, ...] = ()) -> list[str]:
    """Texts of the main forms with these grammemes (no rare or variant forms), without repeats."""
    forms = lexeme.find(*grammemes, exclude=tuple(NOT_MAIN) + exclude)
    return list(dict.fromkeys(f.text for f in forms))


def _text(lexeme: Lexeme, *grammemes: str, exclude: tuple[str, ...] = ()) -> str | None:
    """The first main form with these grammemes."""
    texts = _main(lexeme, *grammemes, exclude=exclude)
    return texts[0] if texts else None


def _fold(text: str) -> str:
    return text.replace("ё", "е")


def _drop_one(longer: str, shorter: str, letters: str) -> bool:
    """True if removing one of `letters` from `longer` gives `shorter`."""
    if len(longer) != len(shorter) + 1:
        return False
    return any(longer[i] in letters and longer[:i] + longer[i + 1:] == shorter for i in range(len(longer)))


def _declension(lexeme: Lexeme, lemma: str) -> str | None:
    tag = lexeme.lemma_tag
    if "Fixd" in tag:
        return "noun.indeclinable"
    # Plural-only, also when the dictionary has only rare singular forms (деньги: деньга is Infr).
    if "Pltm" in tag or (_text(lexeme, "sing", "nomn") is None and _text(lexeme, "plur", "nomn") is not None):
        return "noun.pluralia_tantum"
    gender = tag.gender
    if (lemma.endswith("мя") and gender == "neut") or lemma == "путь":
        return "noun.heteroclitic"
    if lemma[-1] in "ая" and gender in ("femn", "masc", "ms-f", "Ms-f"):
        return "noun.decl.1"
    if lemma.endswith("ь") and gender == "femn":
        return "noun.decl.3"
    if gender == "masc" and (lemma[-1] not in VOWELS or lemma[-1] in "й"):
        return "noun.decl.2"
    if gender == "neut" and lemma[-1] in "оеё":
        return "noun.decl.2"
    return None


def classify_noun(lexeme: Lexeme) -> Profile:
    lemma = lexeme.lemma
    profile = Profile("noun", _declension(lexeme, lemma))
    add = profile.findings.append
    if profile.category in ("noun.indeclinable", "noun.pluralia_tantum", None):
        return profile
    if "Sgtm" in lexeme.lemma_tag:
        add(Finding("noun.singularia_tantum", lemma))

    nom_sg = _text(lexeme, "sing", "nomn")
    gen_sg = _text(lexeme, "sing", "gent")
    nom_pl = _text(lexeme, "plur", "nomn")
    gen_pl = _text(lexeme, "plur", "gent")
    gender = lexeme.lemma_tag.gender

    # Suppletive plural: the plural does not even start like the singular (человек → люди).
    # Changes inside the stem (день → дни, сестра → сёстры, ухо → уши) are not suppletion.
    suppletive = bool(nom_sg and nom_pl and nom_sg[0] != nom_pl[0])
    if suppletive:
        add(Finding("noun.suppletive_plural", f"{nom_sg} → {nom_pl}"))

    if nom_sg and gen_sg and profile.category != "noun.heteroclitic":
        nom_stem = nom_sg[:-1] if nom_sg[-1] in "ьйаяоеё" else nom_sg
        gen_stem = gen_sg[:-1] if gen_sg[-1] in "аяиыу" else gen_sg
        if nom_stem != gen_stem and _drop_one(nom_stem, gen_stem, FLEETING):
            add(Finding("noun.fleeting_vowel", f"{nom_sg} → {gen_sg}"))
        elif len(gen_stem) == len(nom_stem) + 2 and gen_stem.startswith(nom_stem) and gen_stem[-2:] in ("ер", "ен"):
            add(Finding("noun.stem_extension", f"{nom_sg} → {gen_sg}"))
    if profile.category == "noun.heteroclitic" and lemma.endswith("мя") and gen_sg:
        add(Finding("noun.stem_extension", f"{nom_sg} → {gen_sg}"))

    if nom_sg and gen_pl and nom_sg[-1] in "аяоеё" and gen_pl[-1] not in VOWELS:
        sg_stem = nom_sg[:-1].replace("ь", "")
        pl_stem = gen_pl.rstrip("ь").replace("ь", "")
        if _drop_one(pl_stem, sg_stem, FLEETING):
            add(Finding("noun.inserted_vowel", f"{nom_sg} → {gen_pl}"))

    if nom_pl and not suppletive:
        if nom_pl.endswith("ья") and not (nom_sg and nom_sg.endswith("ье")):
            add(Finding("noun.plural_ya", f"{nom_sg} → {nom_pl}"))
        elif gender == "masc" and profile.category == "noun.decl.2" and nom_pl[-1] in "ая":
            add(Finding("noun.plural_a", f"{nom_sg} → {nom_pl}"))

    if gender == "masc" and profile.category == "noun.decl.2" and nom_sg and gen_pl == nom_sg and not suppletive:
        add(Finding("noun.gen_plural_zero", f"{nom_sg} → (много) {gen_pl}"))

    loc2 = _text(lexeme, "sing", "loc2")
    if loc2 and loc2 != _text(lexeme, "sing", "loct"):
        add(Finding("noun.loc2", f"в/на {loc2}"))
    gen2 = _text(lexeme, "sing", "gen2")
    if gen2 and gen2 != gen_sg:
        add(Finding("noun.gen2", gen2))

    if "anim" in lexeme.lemma_tag:
        accs_pl = _text(lexeme, "plur", "accs")
        if accs_pl and accs_pl == gen_pl:
            add(Finding("noun.accs_animate", f"{accs_pl}"))

    # Spelling rules visible in this word's endings.
    if nom_pl and nom_pl.endswith("и") and len(nom_pl) > 1 and nom_pl[-2] in HUSHING_GKH \
            and profile.category in ("noun.decl.1", "noun.decl.2"):
        add(Finding("spelling.gkh_i", f"{nom_sg} → {nom_pl}"))
    ablt = _text(lexeme, "sing", "ablt")
    if ablt and len(ablt) > 2 and ablt[-2:] in ("ей", "ем") and ablt[-3] in SIBILANTS_C \
            and profile.category in ("noun.decl.1", "noun.decl.2") and not lemma.endswith(("я", "ь", "е")):
        add(Finding("spelling.sibilant_o_e", f"{nom_sg} → {ablt}"))
    return profile


# --- Adjectives -----------------------------------------------------------------------------

# The four adjectives whose comparative comes from another stem. A closed list in Russian.
SUPPLETIVE_COMPARATIVE = frozenset({"хороший", "плохой", "большой", "маленький"})


def _adjective_category(lexeme: Lexeme, lemma: str) -> str | None:
    if lexeme.pos == "ADJS":
        return "adj.short_only"
    if not lemma.endswith(("ый", "ий", "ой")):
        return None
    stem = lemma[:-2]
    gen = _text(lexeme, "ADJF", "masc", "sing", "gent", exclude=("Supr",)) or ""
    if lemma.endswith("ий") and gen.startswith(stem + "ь"):
        return "adj.possessive_type"                   # третий → третьего, третья
    if stem[-1:] in HUSHING_GKH:
        return "adj.mixed"
    if lemma.endswith("ий"):
        return "adj.soft"
    return "adj.hard"


def classify_adjective(lexeme: Lexeme) -> Profile:
    lemma = lexeme.lemma
    tag = lexeme.lemma_tag
    profile = Profile("adjective", _adjective_category(lexeme, lemma))
    add = profile.findings.append
    if profile.category is None:
        return profile
    stem = lemma[:-2]

    if profile.category != "adj.short_only":
        if lemma.endswith("ой"):
            add(Finding("adj.stressed_ending", lemma))
        nom_pl = _text(lexeme, "ADJF", "plur", "nomn", exclude=("Supr",))
        if nom_pl and nom_pl.endswith("ие") and stem[-1:] in HUSHING_GKH:
            add(Finding("spelling.gkh_i", f"{lemma} → {nom_pl}"))
        gen = _text(lexeme, "ADJF", "masc", "sing", "gent", exclude=("Supr",))
        if gen and gen.endswith("его") and stem[-1:] in SIBILANTS_C:
            add(Finding("spelling.sibilant_o_e", f"{lemma} → {gen}"))
        if "Qual" not in tag and "Anum" not in tag and not lexeme.find("ADJS"):
            add(Finding("adj.relative", lemma))

    short_m = _text(lexeme, "ADJS", "masc")
    short_f = _text(lexeme, "ADJS", "femn")
    if short_m and short_f and profile.category != "adj.short_only":
        if short_m[:2] != lemma[:2]:
            add(Finding("adj.short_suppletive", f"{lemma} → {short_m}"))
        elif _drop_one(_fold(short_m), _fold(short_f[:-1]), FLEETING):
            add(Finding("adj.short_fleeting", f"{lemma} → {short_m}, {short_f}"))

    comparatives = _main(lexeme, "COMP", exclude=("Cmp2",))
    if comparatives:
        if lemma in SUPPLETIVE_COMPARATIVE:
            add(Finding("adj.comparative_suppletive", f"{lemma} → {comparatives[0]}"))
        else:
            in_ee = [c for c in comparatives if c.endswith("ее")]
            in_e = [c for c in comparatives if not c.endswith(("ее", "ей"))]
            if in_ee:
                add(Finding("adj.comparative_ee", f"{lemma} → {in_ee[0]}"))
            if in_e:
                add(Finding("adj.comparative_e", f"{lemma} → {in_e[0]}"))
    return profile


# --- Pronouns -------------------------------------------------------------------------------

# Pronouns are a closed class, so their kind is a list, not a guess from endings.
PRONOUN_CLASSES: dict[str, str] = {
    **dict.fromkeys(("я", "ты", "он", "она", "оно", "мы", "вы", "они"), "pron.personal"),
    "себя": "pron.reflexive",
    **dict.fromkeys(("кто", "что", "какой", "чей"), "pron.interrogative"),
    **dict.fromkeys(("никто", "ничто"), "pron.negative"),
    **dict.fromkeys(("мой", "твой", "наш", "ваш"), "pron.possessive"),
    "свой": "pron.reflexive_possessive",
    **dict.fromkeys(("этот", "тот"), "pron.demonstrative"),
    **dict.fromkeys(("весь", "каждый", "сам"), "pron.definitive"),
}
_AFTER_PREP = (("gent", "у"), ("datv", "к"), ("ablt", "с"), ("loct", "о"))


def is_pronoun(lexeme: Lexeme) -> bool:
    return lexeme.pos == "NPRO" or (lexeme.pos == "ADJF" and "Apro" in lexeme.lemma_tag)


def classify_pronoun(lexeme: Lexeme) -> Profile:
    lemma = lexeme.lemma
    profile = Profile("pronoun", PRONOUN_CLASSES.get(lemma))
    add = profile.findings.append
    if profile.category is None:
        return profile

    if lexeme.find("Af-p"):
        pairs = [f"{prep} {form}" for case, prep in _AFTER_PREP
                 if (form := _text(lexeme, case, "Af-p"))]
        add(Finding("pron.n_after_prep", ", ".join(pairs)))
        gen = _text(lexeme, "gent", exclude=("Af-p",))
        if gen and "3per" in lexeme.lemma_tag:
            add(Finding("pron.possessive_3per", f"{gen} дом, {gen} книга"))
    if not lexeme.find("nomn"):
        add(Finding("pron.no_nominative", ", ".join(t for c in ("gent", "datv", "ablt") if (t := _text(lexeme, c)))))
    if profile.category == "pron.negative":
        datv, ablt = _text(lexeme, "datv"), _text(lexeme, "ablt")
        if datv and ablt and datv.startswith("ни") and ablt.startswith("ни"):
            add(Finding("pron.negative_prep", f"ни к {datv[2:]}, ни с {ablt[2:]}"))

    if lexeme.pos == "ADJF":
        stem = lemma[:-2] if lemma.endswith(("ый", "ий", "ой")) else lemma
        nom_pl = _text(lexeme, "plur", "nomn") or ""
        before_i = nom_pl[-3:-2] if nom_pl.endswith("ие") else nom_pl[-2:-1] if nom_pl.endswith("и") else ""
        if before_i and before_i in HUSHING_GKH:
            add(Finding("spelling.gkh_i", f"{lemma} → {nom_pl}"))
        gen = _text(lexeme, "masc", "sing", "gent")
        if gen and gen.endswith("его") and stem[-1:] in SIBILANTS_C:
            add(Finding("spelling.sibilant_o_e", f"{lemma} → {gen}"))
    return profile


# --- Verbs ----------------------------------------------------------------------------------

# Closed lists from school grammar. Prefixed verbs follow their base (увидеть like видеть).
IRREGULAR_VERBS = frozenset({"быть", "есть", "дать", "поесть", "съесть", "надоесть", "создать", "продать",
                             "передать", "отдать", "задать", "сдать", "издать", "раздать", "подать"})
MIXED_BASES = ("хотеть", "бежать")                     # разноспрягаемые (and чтить)
CONJ2_EXCEPTIONS = ("гнать", "держать", "дышать", "слышать", "видеть", "смотреть", "обидеть", "терпеть",
                    "вертеть", "ненавидеть", "зависеть")   # -ать/-еть verbs of the 2nd conjugation
CONJ1_EXCEPTIONS = ("брить", "стелить")                # -ить verbs of the 1st conjugation
# Verbs of motion: one direction, now (идти) / back and forth, habitually (ходить).
MOTION_PAIRS = (("идти", "ходить"), ("ехать", "ездить"), ("бежать", "бегать"), ("нести", "носить"),
                ("вести", "водить"), ("везти", "возить"), ("лететь", "летать"), ("плыть", "плавать"),
                ("ползти", "ползать"), ("лезть", "лазить"), ("брести", "бродить"), ("гнать", "гонять"),
                ("катить", "катать"), ("тащить", "таскать"))
MOTION = {**{a: ("verb.motion_unidirectional", b) for a, b in MOTION_PAIRS},
          **{b: ("verb.motion_multidirectional", a) for a, b in MOTION_PAIRS}}


def _unreflexive(text: str) -> str:
    return text[:-2] if text.endswith(("ся", "сь")) else text


def _based_on(lemma: str, bases: tuple[str, ...]) -> bool:
    return any(lemma == b or lemma.endswith(b) for b in bases)


def _conjugation(lemma: str, second_sg: str | None, third_pl: str | None) -> str | None:
    if lemma in IRREGULAR_VERBS:
        return "verb.conj.irregular"
    if _based_on(lemma, MIXED_BASES) or lemma == "чтить":
        return "verb.conj.mixed"
    if not second_sg or not third_pl:
        return None
    second_sg, third_pl = _unreflexive(second_sg), _unreflexive(third_pl)
    by_2sg = "1" if second_sg.endswith(("ешь", "ёшь")) else "2" if second_sg.endswith("ишь") else None
    by_3pl = "1" if third_pl.endswith(("ут", "ют")) else "2" if third_pl.endswith(("ат", "ят")) else None
    # Both endings must agree; a verb that mixes them is not guessed.
    return f"verb.conj.{by_2sg}" if by_2sg and by_2sg == by_3pl else None


def classify_verb(lexeme: Lexeme) -> Profile:
    lemma = lexeme.lemma
    aspects = {a for f in lexeme.forms for a in ("impf", "perf") if a in f.tag}
    tense = "pres" if "impf" in aspects else "futr"

    def nonpast(person: str, number: str) -> str | None:
        return _text(lexeme, "VERB", "indc", tense, person, number)

    first_sg, second_sg, third_sg = nonpast("1per", "sing"), nonpast("2per", "sing"), nonpast("3per", "sing")
    third_pl = nonpast("3per", "plur")
    profile = Profile("verb", _conjugation(lemma, second_sg, third_pl))
    add = profile.findings.append

    # Aspect: what the forms without a tense word mean.
    if len(aspects) == 2:
        add(Finding("verb.aspect_both", lemma))
    elif aspects == {"impf"} and first_sg:
        add(Finding("verb.aspect_impf", f"{lemma} → {first_sg}"))
    elif aspects == {"perf"} and first_sg:
        add(Finding("verb.aspect_perf", f"{lemma} → {first_sg}"))

    if lemma.endswith(("ся", "сь")) and first_sg and second_sg:
        add(Finding("verb.reflexive", f"{lemma} → {first_sg}, {second_sg}"))

    conj = profile.category
    if conj == "verb.conj.2" and _based_on(lemma, CONJ2_EXCEPTIONS) and second_sg and third_pl:
        add(Finding("verb.conj_exception", f"{lemma} → {second_sg}, {third_pl}"))
    if conj == "verb.conj.1" and _based_on(lemma, CONJ1_EXCEPTIONS) and second_sg and third_pl:
        add(Finding("verb.conj_exception", f"{lemma} → {second_sg}, {third_pl}"))

    if conj in ("verb.conj.1", "verb.conj.2") and first_sg and second_sg and third_pl:
        stem_1sg = _unreflexive(first_sg)[:-1]                       # пиш-у, люб-лю → любл
        stem_2sg = _unreflexive(second_sg)[:-3]                      # пиш-ешь, люб-ишь
        stem_3pl = _unreflexive(third_pl)[:-2]                       # мог-ут
        infinitive = _unreflexive(lemma)
        inf_stem = infinitive[:-2] if infinitive.endswith(("ть", "ти", "чь")) else infinitive
        if conj == "verb.conj.2" and stem_1sg != stem_2sg:
            add(Finding("verb.alternation_1sg", f"{lemma} → {first_sg}, {second_sg}"))
        elif conj == "verb.conj.1" and stem_1sg != stem_2sg and stem_1sg == stem_3pl:
            add(Finding("verb.alternation_g_k", f"{lemma} → {first_sg}, {second_sg}, {third_pl}"))
        elif conj == "verb.conj.1" and _fold(stem_2sg) != _fold(inf_stem):
            add(Finding("verb.present_stem", f"{lemma} → {first_sg}, {second_sg}"))
        if conj == "verb.conj.1" and _unreflexive(second_sg).endswith("ёшь") and third_sg:
            add(Finding("verb.stressed_yo", f"{lemma} → {second_sg}, {third_sg}"))

    past_m = _text(lexeme, "VERB", "indc", "past", "masc", "sing")
    past_f = _text(lexeme, "VERB", "indc", "past", "femn", "sing")
    if past_m and past_f:
        infinitive = _unreflexive(lemma)
        expected = infinitive[:-2] + "л"
        if _unreflexive(past_m) != expected:
            rule = "verb.past_no_l" if not _unreflexive(past_m).endswith("л") else "verb.past_stem"
            add(Finding(rule, f"{lemma} → {past_m}, {past_f}"))

    if lemma in MOTION:
        rule, partner = MOTION[lemma]
        add(Finding(rule, f"{lemma} — {partner}"))
    return profile


def classify(lexeme: Lexeme) -> Profile | None:
    """The profile for any lexeme the engine can classify; None for other parts of speech."""
    if lexeme.pos == "NOUN":
        return classify_noun(lexeme)
    if is_pronoun(lexeme):
        return classify_pronoun(lexeme)
    if lexeme.pos in ("ADJF", "ADJS"):
        return classify_adjective(lexeme)
    if lexeme.pos == "INFN":
        return classify_verb(lexeme)
    return None
