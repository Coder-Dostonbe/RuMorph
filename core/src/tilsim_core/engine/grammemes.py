"""Grammemes: the grammatical labels of OpenCorpora tags, grouped into categories,
with names in Uzbek, Russian and English.

The lexicon stores OpenCorpora's own codes ("NOUN", "gent", "perf", …), so this
table is the single place where a code gets its meaning. Codes not listed here
are kept (they come from the data) but shown by their code.

Terminology follows Russian school grammar, with the Uzbek name first and the
Russian term in brackets where Uzbek has no exact equivalent.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Grammeme:
    code: str
    category: str
    uz: str
    ru: str
    en: str

    def name(self, lang: str = "uz") -> str:
        return {"uz": self.uz, "ru": self.ru, "en": self.en}.get(lang, self.uz)


# Category ids, also used by the app to order labels.
CATEGORIES = (
    "pos", "animacy", "gender", "number", "case", "aspect", "transitivity",
    "person", "tense", "mood", "involvement", "voice", "degree", "subtype", "usage", "variant",
)

_G = Grammeme
GRAMMEMES: dict[str, Grammeme] = {g.code: g for g in [
    # --- Part of speech
    _G("NOUN", "pos", "ot", "существительное", "noun"),
    _G("ADJF", "pos", "sifat", "прилагательное (полное)", "adjective"),
    _G("ADJS", "pos", "sifatning qisqa shakli", "краткое прилагательное", "short adjective"),
    _G("COMP", "pos", "qiyosiy daraja", "компаратив", "comparative"),
    _G("VERB", "pos", "fe'l", "глагол (личная форма)", "verb"),
    _G("INFN", "pos", "fe'l (infinitiv)", "глагол (инфинитив)", "infinitive"),
    _G("PRTF", "pos", "sifatdosh", "причастие (полное)", "participle"),
    _G("PRTS", "pos", "sifatdoshning qisqa shakli", "краткое причастие", "short participle"),
    _G("GRND", "pos", "ravishdosh", "деепричастие", "adverbial participle"),
    _G("NUMR", "pos", "son", "числительное", "numeral"),
    _G("ADVB", "pos", "ravish", "наречие", "adverb"),
    _G("NPRO", "pos", "olmosh", "местоимение-существительное", "pronoun"),
    _G("PRED", "pos", "holat so'zi", "предикатив", "predicative"),
    _G("PREP", "pos", "predlog", "предлог", "preposition"),
    _G("CONJ", "pos", "bog'lovchi", "союз", "conjunction"),
    _G("PRCL", "pos", "yuklama", "частица", "particle"),
    _G("INTJ", "pos", "undov", "междометие", "interjection"),
    # --- Animacy
    _G("anim", "animacy", "jonli", "одушевлённое", "animate"),
    _G("inan", "animacy", "jonsiz", "неодушевлённое", "inanimate"),
    # --- Gender
    _G("masc", "gender", "erkak jinsi", "мужской род", "masculine"),
    _G("femn", "gender", "ayol jinsi", "женский род", "feminine"),
    _G("neut", "gender", "o'rta jins", "средний род", "neuter"),
    _G("ms-f", "gender", "umumiy jins", "общий род", "common gender"),
    _G("Ms-f", "gender", "umumiy jins", "общий род", "common gender"),
    _G("GNdr", "gender", "jinsi belgilanmaydi", "род не выражен", "gender not marked"),
    # --- Number
    _G("sing", "number", "birlik", "единственное число", "singular"),
    _G("plur", "number", "ko'plik", "множественное число", "plural"),
    _G("Sgtm", "number", "faqat birlikda ishlatiladi", "только единственное число", "singular only"),
    _G("Pltm", "number", "faqat ko'plikda ishlatiladi", "только множественное число", "plural only"),
    # --- Case
    _G("nomn", "case", "bosh kelishik", "именительный падеж", "nominative"),
    _G("gent", "case", "qaratqich kelishigi", "родительный падеж", "genitive"),
    _G("datv", "case", "jo'nalish kelishigi", "дательный падеж", "dative"),
    _G("accs", "case", "tushum kelishigi", "винительный падеж", "accusative"),
    _G("ablt", "case", "vosita kelishigi", "творительный падеж", "instrumental"),
    _G("loct", "case", "o'rin kelishigi", "предложный падеж", "prepositional"),
    _G("voct", "case", "chaqiruv shakli", "звательная форма", "vocative"),
    _G("gen2", "case", "2-qaratqich kelishigi", "второй родительный (партитив)", "partitive genitive"),
    _G("acc2", "case", "2-tushum kelishigi", "второй винительный", "second accusative"),
    _G("loc2", "case", "2-o'rin kelishigi", "второй предложный (местный)", "locative"),
    # --- Verb categories
    _G("perf", "aspect", "tugallangan tus", "совершенный вид", "perfective"),
    _G("impf", "aspect", "tugallanmagan tus", "несовершенный вид", "imperfective"),
    _G("tran", "transitivity", "o'timli", "переходный", "transitive"),
    _G("intr", "transitivity", "o'timsiz", "непереходный", "intransitive"),
    _G("1per", "person", "1-shaxs", "1-е лицо", "1st person"),
    _G("2per", "person", "2-shaxs", "2-е лицо", "2nd person"),
    _G("3per", "person", "3-shaxs", "3-е лицо", "3rd person"),
    _G("pres", "tense", "hozirgi zamon", "настоящее время", "present"),
    _G("past", "tense", "o'tgan zamon", "прошедшее время", "past"),
    _G("futr", "tense", "kelasi zamon", "будущее время", "future"),
    _G("indc", "mood", "aniqlik mayli", "изъявительное наклонение", "indicative"),
    _G("impr", "mood", "buyruq mayli", "повелительное наклонение", "imperative"),
    _G("incl", "involvement", "birgalikdagi harakat (пойдём)", "совместное действие", "inclusive"),
    _G("excl", "involvement", "suhbatdoshga qaratilgan", "говорящий не включён", "exclusive"),
    _G("actv", "voice", "aniq nisbat", "действительный залог", "active"),
    _G("pssv", "voice", "majhul nisbat", "страдательный залог", "passive"),
    # --- Degree and subtypes
    _G("Supr", "degree", "orttirma daraja", "превосходная степень", "superlative"),
    _G("Cmp2", "degree", "qiyosiy daraja (по- bilan)", "сравнительная степень с по-", "comparative with по-"),
    _G("Qual", "subtype", "sifatlovchi", "качественное", "qualitative"),
    _G("Apro", "subtype", "olmosh-sifat", "местоименное", "pronominal"),
    _G("Anum", "subtype", "tartib son kabi", "порядковое", "ordinal-like"),
    _G("Poss", "subtype", "egalik", "притяжательное", "possessive"),
    _G("Fixd", "subtype", "turlanmaydi", "неизменяемое", "indeclinable"),
    _G("Abbr", "subtype", "qisqartma", "аббревиатура", "abbreviation"),
    _G("Anph", "subtype", "anaforik", "анафорическое", "anaphoric"),
    _G("Dmns", "subtype", "ko'rsatish", "указательное", "demonstrative"),
    _G("Subx", "subtype", "ot o'rnida keladi", "субстантивируемое", "substantive-like"),
    _G("Adjx", "subtype", "sifat o'rnida keladi", "адъективируемое", "adjective-like"),
    _G("Prdx", "subtype", "kesim bo'la oladi", "может быть сказуемым", "predicative-like"),
    _G("Af-p", "subtype", "predlogdan keyingi shakl (него)", "форма после предлога", "form after preposition"),
    _G("Vpre", "subtype", "unli qo'shilgan predlog (со, во)", "вариант предлога с гласной", "preposition with added vowel"),
    _G("Fimp", "subtype", "tugallanmagan fe'lning shakli", "форма несовершенного вида", "imperfective form"),
    # --- Usage notes
    _G("Infr", "usage", "so'zlashuvda, kam ishlatiladi", "разговорное", "informal"),
    _G("Slng", "usage", "jargon", "жаргонное", "slang"),
    _G("Arch", "usage", "eskirgan", "устаревшее", "archaic"),
    _G("Litr", "usage", "adabiy", "литературный вариант", "literary"),
    _G("Erro", "usage", "noto'g'ri yozilish", "опечатка", "misspelling"),
    _G("Dist", "usage", "buzilgan shakl (ети, чо)", "искажённая форма", "distorted form"),
    # --- Spelling variants
    _G("V-be", "variant", "variant shakl (-ье)", "вариант на -ье", "variant (-ье)"),
    _G("V-en", "variant", "variant shakl", "вариант", "variant"),
    _G("V-ie", "variant", "variant shakl (-ие)", "вариант на -ие", "variant (-ие)"),
    _G("V-bi", "variant", "variant shakl (-ьи)", "вариант на -ьи", "variant (-ьи)"),
    _G("V-ey", "variant", "variant shakl (-ею)", "вариант на -ею", "variant (-ею)"),
    _G("V-oy", "variant", "variant shakl (-ою)", "вариант на -ою", "variant (-ою)"),
    _G("V-ej", "variant", "variant shakl (-ей)", "вариант на -ей", "variant (-ей)"),
    _G("V-sh", "variant", "variant shakl (-ши)", "вариант на -ши", "variant (-ши)"),
]}

# Usage notes that make a form worth flagging to a learner.
RARE_USAGE = frozenset({"Infr", "Slng", "Arch", "Erro", "Dist"})

# Forms left out when the engine needs "the" form of a cell to explain a rule: rare usage,
# spelling variants (-ою, -ею, …) and literary variants (краше). They stay in every table.
NOT_MAIN = RARE_USAGE | frozenset({"Litr", "V-be", "V-bi", "V-ey", "V-oy", "V-ej", "V-sh", "V-ie", "V-en"})


def grammeme(code: str) -> Grammeme | None:
    return GRAMMEMES.get(code)


def describe(code: str, lang: str = "uz") -> str:
    g = GRAMMEMES.get(code)
    return g.name(lang) if g else code
