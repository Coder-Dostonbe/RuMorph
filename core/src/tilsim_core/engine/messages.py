"""User-facing engine messages in uz / ru / en.

The engine records a message as a code with parameters; the text is chosen
when a result is turned into JSON for a given language, so one analysis can be
shown in any of the app's languages.
"""

from __future__ import annotations

from dataclasses import dataclass, field

TEXTS: dict[str, dict[str, str]] = {
    "empty": {
        "uz": "Bo'sh kiritma: ruscha so'z yozing.",
        "ru": "Пустой ввод: напишите русское слово.",
        "en": "Empty input: type a Russian word.",
    },
    "several_words": {
        "uz": "Bitta so'z kiriting (bo'shliqsiz).",
        "ru": "Введите одно слово (без пробелов).",
        "en": "Type a single word (no spaces).",
    },
    "too_long": {
        "uz": "So'z juda uzun (ko'pi bilan {limit} harf).",
        "ru": "Слово слишком длинное (не более {limit} букв).",
        "en": "The word is too long (at most {limit} letters).",
    },
    "uzbek_letters": {
        "uz": "Bu so'zda o'zbek harflari (ў, қ, ғ, ҳ) bor. Ruscha so'z kiriting.",
        "ru": "В слове есть узбекские буквы (ў, қ, ғ, ҳ). Введите русское слово.",
        "en": "The word contains Uzbek letters (ў, қ, ғ, ҳ). Type a Russian word.",
    },
    "latin_script": {
        "uz": "So'z lotin harflarida yozilgan. Ruscha so'zni kirill harflarida kiriting.",
        "ru": "Слово написано латиницей. Введите русское слово кириллицей.",
        "en": "The word is in Latin letters. Type the Russian word in Cyrillic.",
    },
    "mixed_script": {
        "uz": "So'zda kirill va lotin harflari aralash.",
        "ru": "В слове смешаны кириллица и латиница.",
        "en": "The word mixes Cyrillic and Latin letters.",
    },
    "invalid_characters": {
        "uz": "So'zda ruscha bo'lmagan belgilar bor.",
        "ru": "В слове есть нерусские символы.",
        "en": "The word contains characters that are not Russian letters.",
    },
    "latin_replaced": {
        "uz": "Lotin harflari ({letters}) kirillchaga almashtirildi: {fixed}. Klaviatura tilini tekshiring.",
        "ru": "Латинские буквы ({letters}) заменены кириллицей: {fixed}. Проверьте раскладку клавиатуры.",
        "en": "Latin letters ({letters}) were replaced with Cyrillic: {fixed}. Check the keyboard layout.",
    },
    "unknown_word": {
        "uz": "«{word}» lug'atda topilmadi. Engine noma'lum so'zni taxmin qilmaydi.",
        "ru": "«{word}» нет в словаре. Движок не угадывает неизвестные слова.",
        "en": "“{word}” is not in the dictionary. The engine does not guess unknown words.",
    },
    "spelled_with_yo": {
        "uz": "To'g'ri yozilishi: {form} (ё bilan).",
        "ru": "Правильное написание: {form} (с ё).",
        "en": "Correct spelling: {form} (with ё).",
    },
    "rare_form": {
        "uz": "Lug'atda belgilangan: {labels}.",
        "ru": "Помета словаря: {labels}.",
        "en": "Dictionary label: {labels}.",
    },
}


@dataclass(frozen=True)
class Message:
    code: str
    params: dict = field(default_factory=dict)

    def text(self, lang: str = "uz") -> str:
        params = {k: (v(lang) if callable(v) else v) for k, v in self.params.items()}
        return TEXTS[self.code][lang].format(**params)

    def to_dict(self, lang: str = "uz") -> dict:
        return {"code": self.code, "message": self.text(lang)}
