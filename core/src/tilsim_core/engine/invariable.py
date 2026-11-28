"""Rules for the words that do not inflect: adverbs, predicatives, prepositions,
conjunctions, particles and interjections.

These are closed or nearly closed classes, so their kinds come from curated
lists (as for pronouns in classify.py) and from the dictionary's own marks
(Ques, Dmns, Prnt). What can be checked against the lexicon is checked there:
an adverb is said to come from an adjective only when that adjective's short
neuter form is the adverb itself (быстрый → быстро), and a preposition's cases
come from prepositions.py. A word none of the lists knows gets the general
rule of its part of speech, which holds for every word of that class.
"""

from __future__ import annotations

from .classify import Finding, Profile, _main
from .lexicon import Lexeme, Lexicon
from .prepositions import governed

# --- Adverbs --------------------------------------------------------------------------------

DEMONSTRATIVE_ADVERBS = frozenset({"здесь", "сюда", "отсюда", "столь", "столько"})   # besides those marked Dmns
INTERROGATIVE_ADVERBS = frozenset({"сколько"})                                      # besides those marked Ques
# Negative adverbs need не with the verb as well (double negation).
NEGATIVE_ADVERBS = {"никогда": "Я никогда не был там.", "нигде": "Его нигде нет.", "никуда": "Я никуда не пойду.",
                    "ниоткуда": "Ниоткуда не слышно ответа.", "никак": "Никак не могу понять.",
                    "нисколько": "Я нисколько не устал."}
# Quantity adverbs take a noun in the genitive; несколько only countable nouns.
QUANTITY_ADVERBS = {w: f"{w} книг, {w} воды" for w in
                    ("много", "мало", "немного", "немало", "сколько", "столько", "достаточно", "недостаточно")}
QUANTITY_ADVERBS["несколько"] = "несколько книг, несколько дней"
ANALYTIC_DEGREE = {"более": "более интересный", "менее": "менее интересный", "наиболее": "наиболее интересный"}
# Times of day and seasons: the instrumental of a noun used as an adverb.
TIME_FROM_NOUN = {"утром": "утро", "днём": "день", "вечером": "вечер", "ночью": "ночь",
                  "весной": "весна", "летом": "лето", "осенью": "осень", "зимой": "зима"}
# ь after a hushing consonant at the end of an adverb, except these three.
NO_SOFT_SIGN = frozenset({"уж", "замуж", "невтерпёж"})
HUSHING = "жшщч"
# Prefix + short adjective stem: из-, до-, с- take -а; в-, на-, за- take -о.
PREFIX_SUFFIX = (("из", "а"), ("до", "а"), ("с", "а"), ("в", "о"), ("на", "о"), ("за", "о"))


def _key(word: str) -> str:
    return word.lower().replace("ё", "е")


def _source_adjective(word: str, lexicon: Lexicon) -> Lexeme | None:
    """The qualitative adjective whose short neuter form is `word` (быстро → быстрый)."""
    for lexeme, form in lexicon.lookup(word):
        if lexeme.pos == "ADJF" and "Apro" not in lexeme.lemma_tag and "ADJS" in form.tag \
                and "neut" in form.tag and "sing" in form.tag:
            return lexeme
    return None


def _adjective_with_stem(stem: str, lexicon: Lexicon) -> Lexeme | None:
    for ending in ("ый", "ий", "ой"):
        for lexeme, form in lexicon.lookup(stem + ending):
            if lexeme.pos == "ADJF" and "Apro" not in lexeme.lemma_tag and _key(lexeme.lemma) == _key(stem + ending):
                return lexeme
    return None


def _adverb_spelling(lemma: str, lexicon: Lexicon) -> list[Finding]:
    found = []
    if lemma[-1:] == "о" and lemma[-2:-1] in HUSHING:
        found.append(Finding("spelling.adv_hushing_o", lemma))             # хорошо, свежо
    if lemma[-1:] == "ь" and lemma[-2:-1] in HUSHING or lemma in NO_SOFT_SIGN:
        found.append(Finding("spelling.adv_soft_sign", lemma))
    for prefix, suffix in PREFIX_SUFFIX:
        if lemma.startswith(prefix) and lemma.endswith(suffix) and len(lemma) > len(prefix) + 2:
            adjective = _adjective_with_stem(lemma[len(prefix):-1], lexicon)
            if adjective is not None:
                found.append(Finding("spelling.adv_prefix_a_o", f"{adjective.headword} → {lemma}"))
                break
    return found


def classify_adverb(lexeme: Lexeme, lexicon: Lexicon) -> Profile:
    lemma = lexeme.lemma
    tag = lexeme.lemma_tag
    if "Ques" in tag or lemma in INTERROGATIVE_ADVERBS:
        category = "adv.interrogative"
    elif "Dmns" in tag or lemma in DEMONSTRATIVE_ADVERBS:
        category = "adv.demonstrative"
    elif lemma in NEGATIVE_ADVERBS:
        category = "adv.negative"
    else:
        category = "adv.class"
    profile = Profile("adverb", category)
    add = profile.findings.append
    if category == "adv.negative":
        add(Finding("adv.double_negation", NEGATIVE_ADVERBS[lemma]))

    if lemma in QUANTITY_ADVERBS:
        add(Finding("adv.quantity_gen", QUANTITY_ADVERBS[lemma]))
    elif lemma in ANALYTIC_DEGREE:
        add(Finding("adv.analytic_degree", ANALYTIC_DEGREE[lemma]))
    elif lemma in TIME_FROM_NOUN:
        noun = TIME_FROM_NOUN[lemma]
        if any(lx.pos == "NOUN" and _key(lx.lemma) == _key(noun) and "ablt" in f.tag
               for lx, f in lexicon.lookup(lemma)):
            add(Finding("adv.from_noun", f"{noun} → {lemma}"))
    else:
        adjective = _source_adjective(lemma, lexicon)
        if adjective is not None:
            add(Finding("adv.from_adjective", f"{adjective.headword} → {lemma}"))
            had_forms = "forms" in adjective.__dict__
            comparatives = _main(adjective, "COMP", exclude=("Cmp2",))
            if not had_forms:
                adjective.__dict__.pop("forms", None)
            # Only the comparatives a learner cannot build with -ее (чаще, лучше); the dictionary also lists
            # formally possible ones (социальнее) that are better not taught as the word's comparative.
            irregular = [c for c in comparatives if not c.endswith(("ее", "ей"))]
            if irregular:
                add(Finding("adv.comparative", f"{lemma} → {irregular[0]}"))
    profile.findings.extend(_adverb_spelling(lemma, lexicon))
    return profile


# --- Predicatives (категория состояния) -----------------------------------------------------

WITH_INFINITIVE = frozenset({"можно", "надо", "нужно", "нельзя", "необходимо", "пора"})
NO_TENSE_EXAMPLE = frozenset({"нет", "должно"})       # нет → не было; должно is a set phrase (должно быть)


def classify_predicative(lexeme: Lexeme, lexicon: Lexicon) -> Profile:
    lemma = lexeme.lemma
    profile = Profile("predicative", "adv.predicative")
    add = profile.findings.append
    if lemma == "нет":
        add(Finding("adv.net_genitive", "нет времени — не было времени — не будет времени"))
    else:
        if lemma in WITH_INFINITIVE:
            add(Finding("adv.with_infinitive", f"мне {lemma} идти"))
        if lemma not in NO_TENSE_EXAMPLE:
            add(Finding("adv.state_tense", f"{lemma} — было {lemma} — будет {lemma}"))
    adjective = _source_adjective(lemma, lexicon)
    if adjective is not None and lemma not in NO_TENSE_EXAMPLE:
        add(Finding("adv.from_adjective", f"{adjective.headword} → {lemma}"))
    profile.findings.extend(f for f in _adverb_spelling(lemma, lexicon) if f.rule_id == "spelling.adv_hushing_o")
    return profile


# --- Prepositions ---------------------------------------------------------------------------

CASE_RULES = {"gent": "prep.gent", "datv": "prep.datv", "accs": "prep.accs", "ablt": "prep.ablt", "loct": "prep.loct"}


def classify_preposition(lexeme: Lexeme) -> Profile:
    lemma = lexeme.lemma
    profile = Profile("preposition", "prep.class")
    add = profile.findings.append
    for government in governed(lemma):
        if government.rare or government.case not in CASE_RULES:
            continue
        note = (government.uz, government.ru, government.en)
        add(Finding(CASE_RULES[government.case], government.example, note))
    variants = list(dict.fromkeys(f.text for f in lexeme.forms if "Vpre" in f.tag))
    if variants:
        add(Finding("prep.vowel_variant", f"{lemma} → {', '.join(variants)}"))
    return profile


# --- Conjunctions ---------------------------------------------------------------------------

COORDINATING = frozenset({"и", "а", "но", "или", "либо", "да", "зато", "ни", "же", "только", "иначе", "причём",
                          "равно"})
SUBORDINATING = frozenset({"что", "чтобы", "чтоб", "как", "если", "когда", "где", "куда", "чем", "хотя", "хоть",
                           "пока", "поскольку", "ли", "будто", "словно", "точно", "раз", "ибо", "сколько",
                           "пусть", "лишь"})
# A comma always comes before these when they join two parts of a sentence.
COMMA_BEFORE = {"а": "Он работает, а я отдыхаю.", "но": "Дорого, но красиво.", "зато": "Дорого, зато удобно.",
                "причём": "Он пришёл, причём вовремя.", "иначе": "Спеши, иначе опоздаешь.",
                "только": "Иди, только осторожно."}
# Repeated conjunctions: a comma before the second one.
PAIRED = {"или": "или чай, или кофе", "либо": "либо сегодня, либо завтра", "ни": "ни чай, ни кофе"}
SAME_SOUND = {"тоже": "Я тоже пойду. — Я сделаю то же самое.", "также": "Он также знает. — Сделай так же, как я."}


def classify_conjunction(lexeme: Lexeme) -> Profile:
    lemma = lexeme.lemma
    if "Prnt" in lexeme.lemma_tag:
        category = "conj.parenthetical"
    elif lemma in COORDINATING:
        category = "conj.coordinating"
    elif lemma in SUBORDINATING:
        category = "conj.subordinating"
    else:
        category = "conj.class"
    profile = Profile("conjunction", category)
    add = profile.findings.append
    if lemma in COMMA_BEFORE and category == "conj.coordinating":
        add(Finding("conj.comma_before", COMMA_BEFORE[lemma]))
    if lemma in PAIRED and category == "conj.coordinating":
        add(Finding("conj.paired", PAIRED[lemma]))
    if lemma in SAME_SOUND:
        add(Finding("spelling.tozhe_takzhe", SAME_SOUND[lemma]))
    return profile


# --- Particles ------------------------------------------------------------------------------

FORMATIVE = {"бы": ("prcl.subjunctive", "я бы пошёл, она бы пошла, они бы пошли"),
             "б": ("prcl.subjunctive", "я б пошёл, она б пошла"),
             "пусть": ("prcl.imperative_3", "пусть он придёт, пусть они знают")}
NEGATIVE = {"не": ("prcl.ne_separate", "не знаю, не был, не читай"),
            "ни": ("prcl.ni", "ни слова, ни разу, ни один")}
NAME_PARTS = frozenset({"ван", "ла"})
MODAL = frozenset({"же", "ж", "это", "также", "тоже", "вот", "даже", "то", "просто", "да", "только", "ну", "всё",
                   "как", "именно", "лишь", "что", "уже", "там", "ведь", "всего", "так", "хоть", "хотя", "лучше",
                   "таки", "ещё", "ничего", "нет", "хорошо", "вроде", "ли", "почти", "правда", "пожалуйста", "было",
                   "уж", "куда", "ка", "прямо", "разве", "будто", "никак", "неужели", "чтобы", "себе", "окей"})
QUESTION = {"ли": "Знаешь ли ты?", "разве": "Разве ты не знаешь?", "неужели": "Неужели это правда?"}
HYPHENATED = {"ка": "дай-ка, ну-ка, посмотри-ка", "таки": "всё-таки, пришёл-таки"}


def classify_particle(lexeme: Lexeme) -> Profile:
    lemma = lexeme.lemma
    if lemma in FORMATIVE:
        category = "prcl.formative"
    elif lemma in NEGATIVE:
        category = "prcl.negative"
    elif lemma in NAME_PARTS:
        category = "prcl.name_part"
    elif lemma in MODAL:
        category = "prcl.modal"
    else:
        category = "prcl.class"
    profile = Profile("particle", category)
    add = profile.findings.append
    if lemma in FORMATIVE:
        add(Finding(*FORMATIVE[lemma]))
    if lemma in NEGATIVE:
        add(Finding(*NEGATIVE[lemma]))
    if lemma in QUESTION:
        add(Finding("prcl.question", QUESTION[lemma]))
    if lemma in HYPHENATED:
        add(Finding("prcl.hyphen", HYPHENATED[lemma]))
    if lemma in SAME_SOUND:
        add(Finding("spelling.tozhe_takzhe", SAME_SOUND[lemma]))
    return profile


# --- Interjections --------------------------------------------------------------------------

def classify_interjection(lexeme: Lexeme) -> Profile:
    return Profile("interjection", "intj.class")


def classify_invariable(lexeme: Lexeme, lexicon: Lexicon) -> Profile | None:
    pos = lexeme.pos
    if pos == "ADVB":
        return classify_adverb(lexeme, lexicon)
    if pos == "PRED":
        return classify_predicative(lexeme, lexicon)
    if pos == "PREP":
        return classify_preposition(lexeme)
    if pos == "CONJ":
        return classify_conjunction(lexeme)
    if pos == "PRCL":
        return classify_particle(lexeme)
    if pos == "INTJ":
        return classify_interjection(lexeme)
    return None
