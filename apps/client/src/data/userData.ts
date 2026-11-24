// The learner's own data (db/sqlite/migrations/0002_learning.sql): words, cards, reviews, texts,
// reading sessions, test results; and the admin's translations (0003_admin_translations.sql).
// In the app it lives in SQLite; in a plain browser (development only) in localStorage under
// "tilsim.table.<name>".
//
// Rows are never deleted: removing one sets deleted_at, so the change can be synced.
// Every change raises version and updated_at, and a change to a synced table (SYNCED) puts the
// row into the outbox (0004_sync_outbox.sql) until the server has it (src/sync/engine.ts).
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

/** The learner's tables, which follow the account between devices. Admin translations stay on the device. */
export const SYNCED = ["user_vocabulary", "flashcards", "review_history", "reading_texts", "reading_history", "test_results"] as const;
export type SyncedTable = (typeof SYNCED)[number];
export const isSynced = (name: string): name is SyncedTable => (SYNCED as readonly string[]).includes(name);

export interface OutboxEntry {
  tbl: string;
  id: string;
  version: number;
}

interface Backend {
  readonly kind: "sqlite" | "browser";
  all(table: TableName): Promise<Record<string, unknown>[]>;
  byIds(table: TableName, ids: string[]): Promise<Record<string, unknown>[]>;
  put(table: TableName, row: Record<string, unknown>): Promise<void>;
  /** Deletes every row of the table for real (only when the device changes accounts). */
  clear(table: TableName): Promise<void>;
  outboxMark(entries: OutboxEntry[]): Promise<void>;
  outboxList(limit: number, tables: readonly string[]): Promise<OutboxEntry[]>;
  /** Removes the entry if its version is at most `version` (a newer local change stays queued). */
  outboxAck(tbl: string, id: string, version: number): Promise<void>;
  outboxCount(tables: readonly string[]): Promise<number>;
  outboxClear(tables: readonly string[]): Promise<void>;
}

function decode(table: TableName, row: Record<string, unknown>): Record<string, unknown> {
  const spec: TableSpec = SPECS[table];
  const out = { ...row };
  for (const column of spec.json) out[column] = JSON.parse(String(row[column] ?? "[]"));
  return out;
}

class SqliteBackend implements Backend {
  readonly kind = "sqlite" as const;
  constructor(private db: NonNullable<ReturnType<typeof database>>) {}

  async all(table: TableName): Promise<Record<string, unknown>[]> {
    const rows = await (await this.db).select<Record<string, unknown>[]>(`SELECT * FROM ${table}`);
    return rows.map((row) => decode(table, row));
  }

  async byIds(table: TableName, ids: string[]): Promise<Record<string, unknown>[]> {
    if (!ids.length) return [];
    const placeholders = ids.map((_, i) => `$${i + 1}`).join(", ");
    const rows = await (await this.db).select<Record<string, unknown>[]>(
      `SELECT * FROM ${table} WHERE id IN (${placeholders})`, ids,
    );
    return rows.map((row) => decode(table, row));
  }

  async clear(table: TableName): Promise<void> {
    await (await this.db).execute(`DELETE FROM ${table}`);
  }

  async outboxMark(entries: OutboxEntry[]): Promise<void> {
    const db = await this.db;
    for (let start = 0; start < entries.length; start += 300) {
      const part = entries.slice(start, start + 300);
      const values = part.map((_, i) => `($${3 * i + 1}, $${3 * i + 2}, $${3 * i + 3})`).join(", ");
      await db.execute(
        `INSERT INTO sync_outbox (tbl, id, version) VALUES ${values}
         ON CONFLICT(tbl, id) DO UPDATE SET version = max(version, excluded.version)`,
        part.flatMap((e) => [e.tbl, e.id, e.version]),
      );
    }
  }

  async outboxList(limit: number, tables: readonly string[]): Promise<OutboxEntry[]> {
    const list = tables.map((_, i) => `$${i + 2}`).join(", ");
    return (await this.db).select<OutboxEntry[]>(
      `SELECT tbl, id, version FROM sync_outbox WHERE tbl IN (${list}) ORDER BY tbl, id LIMIT $1`, [limit, ...tables],
    );
  }

  async outboxAck(tbl: string, id: string, version: number): Promise<void> {
    await (await this.db).execute("DELETE FROM sync_outbox WHERE tbl = $1 AND id = $2 AND version <= $3", [tbl, id, version]);
  }

  async outboxCount(tables: readonly string[]): Promise<number> {
    const list = tables.map((_, i) => `$${i + 1}`).join(", ");
    const rows = await (await this.db).select<{ n: number }[]>(`SELECT count(*) AS n FROM sync_outbox WHERE tbl IN (${list})`, [...tables]);
    return Number(rows[0]?.n ?? 0);
  }

  async outboxClear(tables: readonly string[]): Promise<void> {
    const list = tables.map((_, i) => `$${i + 1}`).join(", ");
    await (await this.db).execute(`DELETE FROM sync_outbox WHERE tbl IN (${list})`, [...tables]);
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

  private save(key: string, value: unknown): void {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // Storage unavailable (private mode): the data lasts for this session only.
    }
  }

  async all(table: TableName): Promise<Record<string, unknown>[]> {
    return this.load(table).map((r) => ({ ...r }));
  }

  async byIds(table: TableName, ids: string[]): Promise<Record<string, unknown>[]> {
    const wanted = new Set(ids);
    return this.load(table).filter((r) => wanted.has(String(r.id))).map((r) => ({ ...r }));
  }

  async put(table: TableName, row: Record<string, unknown>): Promise<void> {
    const rows = this.load(table);
    const at = rows.findIndex((r) => r.id === row.id);
    if (at >= 0) rows[at] = { ...row };
    else rows.push({ ...row });
    this.save(`tilsim.table.${table}`, rows);
  }

  async clear(table: TableName): Promise<void> {
    this.memory.set(table, []);
    this.save(`tilsim.table.${table}`, []);
  }

  private outbox: OutboxEntry[] | null = null;

  private loadOutbox(): OutboxEntry[] {
    if (!this.outbox) {
      try {
        this.outbox = JSON.parse(localStorage.getItem("tilsim.sync_outbox") ?? "[]") as OutboxEntry[];
      } catch {
        this.outbox = [];
      }
    }
    return this.outbox;
  }

  async outboxMark(entries: OutboxEntry[]): Promise<void> {
    const box = this.loadOutbox();
    for (const e of entries) {
      const at = box.findIndex((x) => x.tbl === e.tbl && x.id === e.id);
      if (at >= 0) box[at] = { ...e, version: Math.max(box[at]!.version, e.version) };
      else box.push({ ...e });
    }
    this.save("tilsim.sync_outbox", box);
  }

  async outboxList(limit: number, tables: readonly string[]): Promise<OutboxEntry[]> {
    return this.loadOutbox()
      .filter((e) => tables.includes(e.tbl))
      .sort((a, b) => (a.tbl === b.tbl ? (a.id < b.id ? -1 : 1) : a.tbl < b.tbl ? -1 : 1))
      .slice(0, limit)
      .map((e) => ({ ...e }));
  }

  async outboxAck(tbl: string, id: string, version: number): Promise<void> {
    this.outbox = this.loadOutbox().filter((e) => !(e.tbl === tbl && e.id === id && e.version <= version));
    this.save("tilsim.sync_outbox", this.outbox);
  }

  async outboxCount(tables: readonly string[]): Promise<number> {
    return this.loadOutbox().filter((e) => tables.includes(e.tbl)).length;
  }

  async outboxClear(tables: readonly string[]): Promise<void> {
    this.outbox = this.loadOutbox().filter((e) => !tables.includes(e.tbl));
    this.save("tilsim.sync_outbox", this.outbox);
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

type ChangeListener = () => void;
const listeners = new Set<ChangeListener>();

/** Called after every local change to a synced table (the sync schedules a push). */
export function onLocalChange(listener: ChangeListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Writes a row changed on this device: synced tables also get an outbox entry. */
async function write(name: TableName, row: BaseRow): Promise<void> {
  await backend.put(name, row as unknown as Record<string, unknown>);
  if (isSynced(name)) {
    await backend.outboxMark([{ tbl: name, id: row.id, version: row.version }]);
    for (const listener of listeners) listener();
  }
}

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
      await write(name, row);
      return row;
    },
    /** Changes a row; a row marked deleted becomes live again. */
    async update(row: R, changes: Partial<Omit<R, keyof BaseRow>>): Promise<R> {
      const next = { ...row, ...changes, deleted_at: null, updated_at: nowIso(), version: row.version + 1 } as R;
      await write(name, next);
      return next;
    },
    async remove(row: R): Promise<R> {
      const at = nowIso();
      const next = { ...row, deleted_at: at, updated_at: at, version: row.version + 1 } as R;
      await write(name, next);
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

/** Low-level access for the sync engine (src/sync/engine.ts); the app uses the tables above. */
export const syncStore = {
  all: (name: SyncedTable): Promise<BaseRow[]> => backend.all(name) as unknown as Promise<BaseRow[]>,
  byIds: (name: SyncedTable, ids: string[]): Promise<BaseRow[]> => backend.byIds(name, ids) as unknown as Promise<BaseRow[]>,
  /** A row from the server: written as it is, without an outbox entry. */
  putRemote: (name: SyncedTable, row: BaseRow): Promise<void> => backend.put(name, row as unknown as Record<string, unknown>),
  /** A row this device changed while merging (a duplicate it marked deleted): goes to the outbox. */
  putLocal: (name: SyncedTable, row: BaseRow): Promise<void> => write(name, row),
  outboxList: (limit: number) => backend.outboxList(limit, SYNCED),
  outboxAck: (tbl: SyncedTable, id: string, version: number) => backend.outboxAck(tbl, id, version),
  outboxCount: () => backend.outboxCount(SYNCED),
  /** Queues every row of the learner's tables (the first sync of this device with an account). */
  async markAll(): Promise<void> {
    for (const name of SYNCED) {
      const rows = (await backend.all(name)) as unknown as BaseRow[];
      await backend.outboxMark(rows.map((r) => ({ tbl: name, id: r.id, version: r.version })));
    }
  },
  /** Removes the learner's data from this device (it belongs to another account). */
  async wipe(): Promise<void> {
    for (const name of SYNCED) await backend.clear(name);
    await backend.outboxClear(SYNCED);
  },
};

/**
 * The device's copy of the shared translations (admin_translations): rows from the server and the
 * admin's own edits. An edit waits in the outbox until the server has it (src/sync/translations.ts).
 */
export const translationStore = {
  all: () => adminTranslations.listAll(),
  byIds: (ids: string[]) => backend.byIds("admin_translations", ids) as unknown as Promise<AdminTranslationRow[]>,
  /** A row as the server has it: written without an outbox entry. */
  putRemote: (row: AdminTranslationRow) => backend.put("admin_translations", row as unknown as Record<string, unknown>),
  mark: (rows: AdminTranslationRow[]) =>
    backend.outboxMark(rows.map((r) => ({ tbl: "admin_translations", id: r.id, version: r.version }))),
  pending: (limit: number) => backend.outboxList(limit, ["admin_translations"]),
  ack: (id: string, version: number) => backend.outboxAck("admin_translations", id, version),
  count: () => backend.outboxCount(["admin_translations"]),
};
