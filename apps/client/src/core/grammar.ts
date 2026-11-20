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

export interface LexemeInfo {
  id: string;
  lemma: string;
  pos: string | null;
  description: string;
  source: string;
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
  grammemes: (lang: Locale) => core.call<Grammemes>("grammemes", { lang }),
  lexiconInfo: () => core.call<LexiconInfo>("lexicon_info"),
};

/** Every form index a cell stands for (one text can be several forms of a lexeme). */
export function cellIndices(cell: Cell): number[] {
  return cell.index === undefined ? [] : [cell.index, ...(cell.also ?? [])];
}
