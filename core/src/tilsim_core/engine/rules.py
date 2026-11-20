"""Registry of the grammar rules the engine can name and explain.

Word forms come from the lexicon (OpenCorpora paradigms); rules do not build
them. A rule here explains why a form looks the way it does: which declension a
noun follows, which spelling rule chose an ending, what makes a word an
exception. classify.py decides which rules apply to a lexeme.

As in ArabMorph, rules are data: explanations, examples and review status live
here, separate from the code that detects them, so they can move into the
central database later. Nothing is specialist-reviewed yet.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

SCHOOL = "Русский язык, школьная грамматика (склонение существительных); ссылка уточняется"
ROSENTAL = "Д. Э. Розенталь, «Справочник по правописанию и литературной правке»; раздел уточняется"


@dataclass(frozen=True)
class Rule:
    id: str
    kind: str          # "declension" | "exception" | "spelling" | "note"
    name_uz: str
    name_ru: str
    name_en: str
    explanation_uz: str
    explanation_ru: str
    explanation_en: str
    example: str
    reference: str
    review_status: str = "pending_specialist_review"

    def to_dict(self, lang: str | None = None) -> dict:
        """All fields, or with `lang` the name and explanation in that language only."""
        if lang is None:
            return asdict(self)
        return {
            "id": self.id, "kind": self.kind,
            "name": getattr(self, f"name_{lang}"), "explanation": getattr(self, f"explanation_{lang}"),
            "example": self.example, "reference": self.reference, "review_status": self.review_status,
        }


_RULES = [
    # --- Declension classes (Russian school numbering: 1 = -а/-я, 2 = masc. zero / neut., 3 = fem. -ь)
    Rule("noun.decl.1", "declension",
         "1-turlanish", "1-е склонение", "1st declension",
         "-а yoki -я bilan tugaydigan otlar: asosan ayol jinsi, ba'zan erkak jinsi (папа, дедушка). "
         "Qaratqich birlikda -ы/-и, jo'nalish va o'rin kelishigida -е oladi.",
         "Существительные на -а/-я женского (и некоторые мужского) рода: стена, неделя, папа.",
         "Nouns ending in -а/-я, mostly feminine, some masculine (папа).",
         "книга → книги, книге, книгу, книгой, о книге", SCHOOL),
    Rule("noun.decl.2", "declension",
         "2-turlanish", "2-е склонение", "2nd declension",
         "Qo'shimchasiz tugaydigan erkak jinsidagi otlar (стол, день, музей) va -о/-е bilan tugaydigan "
         "o'rta jinsdagi otlar (окно, море). Qaratqich birlikda -а/-я oladi.",
         "Существительные мужского рода с нулевым окончанием и среднего рода на -о/-е.",
         "Masculine nouns with a zero ending and neuter nouns in -о/-е.",
         "стол → стола, столу, столом, о столе; окно → окна", SCHOOL),
    Rule("noun.decl.3", "declension",
         "3-turlanish", "3-е склонение", "3rd declension",
         "-ь bilan tugaydigan ayol jinsidagi otlar. Qaratqich, jo'nalish va o'rin kelishigida -и oladi; "
         "tushum bosh kelishik bilan bir xil.",
         "Существительные женского рода на -ь: ночь, тетрадь.",
         "Feminine nouns ending in -ь.",
         "тетрадь → тетради, тетради, тетрадь, тетрадью, о тетради", SCHOOL),
    Rule("noun.heteroclitic", "declension",
         "Noodatiy turlanish", "Разносклоняемые существительные", "Heteroclitic nouns",
         "-мя bilan tugaydigan o'rta jinsdagi 10 ta ot (время, имя, знамя…) va путь so'zi. Ular ikki "
         "turlanish qo'shimchalarini aralash oladi; -мя otlarida o'zakka -ен- qo'shiladi.",
         "Десять существительных на -мя и слово «путь».",
         "Ten neuter nouns in -мя, and путь.",
         "время → времени, временем; путь → пути, путём", SCHOOL),
    Rule("noun.indeclinable", "declension",
         "Turlanmaydigan ot", "Несклоняемое существительное", "Indeclinable noun",
         "Asosan chet tilidan kirgan otlar (кофе, метро, такси, пальто). Barcha kelishik va sonlarda "
         "shakli o'zgarmaydi; jinsini sifat va fe'l ko'rsatadi (чёрный кофе).",
         "Не изменяются по падежам и числам.", "Never change their form.",
         "в метро, без пальто, с кофе", SCHOOL),
    Rule("noun.pluralia_tantum", "declension",
         "Faqat ko'plikda", "Только множественное число", "Plural-only noun",
         "Bu ot faqat ko'plik shaklida ishlatiladi (ножницы, очки, деньги). Birlik shakli yo'q yoki juda kam.",
         "Существительное употребляется только во множественном числе.", "Used only in the plural.",
         "ножницы → ножниц, ножницам", SCHOOL),
    Rule("noun.singularia_tantum", "declension",
         "Faqat birlikda", "Только единственное число", "Singular-only noun",
         "Bu ot odatda faqat birlikda ishlatiladi (молоко, мир ma'nosida 'tinchlik').",
         "Существительное употребляется только в единственном числе.", "Normally used only in the singular.",
         "молоко → молока, молоку", SCHOOL),
    # --- Exceptions found by comparing forms
    Rule("noun.fleeting_vowel", "exception",
         "Qochuvchi unli", "Беглая гласная", "Fleeting vowel",
         "Bosh kelishikdagi о/е/ё boshqa shakllarda tushib qoladi.",
         "Гласная о/е/ё основы выпадает в косвенных падежах.",
         "The о/е/ё of the stem drops out in the other forms.",
         "день → дня, отец → отца, ребёнок → ребёнка", SCHOOL),
    Rule("noun.inserted_vowel", "exception",
         "Qo'shiluvchi unli", "Беглая гласная в род. п. мн. ч.", "Inserted vowel",
         "Ko'plik qaratqich kelishigida qo'shimcha bo'lmaganda, ikki undosh orasiga о/е/ё qo'shiladi.",
         "В род. п. мн. ч. с нулевым окончанием между согласными появляется о/е/ё.",
         "In the genitive plural with a zero ending, о/е/ё appears between two consonants.",
         "девочка → девочек, сестра → сестёр, окно → окон", SCHOOL),
    Rule("noun.stem_extension", "exception",
         "O'zak kengayishi", "Наращение основы", "Stem extension",
         "Bosh kelishikdan tashqari shakllarda o'zakka -ер- yoki -ен- qo'shiladi.",
         "В косвенных падежах к основе прибавляется -ер- или -ен-.",
         "In the other cases the stem adds -ер- or -ен-.",
         "мать → матери, дочь → дочери, время → времени", SCHOOL),
    Rule("noun.plural_ya", "exception",
         "Ko'plikda -ья", "Мн. ч. на -ья", "Plural in -ья",
         "Ko'plik bosh kelishigida -ья qo'shimchasi va o'zgargan o'zak.",
         "Им. п. мн. ч. на -ья, часто с изменением основы.",
         "Nominative plural in -ья, often with a changed stem.",
         "брат → братья, друг → друзья, стул → стулья, дерево → деревья", SCHOOL),
    Rule("noun.suppletive_plural", "exception",
         "Ko'plik boshqa so'zdan", "Супплетивное множественное число", "Suppletive plural",
         "Ko'plik shakli butunlay boshqa o'zakdan yasaladi.",
         "Множественное число образуется от другой основы.",
         "The plural is built on a different stem.",
         "человек → люди, ребёнок → дети", SCHOOL),
    Rule("noun.plural_a", "exception",
         "Ko'plikda urg'uli -а/-я", "Мн. ч. на ударное -а/-я", "Plural in stressed -а/-я",
         "Bu erkak jinsidagi ot ko'plik bosh kelishigida -ы/-и o'rniga urg'uli -а/-я oladi.",
         "Им. п. мн. ч. на ударное -а/-я вместо -ы/-и.",
         "Nominative plural in stressed -а/-я instead of -ы/-и.",
         "дом → дома, город → города, глаз → глаза", SCHOOL),
    Rule("noun.gen_plural_zero", "exception",
         "Ko'plik qaratqichida qo'shimchasiz", "Нулевое окончание в род. п. мн. ч.",
         "Zero ending in the genitive plural",
         "Erkak jinsidagi bu ot ko'plik qaratqich kelishigida -ов olmaydi.",
         "Род. п. мн. ч. без окончания -ов.",
         "The genitive plural takes no -ов.",
         "глаз → (много) глаз", SCHOOL),
    Rule("noun.loc2", "exception",
         "2-o'rin kelishigi", "Второй предложный (местный) падеж", "Locative in -у/-ю",
         "в va на predloglari bilan joy ma'nosida -у/-ю (urg'uli) oladi; о bilan esa oddiy -е.",
         "С предлогами в/на в значении места — окончание -у/-ю; с «о» — обычное -е.",
         "After в/на meaning place the ending is stressed -у/-ю; after о it is the usual -е.",
         "в лесу, в саду, на берегу (lekin: о лесе)", SCHOOL),
    Rule("noun.gen2", "exception",
         "2-qaratqich (miqdor)", "Второй родительный (партитив)", "Partitive genitive",
         "Miqdor ma'nosida -у/-ю qo'shimchasi ham ishlatiladi.",
         "В значении части целого возможно окончание -у/-ю.",
         "When meaning 'some of', -у/-ю is also used.",
         "чашка чаю, много народу", SCHOOL),
    Rule("noun.accs_animate", "note",
         "Jonli otning tushum kelishigi", "Винительный падеж одушевлённых", "Accusative of animate nouns",
         "Jonli otlarda tushum kelishigi qaratqich kelishigi bilan bir xil bo'ladi: erkak jinsida birlikda, "
         "barcha jinslarda ko'plikda.",
         "У одушевлённых существительных В. п. совпадает с Р. п. (м. р. ед. ч. и мн. ч.).",
         "For animate nouns the accusative equals the genitive (masc. sing. and all plurals).",
         "вижу брата, вижу сестёр", SCHOOL),
    # --- Spelling rules
    Rule("spelling.gkh_i", "spelling",
         "г, к, х, ж, ш, щ, ч dan keyin и", "После г, к, х, ж, ш, щ, ч пишется и", "и after г к х ж ш щ ч",
         "Bu harflardan keyin ы yozilmaydi, uning o'rniga и yoziladi.",
         "После г, к, х, ж, ш, щ, ч не пишется ы, пишется и.",
         "After these letters ы is never written; и is written instead.",
         "книга → книги, нож → ножи, врач → врачи", ROSENTAL),
    Rule("spelling.sibilant_o_e", "spelling",
         "ж, ш, щ, ч, ц dan keyin urg'usiz е", "После шипящих и ц без ударения пишется е",
         "Unstressed е after sibilants and ц",
         "Qo'shimchada urg'u tushmasa, bu harflardan keyin о o'rniga е yoziladi.",
         "После ж, ш, щ, ч, ц в безударном окончании пишется е, под ударением — о.",
         "After ж ш щ ч ц an unstressed ending has е; a stressed one has о.",
         "улица → улицей (lekin: душа → душой)", ROSENTAL),
    # --- Data notes
    Rule("lexicon.form", "note",
         "Lug'atdan olingan shakl", "Форма из словаря", "Form from the dictionary",
         "Bu shakl OpenCorpora lug'atidan olingan, qoida bo'yicha taxmin qilinmagan.",
         "Форма взята из словаря OpenCorpora.", "This form comes from the OpenCorpora dictionary.",
         "", "OpenCorpora, CC BY-SA 3.0"),
    Rule("lexicon.rare_form", "note",
         "Kam ishlatiladigan shakl", "Редкая форма", "Rare form",
         "Lug'atda bu shakl so'zlashuvga oid, eskirgan yoki variant deb belgilangan.",
         "Форма помечена в словаре как разговорная, устаревшая или вариантная.",
         "The dictionary marks this form as informal, archaic or a variant.",
         "деньга (деньги ning birligi)", "OpenCorpora, CC BY-SA 3.0"),
]

RULES: dict[str, Rule] = {r.id: r for r in _RULES}
assert len(RULES) == len(_RULES), "duplicate rule id"


def rule(rule_id: str) -> Rule:
    return RULES[rule_id]
