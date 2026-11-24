// The sync engine (src/sync/engine.ts) against an in-memory server that follows the same rule as
// apps/api (sync.py): the higher (version, updated_at) is kept; a pull returns rows by sequence.
import { beforeEach, describe, expect, it, vi } from "vitest";

const storage = new Map<string, string>();
vi.stubGlobal("localStorage", {
  getItem: (k: string) => storage.get(k) ?? null,
  setItem: (k: string, v: string) => void storage.set(k, v),
});

const { vocabulary, flashcards, syncStore, onLocalChange } = await import("../src/data/userData");
const { syncOnce, isNewer, MAX_ROWS } = await import("../src/sync/engine");
type BaseRow = import("../src/data/userData").BaseRow;
type Change = import("../src/sync/engine").Change;
type SyncApi = import("../src/sync/engine").SyncApi;

class FakeServer implements SyncApi {
  rows = new Map<string, { table: string; row: BaseRow; seq: number }>();
  seq = 0;
  pushes = 0;
  pageSize = 500;
  refuse = new Set<string>();

  put(table: string, row: BaseRow): void {
    this.rows.set(`${table}/${row.id}`, { table, row: structuredClone(row), seq: ++this.seq });
  }

  async push(changes: Change[]) {
    this.pushes++;
    const result = { accepted: [] as { table: string; id: string }[], conflicts: [] as { table: string; row: BaseRow }[],
      rejected: [] as { table: string; id: string; code: string }[] };
    for (const { table, row } of changes) {
      if (this.refuse.has(row.id)) {
        result.rejected.push({ table, id: row.id, code: "invalid_note" });
        continue;
      }
      const stored = this.rows.get(`${table}/${row.id}`);
      if (!stored || isNewer(row, stored.row)) {
        this.put(table, row);
        result.accepted.push({ table, id: row.id });
      } else {
        result.conflicts.push({ table, row: structuredClone(stored.row) });
      }
    }
    return result;
  }

  async pull(since: number) {
    const all = [...this.rows.values()].filter((r) => r.seq > since).sort((a, b) => a.seq - b.seq);
    const page = all.slice(0, this.pageSize);
    return {
      changes: page.map((r) => ({ table: r.table, row: structuredClone(r.row) })),
      cursor: page.length ? page[page.length - 1]!.seq : since,
      more: all.length > page.length,
    };
  }
}

const T0 = "2026-11-20T09:00:00.000Z";

function word(id: string, lexeme: string, extra: Partial<Record<string, unknown>> = {}): BaseRow {
  return {
    id, created_at: T0, updated_at: T0, deleted_at: null, version: 1, lexeme_id: lexeme, lemma: lexeme, pos: "NOUN",
    translation: "", note: "", examples: [], status: "learning", ...extra,
  } as unknown as BaseRow;
}

const newWord = (lexeme: string) =>
  vocabulary.insert({ lexeme_id: lexeme, lemma: lexeme, pos: "NOUN", translation: "", note: "", examples: [], status: "learning" });

let cursor = 0;
const save = async (c: number) => void (cursor = c);

beforeEach(async () => {
  storage.clear();
  await syncStore.wipe(); // the browser backend also keeps the tables in memory
  cursor = 0;
});

describe("outbox", () => {
  it("queues every local change of a synced table, once per row", async () => {
    const seen = vi.fn();
    const stop = onLocalChange(seen);
    const row = await newWord("a");
    await vocabulary.update(row, { note: "x" });
    stop();
    expect(seen).toHaveBeenCalledTimes(2);
    expect(await syncStore.outboxList(10)).toEqual([{ tbl: "user_vocabulary", id: row.id, version: 2 }]);
  });

  it("markAll queues rows written before the device had an account", async () => {
    const a = await newWord("a");
    await syncStore.outboxAck("user_vocabulary", a.id, 99);
    expect(await syncStore.outboxCount()).toBe(0);
    await syncStore.markAll();
    expect(await syncStore.outboxCount()).toBe(1);
  });

  it("wipe removes the learner's rows and the outbox", async () => {
    await newWord("a");
    await syncStore.wipe();
    expect(await vocabulary.listAll()).toEqual([]);
    expect(await syncStore.outboxCount()).toBe(0);
  });
});

describe("syncOnce", () => {
  it("sends local changes, empties the outbox and keeps the cursor", async () => {
    const server = new FakeServer();
    const row = await newWord("a");
    const outcome = await syncOnce(server, cursor, save);
    expect(outcome.pushed).toBe(1);
    expect(await syncStore.outboxCount()).toBe(0);
    expect(server.rows.get(`user_vocabulary/${row.id}`)?.row).toEqual(row);
    // The pull brings the device's own row back; it changes nothing here.
    expect(outcome.changed).toBe(false);
    expect(cursor).toBe(server.seq);
  });

  it("brings rows made on another device and reports the change", async () => {
    const server = new FakeServer();
    server.put("user_vocabulary", word("018f0000-0000-7000-8000-000000000001", "b"));
    const outcome = await syncOnce(server, cursor, save);
    expect(outcome.changed).toBe(true);
    expect((await vocabulary.list()).map((r) => r.lexeme_id)).toEqual(["b"]);
    expect(await syncStore.outboxCount()).toBe(0);
  });

  it("a newer server row replaces the local one; an older one is ignored", async () => {
    const server = new FakeServer();
    const row = await newWord("a");
    await syncOnce(server, cursor, save);

    server.put("user_vocabulary", { ...row, version: 5, updated_at: "2026-11-21T00:00:00Z", note: "phone" } as BaseRow);
    await syncOnce(server, cursor, save);
    expect((await vocabulary.list())[0]!.note).toBe("phone");

    server.put("user_vocabulary", { ...row, version: 2, note: "stale" } as BaseRow);
    await syncOnce(server, cursor, save);
    expect((await vocabulary.list())[0]!.note).toBe("phone");
  });

  it("takes the server's row when the server already has a newer one", async () => {
    const server = new FakeServer();
    const row = await newWord("a");
    server.put("user_vocabulary", { ...row, version: 3, note: "server" } as BaseRow);
    cursor = server.seq; // skip the pull, so only the answer to the push can bring the newer row
    const outcome = await syncOnce(server, cursor, save);
    expect(outcome.pushed).toBe(0);
    expect(outcome.changed).toBe(true);
    expect((await vocabulary.list())[0]!.note).toBe("server");
  });

  it("the same word made on two devices: both keep the smaller id", async () => {
    const server = new FakeServer();
    const mine = await newWord("книга");
    const smaller = "00000000-0000-7000-8000-000000000001";
    const larger = "ffffffff-ffff-7fff-bfff-ffffffffffff";

    // Another device made the word first (smaller id): the local row is marked deleted and sent.
    server.put("user_vocabulary", word(smaller, "книга"));
    await syncOnce(server, cursor, save);
    expect((await vocabulary.list()).map((r) => r.id)).toEqual([smaller]);
    const loser = (await vocabulary.listAll()).find((r) => r.id === mine.id)!;
    expect(loser.deleted_at).not.toBeNull();
    await syncOnce(server, cursor, save);
    expect(server.rows.get(`user_vocabulary/${mine.id}`)?.row.deleted_at).not.toBeNull();

    // A later copy (larger id) from yet another device loses: it is stored deleted and sent back so.
    server.put("user_vocabulary", word(larger, "книга"));
    await syncOnce(server, cursor, save);
    expect((await vocabulary.list()).map((r) => r.id)).toEqual([smaller]);
    await syncOnce(server, cursor, save);
    expect(server.rows.get(`user_vocabulary/${larger}`)?.row.deleted_at).not.toBeNull();
  });

  it("flashcards are unique per word and direction", async () => {
    const server = new FakeServer();
    await flashcards.insert({
      lexeme_id: "a", direction: "ru_uz", due_at: T0, interval_days: 0, ease: 2.5, reps: 0, lapses: 0, last_review_at: null,
    });
    const other = {
      id: "00000000-0000-7000-8000-000000000002", created_at: T0, updated_at: T0, deleted_at: null, version: 1,
      lexeme_id: "a", direction: "uz_ru", due_at: T0, interval_days: 0, ease: 2.5, reps: 0, lapses: 0, last_review_at: null,
    } as unknown as BaseRow;
    server.put("flashcards", other);
    await syncOnce(server, cursor, save);
    expect((await flashcards.list()).map((c) => c.direction).sort()).toEqual(["ru_uz", "uz_ru"]);
  });

  it("sends in batches and follows pull pages", async () => {
    const server = new FakeServer();
    server.pageSize = 40;
    for (let i = 0; i < MAX_ROWS * 2 + 5; i++) await newWord(`w${i}`);
    const outcome = await syncOnce(server, cursor, save);
    expect(server.pushes).toBe(3);
    expect(outcome.pushed).toBe(MAX_ROWS * 2 + 5);
    expect(outcome.pulled).toBe(MAX_ROWS * 2 + 5);
    expect(cursor).toBe(server.seq);
  });

  it("refused rows are counted and leave the outbox", async () => {
    const server = new FakeServer();
    const bad = await newWord("bad");
    await newWord("good");
    server.refuse.add(bad.id);
    const outcome = await syncOnce(server, cursor, save);
    expect(outcome.rejected).toBe(1);
    expect(outcome.rejectedCodes).toEqual(["invalid_note"]);
    expect(await syncStore.outboxCount()).toBe(0);
  });

  it("a change made while a push is on the way stays queued", async () => {
    const server = new FakeServer();
    const row = await newWord("a");
    const push = server.push.bind(server);
    let changed = false;
    server.push = async (changes) => {
      const result = await push(changes);
      if (!changed) {
        changed = true;
        const live = (await vocabulary.list())[0]!;
        await vocabulary.update(live, { note: "typed meanwhile" });
      }
      return result;
    };
    await syncOnce(server, cursor, save);
    // The second round sent the newer version.
    expect(server.rows.get(`user_vocabulary/${row.id}`)?.row.version).toBe(2);
    expect(await syncStore.outboxCount()).toBe(0);
  });
});
