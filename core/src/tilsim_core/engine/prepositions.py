"""Which case each preposition takes, and what it means with that case.

A preposition decides the case of the noun (or pronoun, adjective, numeral)
after it. Several take two or three cases with different meanings (в школу —
direction, в школе — place), so a word after such a preposition can still be
ambiguous; context.py then lists every reading with its meaning.

Prepositions are a closed class, so this is curated data, not a rule applied
to unknown words. The second genitive / locative / accusative count as the
case they belong to (в лесу is the prepositional of в). Readings marked
`rare` are correct but limited to set phrases.
"""

from __future__ import annotations

from dataclasses import dataclass

# A governed case also accepts these tag cases.
CASE_VARIANTS = {"gent": ("gent", "gen2"), "accs": ("accs", "acc2"), "loct": ("loct", "loc2"),
                 "datv": ("datv",), "ablt": ("ablt",), "nomn": ("nomn",)}


@dataclass(frozen=True)
class Government:
    case: str
    uz: str
    ru: str
    en: str
    example: str
    rare: bool = False

    def meaning(self, lang: str) -> str:
        return {"uz": self.uz, "ru": self.ru, "en": self.en}[lang]

    def to_dict(self, lang: str) -> dict:
        return {"case": self.case, "meaning": self.meaning(lang), "example": self.example, "rare": self.rare}


_G = Government
PREPOSITIONS: dict[str, tuple[Government, ...]] = {
    "в": (_G("accs", "qayerga? (ichiga); qachon? (kun, soat)", "куда? (внутрь); когда? (день, час)",
             "where to? (into); when? (day, hour)", "в школу, в среду"),
          _G("loct", "qayerda? (ichida); qachon? (oy, yil)", "где? (внутри); когда? (месяц, год)",
             "where? (inside); when? (month, year)", "в школе, в мае")),
    "на": (_G("accs", "qayerga? (ustiga, tadbirga)", "куда? (на поверхность, на мероприятие)",
              "where to? (onto, to an event)", "на стол, на работу"),
           _G("loct", "qayerda? (ustida, tadbirda)", "где? (на поверхности, на мероприятии)",
              "where? (on, at an event)", "на столе, на работе")),
    "с": (_G("gent", "qayerdan? (ustidan, tadbirdan); qachondan?", "откуда? (с поверхности); с какого времени?",
             "from where? (off, from an event); since when?", "с работы, с утра"),
          _G("ablt", "kim bilan? nima bilan?", "с кем? с чем?", "with whom? with what?", "с другом, с молоком")),
    "о": (_G("loct", "kim haqida? nima haqida?", "о ком? о чём?", "about whom? about what?", "о книге, о нём"),),
    "у": (_G("gent", "kimning yonida; kimda bor (у меня есть)", "около; у кого (у меня есть)",
             "by, near; who has (у меня есть)", "у дома, у брата"),),
    "к": (_G("datv", "kimga? nimaga? (tomon)", "к кому? к чему?", "towards whom? towards what?", "к другу, к дому"),),
    "от": (_G("gent", "kimdan? qayerdan? (uzoqlashish)", "от кого? откуда?", "from whom? away from where?",
              "от друга, от дома"),),
    "до": (_G("gent", "qayergacha? qachongacha?", "до какого места? до какого времени?", "up to where? until when?",
              "до дома, до утра"),),
    "из": (_G("gent", "qayerdan? (ichidan)", "откуда? (изнутри)", "from where? (out of)", "из школы, из Ташкента"),),
    "за": (_G("accs", "nima uchun? (rahmat, to'lov); orqasiga", "за что? (спасибо, оплата); куда? (за что-то)",
              "for what? (thanks, payment); behind (direction)", "спасибо за помощь, за дом"),
           _G("ablt", "orqasida; nimaga? (olib kelish uchun)", "где? (позади); за чем? (сходить за хлебом)",
              "behind; to fetch (сходить за хлебом)", "за домом, за хлебом")),
    "под": (_G("accs", "qayerga? (tagiga)", "куда? (вниз под что-то)", "where to? (under)", "под стол"),
            _G("ablt", "qayerda? (tagida)", "где? (под чем-то)", "where? (under)", "под столом")),
    "над": (_G("ablt", "ustida (tegmasdan)", "над чем? (выше)", "above", "над столом, над городом"),),
    "перед": (_G("ablt", "oldida; ...dan oldin", "перед чем? (впереди; раньше)", "in front of; before",
                 "перед домом, перед уроком"),),
    "без": (_G("gent", "kimsiz? nimasiz?", "без кого? без чего?", "without", "без сахара, без друга"),),
    "для": (_G("gent", "kim uchun? nima uchun?", "для кого? для чего?", "for whom? for what?", "для друга, для работы"),),
    "через": (_G("accs", "orqali, ustidan; ...dan keyin", "через что? (сквозь; спустя)", "across, through; in (time)",
                 "через улицу, через час"),),
    "про": (_G("accs", "kim haqida? nima haqida? (so'zlashuvda)", "про кого? про что? (разг.)",
               "about (informal)", "про книгу, про него"),),
    "по": (_G("datv", "bo'ylab; orqali; bo'yicha", "по чему? (по поверхности; средство; предмет)",
              "along; by means of; in (a subject)", "по улице, по телефону, по математике"),
           _G("accs", "...gacha (barqaror birikmalarda)", "до (в устойчивых сочетаниях)", "up to (set phrases)",
              "по колено, по пятое мая", rare=True),
           _G("loct", "...dan keyin (kitobiy)", "после (книжн.)", "after (formal)", "по приезде", rare=True)),
    "при": (_G("loct", "huzurida; davrida; qoshida", "при ком? при чём? (в присутствии; во время)",
               "in the presence of; at the time of; attached to", "при школе, при мне"),),
    "между": (_G("ablt", "orasida", "между кем? между чем?", "between", "между домами, между нами"),
              _G("gent", "orasida (barqaror birikmalarda)", "между (в устойчивых сочетаниях)", "between (set phrases)",
                 "между двух огней", rare=True)),
    "благодаря": (_G("datv", "tufayli (yaxshi sabab)", "по причине (положительной)", "thanks to",
                     "благодаря другу, благодаря помощи"),),
    "ввиду": (_G("gent", "sababli (rasmiy)", "по причине (офиц.)", "in view of", "ввиду погоды"),),
    "вдоль": (_G("gent", "bo'ylab (chetidan)", "по длине чего-либо", "along", "вдоль реки, вдоль дороги"),),
    "включая": (_G("accs", "shu jumladan", "в том числе", "including", "включая детей"),),
    "вместо": (_G("gent", "o'rniga", "взамен", "instead of", "вместо чая, вместо брата"),),
    "вне": (_G("gent", "tashqarisida", "за пределами", "outside", "вне дома, вне очереди"),),
    "внутри": (_G("gent", "ichida", "в пределах чего-либо", "inside", "внутри дома"),),
    "возле": (_G("gent", "yonida", "около, рядом", "next to", "возле дома"),),
    "вокруг": (_G("gent", "atrofida", "кругом", "around", "вокруг дома, вокруг света"),),
    "вроде": (_G("gent", "...ga o'xshash (so'zlashuvda)", "наподобие (разг.)", "like, such as (informal)",
                 "вроде этого"),),
    "кроме": (_G("gent", "...dan tashqari", "за исключением; сверх", "except; besides", "кроме брата"),),
    "мимо": (_G("gent", "yonidan o'tib", "проходя рядом", "past", "мимо дома"),),
    "насчёт": (_G("gent", "haqida (so'zlashuvda)", "относительно (разг.)", "about (informal)", "насчёт работы"),),
    "несмотря": (_G("accs", "...ga qaramay (несмотря на + tushum kelishigi)", "вопреки (несмотря на + В. п.)",
                    "despite (несмотря на + accusative)", "несмотря на дождь"),),
    "ниже": (_G("gent", "...dan pastda", "под уровнем", "below", "ниже нуля"),),
    "около": (_G("gent", "yonida; taxminan", "возле; приблизительно", "near; about (a number)",
                 "около дома, около часа"),),
    "относительно": (_G("gent", "haqida, borasida (rasmiy)", "по поводу (офиц.)", "concerning (formal)",
                        "относительно плана"),),
    "помимо": (_G("gent", "...dan tashqari, ...dan boshqa", "кроме", "apart from", "помимо работы"),),
    "после": (_G("gent", "...dan keyin", "позже чего-либо", "after", "после урока, после обеда"),),
    "прежде": (_G("gent", "...dan oldin (kitobiy)", "раньше (книжн.)", "before (formal)", "прежде всего"),),
    "против": (_G("gent", "qarshi; ro'parasida", "в противоположность; напротив", "against; opposite",
                  "против войны, против дома"),),
    "путём": (_G("gent", "yo'li bilan", "посредством", "by means of", "путём переговоров"),),
    "ради": (_G("gent", "...uchun, ...ning xotiri uchun", "для, во имя", "for the sake of", "ради детей"),),
    "свыше": (_G("gent", "...dan ortiq", "больше чем", "over, more than", "свыше ста человек"),),
    "сквозь": (_G("accs", "orqali, ichidan o'tib", "через (преодолевая)", "through", "сквозь окно, сквозь сон"),),
    "согласно": (_G("datv", "...ga muvofiq", "в соответствии с", "according to", "согласно закону"),),
    "спустя": (_G("accs", "...dan keyin (vaqt o'tib)", "через (о времени)", "later, after (time)", "спустя час"),),
    "среди": (_G("gent", "orasida, o'rtasida", "в середине; в числе", "among; in the middle of",
                 "среди друзей, среди ночи"),),
}


def governed(lemma: str) -> tuple[Government, ...]:
    return PREPOSITIONS.get(lemma, ())
