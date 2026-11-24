// Sync of the learner's tables with the account on the server (apps/api, sync.py).
//
// 1. Push: rows in the outbox go up in batches. The server keeps the higher
//    (version, updated_at); when its own row wins, it sends that row back and it is written here.
// 2. Pull: rows changed on the server since the saved cursor come down and are written here
//    when they are newer than the local row.
//
// The same word or card can be made on two devices before they sync (two ids, one lexeme).
// Both devices then keep the row with the smaller id and mark the other deleted, so they end
// up with the same rows without asking the user.
import { isSynced, nowIso, syncStore, type BaseRow, type SyncedTable } from "../data/userData";

export interface Change {
  table: SyncedTable;
  row: BaseRow;
}

export interface PushResult {
  accepted: { table: string; id: string }[];
  conflicts: { table: string; row: BaseRow }[];
  rejected: { table: string; id: string; code: string }[];
}

export interface PullResult {
  changes: { table: string; row: BaseRow }[];
  cursor: number;
  more: boolean;
}

export interface SyncApi {
  push(changes: Change[]): Promise<PushResult>;
  pull(since: number): Promise<PullResult>;
}

export interface SyncOutcome {
  pushed: number;
  pulled: number;
  /** Rows the server refused (their codes are in `rejectedCodes`). */
  rejected: number;
  rejectedCodes: string[];
  /** Whether rows on this device changed, so the screens must reload. */
  changed: boolean;
  cursor: number;
}

export const MAX_ROWS = 100;
/** Characters of JSON per push; the server takes up to 1 MB. */
export const MAX_CHARS = 400_000;
const MAX_ROUNDS = 200;

/** a is newer than b: a higher version, or the same version changed later. */
export function isNewer(a: BaseRow, b: BaseRow): boolean {
  if (a.version !== b.version) return a.version > b.version;
  return Date.parse(a.updated_at) > Date.parse(b.updated_at);
}

/** The key that must be unique among live rows (the unique indexes of 0002_learning.sql). */
export function naturalKey(table: SyncedTable, row: BaseRow): string | null {
  const r = row as unknown as Record<string, unknown>;
  if (table === "user_vocabulary") return String(r.lexeme_id);
  if (table === "flashcards") return `${String(r.lexeme_id)}#${String(r.direction)}`;
  return null;
}

function deleted<R extends BaseRow>(row: R): R {
  const at = nowIso();
  return { ...row, deleted_at: at, updated_at: at, version: row.version + 1 };
}

/** Writes rows that came from the server. Returns how many changed this device. */
export async function applyRemote(changes: { table: string; row: BaseRow }[]): Promise<number> {
  const byTable = new Map<SyncedTable, BaseRow[]>();
  for (const c of changes) {
    if (!isSynced(c.table)) continue;
    byTable.set(c.table, [...(byTable.get(c.table) ?? []), c.row]);
  }
  let written = 0;
  for (const [table, incoming] of byTable) {
    const local = await syncStore.all(table);
    const byId = new Map(local.map((r) => [r.id, r]));
    const liveByKey = new Map<string, BaseRow>();
    for (const r of local) {
      const key = naturalKey(table, r);
      if (key !== null && !r.deleted_at) liveByKey.set(key, r);
    }
    for (let row of incoming) {
      const mine = byId.get(row.id);
      if (mine && !isNewer(row, mine)) continue;

      const key = naturalKey(table, row);
      const other = key !== null && !row.deleted_at ? liveByKey.get(key) : undefined;
      if (other && other.id !== row.id) {
        if (row.id < other.id) {
          const loser = deleted(other);
          await syncStore.putLocal(table, loser);
          byId.set(loser.id, loser);
        } else {
          row = deleted(row);
          await syncStore.putLocal(table, row);
          byId.set(row.id, row);
          written++;
          continue;
        }
      }

      await syncStore.putRemote(table, row);
      // A local change this row replaces is no longer worth sending.
      await syncStore.outboxAck(table, row.id, row.version);
      byId.set(row.id, row);
      if (key !== null) {
        if (row.deleted_at) {
          if (liveByKey.get(key)?.id === row.id) liveByKey.delete(key);
        } else {
          liveByKey.set(key, row);
        }
      }
      written++;
    }
  }
  return written;
}

/** The next batch from the outbox, within the row and size limits. Entries whose row is gone are dropped. */
async function nextBatch(): Promise<Change[]> {
  const entries = await syncStore.outboxList(MAX_ROWS);
  const batch: Change[] = [];
  let chars = 0;
  const byTable = new Map<SyncedTable, string[]>();
  for (const e of entries) if (isSynced(e.tbl)) byTable.set(e.tbl, [...(byTable.get(e.tbl) ?? []), e.id]);
  for (const [table, ids] of byTable) {
    const rows = new Map((await syncStore.byIds(table, ids)).map((r) => [r.id, r]));
    for (const id of ids) {
      const row = rows.get(id);
      if (!row) {
        await syncStore.outboxAck(table, id, Number.MAX_SAFE_INTEGER);
        continue;
      }
      const size = JSON.stringify(row).length;
      if (batch.length && chars + size > MAX_CHARS) return batch;
      batch.push({ table, row });
      chars += size;
    }
  }
  return batch;
}

/** One full sync: push everything queued, then pull everything new. */
export async function syncOnce(api: SyncApi, cursor: number, saveCursor: (c: number) => Promise<void>): Promise<SyncOutcome> {
  const outcome: SyncOutcome = { pushed: 0, pulled: 0, rejected: 0, rejectedCodes: [], changed: false, cursor };

  for (let round = 0; round < MAX_ROUNDS; round++) {
    const batch = await nextBatch();
    if (!batch.length) break;
    const result = await api.push(batch);
    // Every row sent is settled: accepted, answered with the server's row, or refused.
    for (const { table, row } of batch) await syncStore.outboxAck(table, row.id, row.version);
    outcome.pushed += result.accepted.length;
    if (result.conflicts.length && (await applyRemote(result.conflicts))) outcome.changed = true;
    outcome.rejected += result.rejected.length;
    for (const r of result.rejected) if (!outcome.rejectedCodes.includes(r.code)) outcome.rejectedCodes.push(r.code);
  }

  for (let round = 0; round < MAX_ROUNDS; round++) {
    const page = await api.pull(outcome.cursor);
    if (page.changes.length && (await applyRemote(page.changes))) outcome.changed = true;
    outcome.pulled += page.changes.length;
    if (page.cursor !== outcome.cursor) {
      outcome.cursor = page.cursor;
      await saveCursor(page.cursor);
    }
    if (!page.more) break;
  }
  return outcome;
}
