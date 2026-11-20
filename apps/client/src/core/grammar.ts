// Typed calls to the grammar engine (tilsim_core.engine through the bridge) and the shapes of
// its replies. Shapes follow core/src/tilsim_core/engine/{analyze,context,tables,classify}.py.
import type { Locale } from "../i18n";
import { core } from "./client";

export type Status = "ok" | "ambiguous" | "error";

export interface EngineMessage {
  code: string;
  message: string;
}

export interface Government {
  case: string;
  meaning: string;
  example: string;
  rare: boolean;
}

export interface Reading {
  lexeme: string;
  lemma: string;
  form: string;
  form_index: number;
  pos: string | null;
  description: string;
  rules: string[];
  confidence: number;
  frequency: number | null;
  notes: string[];
  government?: Government;
}

export interface Analysis {
  input: string;
  word: string;
  status: Status;
  lemmas: string[];
  readings: Reading[];
  warnings: string[];
  errors: EngineMessage[];
  suggestions: string[];
  stress_index: number | null;
}

export interface PhraseAnalysis {
  preposition: string;
  word: string;
  status: Status;
  governs: Government[];
  readings: Reading[];
  warnings: string[];
  errors: EngineMessage[];
  suggestions: string[];
}

export interface Cell {
  form: string;
  index?: number;
  also?: number[];
  rare?: boolean;
  variant?: boolean;
  constructed?: boolean;
  rule?: string;
}

export interface Row {
  key: string;
  cells: Cell[][];
}

export interface ExtraForm {
  form: string;
  index: number;
  tag: string;
  rare: boolean;
  description: string;
}

interface TableBase {
  extra: ExtraForm[];
}

export interface GridTable extends TableBase {
  kind: "noun" | "pronoun" | "numeral";
  columns: string[];
  rows: Row[];
}

export interface AdjectiveTable extends TableBase {
  kind: "adjective";
  columns: string[];
  rows: Row[];
  short: Cell[][] | null;
  comparative: Cell[] | null;
}

export interface Participle {
  key: string;
  lemma: Cell[];
  columns: string[];
  rows: Row[];
  short: Cell[][] | null;
}

export interface VerbTable extends TableBase {
  kind: "verb";
  aspect: "impf" | "perf" | "both" | null;
  transitivity: "tran" | "intr" | null;
  infinitive: Cell[];
  nonpast: { tense: "pres" | "futr"; columns: string[]; rows: Row[] }[];
  future_compound: Row[] | null;
  past: { columns: string[]; cells: Cell[][] } | null;
  imperative: Row[];
  participles: Participle[];
  gerunds: { key: string; cells: Cell[] }[];
}

export interface ListTable extends TableBase {
  kind: "list";
}

export type Table = GridTable | AdjectiveTable | VerbTable | ListTable;

export interface Finding {
  rule: string;
  detail: string;
}

export interface Profile {
  kind: string;
  category: string | null;
  findings: Finding[];
}

export interface WordSummary {
  id: string;
  lemma: string;
  pos: string | null;
  description: string;
  frequency: number | null;
  rank: number | null;
}

export interface SearchResult {
  total: number;
  items: (WordSummary & { match: "form" | "prefix" | "browse" })[];
}

export interface KeyForm {
  form: string;
  grammemes: string[];
  index: number;
}

export type WordInfo = WordSummary & { key_forms: KeyForm[] };

export interface CardState {
  due_at: string;
  interval_days: number;
  ease: number;
  reps: number;
  lapses: number;
  last_review_at: string | null;
}

export interface CatalogRule extends Rule {
  words: number;
}

export interface Catalog {
  groups: { id: "noun" | "adj" | "pron" | "num" | "verb" | "spelling"; rules: CatalogRule[] }[];
}

export interface RuleExamples {
  total: number;
  items: (WordSummary & { detail: string })[];
}

export interface PrepositionInfo {
  preposition: string;
  governs: Government[];
}

export type ExerciseKind = "case_form" | "conjugation" | "gender" | "preposition" | "aspect" | "translation";

export interface Question {
  kind: ExerciseKind;
  lexeme: string;
  lemma: string;
  prompt: { grammemes?: string[]; preposition?: string; case?: string };
  options: string[];
  answer: number;
  rule: string | null;
  option_kind?: "grammeme";
}

export interface SpellIssue {
  start: number;
  end: number;
  word: string;
  level: "error" | "grammar" | "unknown" | "note" | "repeat";
  messages: string[];
  suggestions: string[];
  replace_start: number;
  replace_end: number;
}

export interface SpellResult {
  words: number;
  known: number;
  issues: SpellIssue[];
}

export interface ReadingToken {
  start: number;
  end: number;
  lexemes: string[];
  known: boolean;
  rank: number | null;
}

export interface PreparedText {
  tokens: ReadingToken[];
  words: number;
  distinct_lemmas: number;
  coverage: Record<"500" | "1000" | "3000", number>;
  unknown: number;
}

export const POS_FILTERS = ["NOUN", "ADJF", "VERB", "ADVB", "NPRO", "NUMR", "PREP", "CONJ", "PRCL", "PRED", "INTJ"] as const;
export type PosFilter = (typeof POS_FILTERS)[number];

export interface LexemeInfo {
  id: string;
  lemma: string;
  pos: string | null;
  description: string;
  source: string;
  frequency: number | null;
  rank: number | null;
  profile: Profile | null;
  table: Table;
}

export interface Rule {
  id: string;
  kind: string;
  name: string;
  explanation: string;
  example: string;
  reference: string;
  review_status: string;
}

export interface Grammemes {
  categories: string[];
  grammemes: Record<string, { name: string; category: string }>;
}

export interface LexiconSource {
  name: string;
  url: string;
  license: string;
  version?: string;
  revision?: string;
  via?: string;
}

export interface LexiconInfo {
  packages: { package: string; version: string; description: string; source: LexiconSource }[];
  lexemes: number;
  forms: number;
}

export const grammar = {
  analyze: (word: string, lang: Locale) => core.call<Analysis>("analyze", { word, lang }),
  phrase: (preposition: string, word: string, lang: Locale) =>
    core.call<PhraseAnalysis>("phrase", { preposition, word, lang }),
  lexeme: (id: string, lang: Locale) => core.call<LexemeInfo>("lexeme", { id, lang }),
  rules: (lang: Locale) => core.call<Rule[]>("rules", { lang }),
  catalog: (lang: Locale) => core.call<Catalog>("grammar", { lang }),
  ruleExamples: (rule: string, lang: Locale, offset = 0, limit = 24) =>
    core.call<RuleExamples>("rule_examples", { rule, lang, offset, limit }),
  prepositions: (lang: Locale) => core.call<PrepositionInfo[]>("prepositions", { lang }),
  exercises: (kind: ExerciseKind, count: number, seed: number, maxRank: number,
    vocabulary: { lexeme_id: string; lemma: string; translation: string }[] = []) =>
    core.call<Question[]>("exercises", { kind, count, seed, max_rank: maxRank, vocabulary }),
  spellcheck: (text: string, lang: Locale) => core.call<SpellResult>("spellcheck", { text, lang }),
  reading: (text: string) => core.call<PreparedText>("reading", { text }),
  words: (ids: string[], lang: Locale) => core.call<Record<string, WordInfo>>("words", { ids, lang }),
  srsReview: (card: CardState, grade: 0 | 1 | 2 | 3, now: string) =>
    core.call<{ card: CardState }>("srs_review", { card, grade, now }),
  srsPreview: (card: CardState, now: string) => core.call<{ days: Record<string, number> }>("srs_preview", { card, now }),
  srsQueue: (cards: (CardState & { id: string })[], now: string, newLimit: number, newSeenToday: number) =>
    core.call<{ ids: string[] }>("srs_queue", { cards, now, new_limit: newLimit, new_seen_today: newSeenToday }),
  search: (query: string, lang: Locale, opts: { pos?: PosFilter | null; limit?: number; offset?: number } = {}) =>
    core.call<SearchResult>("search", {
      query, lang, limit: opts.limit ?? 30, offset: opts.offset ?? 0, ...(opts.pos ? { pos: opts.pos } : {}),
    }),
  grammemes: (lang: Locale) => core.call<Grammemes>("grammemes", { lang }),
  lexiconInfo: () => core.call<LexiconInfo>("lexicon_info"),
};

/** Every form index a cell stands for (one text can be several forms of a lexeme). */
export function cellIndices(cell: Cell): number[] {
  return cell.index === undefined ? [] : [cell.index, ...(cell.also ?? [])];
}
