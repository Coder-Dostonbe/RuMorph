"""Russian grammar engine.

- normalize: clean up a typed word (stress marks, ё/е, keyboard-layout mistakes).
- lexicon: lexemes with full OpenCorpora paradigms; analysis is a lookup.
- analyze: every reading of a word, "ambiguous" when there are several.
- classify + rules: which declension and which exceptions explain a lexeme.
- tables: paradigms arranged for display.

Standard library only (tests/test_architecture.py), so it runs under Pyodide
in the app, in the Python Worker and in tests alike.
"""

from .analyze import AMBIGUOUS, ERROR, OK, Analysis, Reading, analyze
from .classify import NounProfile, classify_noun
from .lexicon import Lexeme, Lexicon, default_lexicon
from .normalize import normalize_word
from .rules import RULES, Rule
from .tables import paradigm_table
from .tag import Tag

__all__ = [
    "AMBIGUOUS", "ERROR", "OK", "RULES", "Analysis", "Lexeme", "Lexicon", "NounProfile", "Reading", "Rule",
    "Tag", "analyze", "classify_noun", "default_lexicon", "normalize_word", "paradigm_table",
]
