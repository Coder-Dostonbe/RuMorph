// Shared translations with the server (apps/api, translations.py). The device keeps its copy in
// admin_translations: rows from the server and the admin's own edits.
//
// Push (admin accounts only): edits in the outbox go up; for each word the later updated_at wins,
// and when the server's entry wins it comes back and is written here.
// Pull (no account needed): entries changed since the saved cursor come down and replace older
// local rows.
import { translationStore, uuidv7, type AdminTranslationRow, type Example } from "../data/userData";

export interface WireTranslation {
  lexeme_id: string;
  lemma: string;
  translation: string;
  updated_at: string;
  deleted_at: string | null;
  /** Missing from servers older than migration 0004. */
  examples?: Example[];
  verified?: boolean;
}

export interface TranslationPushResult {
  accepted: string[];
  conflicts: WireTranslation[];
  rejected: { lexeme_id: string; code: string }[];
}

export interface TranslationPullResult {
  changes: WireTranslation[];
  cursor: number;
  more: boolean;
}

export interface TranslationApi {
  push(changes: WireTranslation[]): Promise<TranslationPushResult>;
  pull(since: number): Promise<TranslationPullResult>;
}

export const MAX_PUSH = 200;
const MAX_ROUNDS = 200;

/** One time format everywhere, so that dates also compare correctly as text (mergeTranslations). */
const iso = (value: string): string => new Date(value).toISOString();

export function toWire(row: AdminTranslationRow): WireTranslation {
  return {
    lexeme_id: row.lexeme_id,
    lemma: row.lemma.trim(),
    translation: row.translation.trim(),
    updated_at: iso(row.updated_at),
    deleted_at: row.deleted_at ? iso(row.deleted_at) : null,
    examples: (row.examples ?? []).map((e) => ({ ru: e.ru.trim(), uz: e.uz.trim() })).filter((e) => e.ru && e.uz).slice(0, 3),
    verified: row.verified ?? true,
  };
}

/** Writes server entries that are newer than the local row. Returns how many rows changed. */
export async function applyRemoteTranslations(entries: WireTranslation[]): Promise<number> {
  if (!entries.length) return 0;
  const byLexeme = new Map((await translationStore.all()).map((r) => [r.lexeme_id, r]));
  let written = 0;
  for (const e of entries) {
    const local = byLexeme.get(e.lexeme_id);
    if (local && Date.parse(local.updated_at) >= Date.parse(e.updated_at)) continue;
    const fields = {
      lemma: e.lemma,
      translation: e.translation,
      updated_at: iso(e.updated_at),
      deleted_at: e.deleted_at ? iso(e.deleted_at) : null,
      examples: e.examples ?? [],
      verified: e.verified ?? true,
    };
    const row: AdminTranslationRow = local
      ? { ...local, ...fields, version: local.version + 1 }
      : { id: uuidv7(), lexeme_id: e.lexeme_id, created_at: fields.updated_at, version: 1, ...fields };
    await translationStore.putRemote(row);
    // A local edit older than this entry is no longer worth sending.
    await translationStore.ack(row.id, row.version);
    byLexeme.set(row.lexeme_id, row);
    written++;
  }
  return written;
}

export interface TranslationPushOutcome {
  pushed: number;
  rejected: number;
  rejectedCodes: string[];
  changed: boolean;
}

/** Sends every queued edit. Throws the API's error (for example not_admin) and keeps the queue then. */
export async function pushTranslations(api: TranslationApi): Promise<TranslationPushOutcome> {
  const outcome: TranslationPushOutcome = { pushed: 0, rejected: 0, rejectedCodes: [], changed: false };
  for (let round = 0; round < MAX_ROUNDS; round++) {
    const entries = await translationStore.pending(MAX_PUSH);
    if (!entries.length) break;
    const rows = new Map((await translationStore.byIds(entries.map((e) => e.id))).map((r) => [r.id, r]));
    const sent: AdminTranslationRow[] = [];
    for (const e of entries) {
      const row = rows.get(e.id);
      if (row) sent.push(row);
      else await translationStore.ack(e.id, Number.MAX_SAFE_INTEGER);
    }
    if (!sent.length) continue;
    const result = await api.push(sent.map(toWire));
    for (const row of sent) await translationStore.ack(row.id, row.version);
    outcome.pushed += result.accepted.length;
    if (await applyRemoteTranslations(result.conflicts)) outcome.changed = true;
    outcome.rejected += result.rejected.length;
    for (const r of result.rejected) if (!outcome.rejectedCodes.includes(r.code)) outcome.rejectedCodes.push(r.code);
  }
  return outcome;
}

/** Brings every entry changed since `cursor`. Returns the new cursor and whether rows changed. */
export async function pullTranslations(
  api: TranslationApi, cursor: number, saveCursor: (c: number) => Promise<void>,
): Promise<{ cursor: number; changed: boolean }> {
  let changed = false;
  for (let round = 0; round < MAX_ROUNDS; round++) {
    const page = await api.pull(cursor);
    if (await applyRemoteTranslations(page.changes)) changed = true;
    if (page.cursor !== cursor) {
      cursor = page.cursor;
      await saveCursor(cursor);
    }
    if (!page.more) break;
  }
  return { cursor, changed };
}

/** Local edits made before the server had translations: queued once. */
export async function queueExisting(): Promise<number> {
  const rows = await translationStore.all();
  await translationStore.mark(rows);
  return rows.length;
}

