// The learner's own data (db/sqlite/migrations/0002_learning.sql): words, cards, reviews, texts,
// reading sessions, test results; and the admin's translations (0003_admin_translations.sql).
// In the app it lives in SQLite; in a plain browser (development only) in localStorage under
// "tilsim.table.<name>".
//
// Rows are never deleted: removing one sets deleted_at, so the change can be synced (Phase 6).
// Every change raises version and updated_at.
import { database } from "./db";

export interface BaseRow {
  id: string;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  version: number;
}

export interface Example {
  ru: string;
  uz: string;
}

export interface VocabularyRow extends BaseRow {
  lexeme_id: string;
  lemma: string;
  pos: string | null;
  translation: string;
  note: string;
  examples: Example[];
  status: "learning" | "known";
}

/** A translation entered in the admin panel (0003_admin_translations.sql). */
export interface AdminTranslationRow extends BaseRow {
  lexeme_id: string;
  lemma: string;
  translation: string;
}

export type Direction = "ru_uz" | "uz_ru";

export interface FlashcardRow extends BaseRow {
  lexeme_id: string;
  direction: Direction;
  due_at: string;
  interval_days: number;
  ease: number;
  reps: number;
  lapses: number;
  last_review_at: string | null;
}

export interface ReviewRow extends BaseRow {
  card_id: string;
  reviewed_at: string;
  grade: 0 | 1 | 2 | 3;
  interval_after: number;
  ease_after: number;
}

export interface ReadingTextRow extends BaseRow {
  title: string;
  body: string;
  source: string;
}

export interface ReadingRow extends BaseRow {
  text_id: string;
  read_at: string;
  words: number;
  looked_up: number;
  duration_ms: number;
}

export interface TestResultRow extends BaseRow {
  kind: string;
  taken_at: string;
  total: number;
  correct: number;
  details: unknown[];
}

interface TableSpec {
  columns: string[];
  json: string[];
}

const BASE = ["id", "created_at", "updated_at", "deleted_at", "version"];
const SPECS = {
  user_vocabulary: {
    columns: [...BASE, "lexeme_id", "lemma", "pos", "translation", "note", "examples", "status"],
    json: ["examples"],
  },
  flashcards: {
    columns: [...BASE, "lexeme_id", "direction", "due_at", "interval_days", "ease", "reps", "lapses", "last_review_at"],
    json: [],
  },
  review_history: { columns: [...BASE, "card_id", "reviewed_at", "grade", "interval_after", "ease_after"], json: [] },
  reading_texts: { columns: [...BASE, "title", "body", "source"], json: [] },
  reading_history: { columns: [...BASE, "text_id", "read_at", "words", "looked_up", "duration_ms"], json: [] },
  test_results: { columns: [...BASE, "kind", "taken_at", "total", "correct", "details"], json: ["details"] },
  admin_translations: { columns: [...BASE, "lexeme_id", "lemma", "translation"], json: [] },
} satisfies Record<string, TableSpec>;

export type TableName = keyof typeof SPECS;

interface Backend {
  readonly kind: "sqlite" | "browser";
  all(table: TableName): Promise<Record<string, unknown>[]>;
  put(table: TableName, row: Record<string, unknown>): Promise<void>;
}

class SqliteBackend implements Backend {
  readonly kind = "sqlite" as const;
  constructor(private db: NonNullable<ReturnType<typeof database>>) {}

  async all(table: TableName): Promise<Record<string, unknown>[]> {
    const rows = await (await this.db).select<Record<string, unknown>[]>(`SELECT * FROM ${table}`);
    const spec: TableSpec = SPECS[table];
    return rows.map((row) => {
      const out = { ...row };
      for (const column of spec.json) out[column] = JSON.parse(String(row[column] ?? "[]"));
      return out;
    });
  }

  async put(table: TableName, row: Record<string, unknown>): Promise<void> {
    const spec: TableSpec = SPECS[table];
    const values = spec.columns.map((c) => (spec.json.includes(c) ? JSON.stringify(row[c] ?? []) : row[c] ?? null));
    const placeholders = spec.columns.map((_, i) => `$${i + 1}`).join(", ");
    const updates = spec.columns.filter((c) => c !== "id").map((c) => `${c} = excluded.${c}`).join(", ");
    await (await this.db).execute(
      `INSERT INTO ${table} (${spec.columns.join(", ")}) VALUES (${placeholders}) ON CONFLICT(id) DO UPDATE SET ${updates}`,
      values,
    );
  }
}

class BrowserBackend implements Backend {
  readonly kind = "browser" as const;
  private memory = new Map<TableName, Record<string, unknown>[]>();

  private load(table: TableName): Record<string, unknown>[] {
    let rows = this.memory.get(table);
    if (!rows) {
      try {
        rows = JSON.parse(localStorage.getItem(`tilsim.table.${table}`) ?? "[]") as Record<string, unknown>[];
      } catch {
        rows = [];
      }
      this.memory.set(table, rows);
    }
    return rows;
  }

  async all(table: TableName): Promise<Record<string, unknown>[]> {
    return this.load(table).map((r) => ({ ...r }));
  }

  async put(table: TableName, row: Record<string, unknown>): Promise<void> {
    const rows = this.load(table);
    const at = rows.findIndex((r) => r.id === row.id);
    if (at >= 0) rows[at] = { ...row };
    else rows.push({ ...row });
    try {
      localStorage.setItem(`tilsim.table.${table}`, JSON.stringify(rows));
    } catch {
      // Storage unavailable (private mode): the data lasts for this session only.
    }
  }
}

const db = database();
const backend: Backend = db ? new SqliteBackend(db) : new BrowserBackend();
export const storageKind = backend.kind;

/** UUID v7: 48-bit Unix time in milliseconds, then random bits; sorts by creation time. */
export function uuidv7(now = Date.now()): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let t = now;
  for (let i = 5; i >= 0; i--) {
    bytes[i] = t % 256;
    t = Math.floor(t / 256);
  }
  bytes[6] = (bytes[6]! & 0x0f) | 0x70;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export function nowIso(): string {
  return new Date().toISOString();
}

type RowOf<T extends TableName> = T extends "user_vocabulary"
  ? VocabularyRow
  : T extends "flashcards"
    ? FlashcardRow
    : T extends "review_history"
      ? ReviewRow
      : T extends "reading_texts"
        ? ReadingTextRow
        : T extends "reading_history"
          ? ReadingRow
          : T extends "admin_translations"
            ? AdminTranslationRow
            : TestResultRow;

export type NewRow<R extends BaseRow> = Omit<R, keyof BaseRow> & Partial<Pick<R, "id">>;

/** Typed access to one table. Deleted rows are hidden from list(). */
export function table<T extends TableName>(name: T) {
  type R = RowOf<T>;
  return {
    async list(): Promise<R[]> {
      return ((await backend.all(name)) as unknown as R[]).filter((r) => !r.deleted_at);
    },
    /** Every row, the ones marked deleted included. */
    async listAll(): Promise<R[]> {
      return (await backend.all(name)) as unknown as R[];
    },
    async insert(fields: NewRow<R>): Promise<R> {
      const at = nowIso();
      const row = { ...fields, id: fields.id ?? uuidv7(), created_at: at, updated_at: at, deleted_at: null, version: 1 } as R;
      await backend.put(name, row as unknown as Record<string, unknown>);
      return row;
    },
    /** Changes a row; a row marked deleted becomes live again. */
    async update(row: R, changes: Partial<Omit<R, keyof BaseRow>>): Promise<R> {
      const next = { ...row, ...changes, deleted_at: null, updated_at: nowIso(), version: row.version + 1 } as R;
      await backend.put(name, next as unknown as Record<string, unknown>);
      return next;
    },
    async remove(row: R): Promise<R> {
      const at = nowIso();
      const next = { ...row, deleted_at: at, updated_at: at, version: row.version + 1 } as R;
      await backend.put(name, next as unknown as Record<string, unknown>);
      return next;
    },
  };
}

export const vocabulary = table("user_vocabulary");
export const flashcards = table("flashcards");
export const reviews = table("review_history");
export const readingTexts = table("reading_texts");
export const readings = table("reading_history");
export const testResults = table("test_results");
export const adminTranslations = table("admin_translations");
