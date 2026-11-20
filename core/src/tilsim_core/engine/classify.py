"""Decides which rules explain a lexeme: its declension class and its exceptions.

The lexicon already holds the correct forms. Here they are compared with each
other (nominative with genitive, singular with plural, …) to find what a learner
needs to be told: a fleeting vowel, a plural on another stem, a spelling rule.
Each finding names a rule from rules.py and gives the concrete example from
this word. A check that cannot decide says nothing rather than guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field

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
class NounProfile:
    declension: str | None                 # rule id of the declension class, None if unknown
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"declension": self.declension, "findings": [f.to_dict() for f in self.findings]}


def _text(lexeme: Lexeme, *grammemes: str) -> str | None:
    """The main (non-rare) form with these grammemes."""
    forms = lexeme.find(*grammemes, exclude=("Infr", "Arch", "Erro", "Slng", "V-be", "V-bi", "V-ey", "V-oy",
                                            "V-ej", "V-sh", "V-ie", "V-en"))
    return forms[0].text if forms else None


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


def classify_noun(lexeme: Lexeme) -> NounProfile:
    lemma = lexeme.lemma
    profile = NounProfile(declension=_declension(lexeme, lemma))
    add = profile.findings.append
    if profile.declension in ("noun.indeclinable", "noun.pluralia_tantum", None):
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

    if nom_sg and gen_sg and profile.declension != "noun.heteroclitic":
        nom_stem = nom_sg[:-1] if nom_sg[-1] in "ьйаяоеё" else nom_sg
        gen_stem = gen_sg[:-1] if gen_sg[-1] in "аяиыу" else gen_sg
        if nom_stem != gen_stem and _drop_one(nom_stem, gen_stem, FLEETING):
            add(Finding("noun.fleeting_vowel", f"{nom_sg} → {gen_sg}"))
        elif len(gen_stem) == len(nom_stem) + 2 and gen_stem.startswith(nom_stem) and gen_stem[-2:] in ("ер", "ен"):
            add(Finding("noun.stem_extension", f"{nom_sg} → {gen_sg}"))
    if profile.declension == "noun.heteroclitic" and lemma.endswith("мя") and gen_sg:
        add(Finding("noun.stem_extension", f"{nom_sg} → {gen_sg}"))

    if nom_sg and gen_pl and nom_sg[-1] in "аяоеё" and gen_pl[-1] not in VOWELS:
        sg_stem = nom_sg[:-1].replace("ь", "")
        pl_stem = gen_pl.rstrip("ь").replace("ь", "")
        if _drop_one(pl_stem, sg_stem, FLEETING):
            add(Finding("noun.inserted_vowel", f"{nom_sg} → {gen_pl}"))

    if nom_pl and not suppletive:
        if nom_pl.endswith("ья") and not (nom_sg and nom_sg.endswith("ье")):
            add(Finding("noun.plural_ya", f"{nom_sg} → {nom_pl}"))
        elif gender == "masc" and profile.declension == "noun.decl.2" and nom_pl[-1] in "ая":
            add(Finding("noun.plural_a", f"{nom_sg} → {nom_pl}"))

    if gender == "masc" and profile.declension == "noun.decl.2" and nom_sg and gen_pl == nom_sg and not suppletive:
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
            and profile.declension in ("noun.decl.1", "noun.decl.2"):
        add(Finding("spelling.gkh_i", f"{nom_sg} → {nom_pl}"))
    ablt = _text(lexeme, "sing", "ablt")
    if ablt and len(ablt) > 2 and ablt[-2:] in ("ей", "ем") and ablt[-3] in SIBILANTS_C \
            and profile.declension in ("noun.decl.1", "noun.decl.2") and not lemma.endswith(("я", "ь", "е")):
        add(Finding("spelling.sibilant_o_e", f"{nom_sg} → {ablt}"))
    return profile
