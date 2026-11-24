// Shared translations (src/sync/translations.ts) against an in-memory server with the API's rule:
// for each word the later updated_at wins.
import { beforeEach, describe, expect, it, vi } from "vitest";

const storage = new Map<string, string>();
vi.stubGlobal("localStorage", {
  getItem: (k: string) => storage.get(k) ?? null,
  setItem: (k: string, v: string) => void storage.set(k, v),
});

const { adminTranslations, translationStore } = await import("../src/data/userData");
const { pushTranslations, pullTranslations, applyRemoteTranslations, queueExisting, toWire } = await import("../src/sync/translations");
const { mergeTranslations } = await import("../src/stores/translations");
type Wire = import("../src/sync/translations").WireTranslation;
type Api = import("../src/sync/translations").TranslationApi;

class FakeServer implements Api {
  rows = new Map<string, { entry: Wire; seq: number }>();
  seq = 0;
  admin = true;

  put(entry: Wire): void {
    this.rows.set(entry.lexeme_id, { entry: { ...entry }, seq: ++this.seq });
  }

  async push(changes: Wire[]) {
    if (!this.admin) throw Object.assign(new Error("not admin"), { code: "not_admin" });
    const result = { accepted: [] as string[], conflicts: [] as Wire[], rejected: [] as { lexeme_id: string; code: string }[] };
    for (const e of changes) {
      if (!e.deleted_at && !e.translation) {
        result.rejected.push({ lexeme_id: e.lexeme_id, code: "invalid_translation" });
        continue;
      }
      const stored = this.rows.get(e.lexeme_id);
      if (!stored || Date.parse(e.updated_at) > Date.parse(stored.entry.updated_at)) {
        this.put(e);
        result.accepted.push(e.lexeme_id);
      } else {
        result.conflicts.push({ ...stored.entry, updated_at: stored.entry.updated_at.replace("Z", "+00:00") });
      }
    }
    return result;
  }

  async pull(since: number) {
    const page = [...this.rows.values()].filter((r) => r.seq > since).sort((a, b) => a.seq - b.seq);
    // The server writes times as +00:00, the app as Z: both must work.
    return {
      changes: page.map((r) => ({ ...r.entry, updated_at: r.entry.updated_at.replace("Z", "+00:00") })),
      cursor: page.length ? page[page.length - 1]!.seq : since,
      more: false,
    };
  }
}

const wire = (lexeme: string, translation: string, updated_at: string, deleted_at: string | null = null): Wire =>
  ({ lexeme_id: lexeme, lemma: lexeme, translation, updated_at, deleted_at });

let cursor = 0;
const save = async (c: number) => void (cursor = c);

async function reset(): Promise<void> {
  storage.clear();
  cursor = 0;
  for (const row of await adminTranslations.listAll()) {
    await translationStore.ack(row.id, Number.MAX_SAFE_INTEGER);
  }
}

beforeEach(reset);

describe("shared translations", () => {
  it("learners get the server's translations without an account and keep them", async () => {
    const server = new FakeServer();
    server.put(wire("книга", "kitob", "2026-11-20T09:00:00.000Z"));
    const result = await pullTranslations(server, cursor, save);
    expect(result.changed).toBe(true);
    const merged = mergeTranslations([], await adminTranslations.listAll());
    expect(merged.get("книга")?.translation).toBe("kitob");
    expect(cursor).toBe(server.seq);
    // Pulled rows are not sent back.
    expect(await translationStore.count()).toBe(0);
  });

  it("the admin's edit goes up and its queue empties", async () => {
    const server = new FakeServer();
    const row = await adminTranslations.insert({ lexeme_id: "дом", lemma: "дом", translation: "uy", examples: [], verified: true });
    await translationStore.mark([row]);
    const outcome = await pushTranslations(server);
    expect(outcome.pushed).toBe(1);
    expect(server.rows.get("дом")?.entry).toEqual(toWire(row));
    expect(await translationStore.count()).toBe(0);
  });

  it("without an admin account the edit stays queued", async () => {
    const server = new FakeServer();
    server.admin = false;
    const row = await adminTranslations.insert({ lexeme_id: "сад", lemma: "сад", translation: "bog'", examples: [], verified: true });
    await translationStore.mark([row]);
    await expect(pushTranslations(server)).rejects.toMatchObject({ code: "not_admin" });
    expect(await translationStore.count()).toBe(1);
  });

  it("a later server entry replaces a local one, an earlier one does not", async () => {
    const server = new FakeServer();
    const row = await adminTranslations.insert({ lexeme_id: "кот", lemma: "кот", translation: "mushuk", examples: [], verified: true });
    server.put(wire("кот", "eski", "2020-01-01T00:00:00.000Z"));
    await pullTranslations(server, cursor, save);
    expect((await adminTranslations.listAll()).find((r) => r.id === row.id)?.translation).toBe("mushuk");

    server.put(wire("кот", "mushuk, pishak", "2099-01-01T00:00:00.000Z"));
    await pullTranslations(server, cursor, save);
    const rows = (await adminTranslations.listAll()).filter((r) => r.lexeme_id === "кот");
    expect(rows.map((r) => r.translation)).toEqual(["mushuk, pishak"]);
    expect(rows[0]!.updated_at).toBe("2099-01-01T00:00:00.000Z");
  });

  it("an older local edit is answered with the server's entry", async () => {
    const server = new FakeServer();
    server.put(wire("лес", "o'rmon", "2099-01-01T00:00:00.000Z"));
    const row = await adminTranslations.insert({ lexeme_id: "лес", lemma: "лес", translation: "daraxtzor", examples: [], verified: true });
    await translationStore.mark([row]);
    const outcome = await pushTranslations(server);
    expect(outcome.pushed).toBe(0);
    expect(outcome.changed).toBe(true);
    expect((await adminTranslations.listAll()).find((r) => r.lexeme_id === "лес")?.translation).toBe("o'rmon");
  });

  it("a removal reaches the other devices", async () => {
    const server = new FakeServer();
    server.put(wire("река", "daryo", "2026-11-20T09:00:00.000Z"));
    await pullTranslations(server, cursor, save);
    server.put(wire("река", "daryo", "2026-11-21T09:00:00.000Z", "2026-11-21T09:00:00.000Z"));
    await pullTranslations(server, cursor, save);
    expect(mergeTranslations([], await adminTranslations.listAll()).has("река")).toBe(false);
  });

  it("refused entries are counted and leave the queue", async () => {
    const server = new FakeServer();
    const row = await adminTranslations.insert({ lexeme_id: "x", lemma: "x", translation: "", examples: [], verified: true });
    await translationStore.mark([row]);
    const outcome = await pushTranslations(server);
    expect(outcome.rejected).toBe(1);
    expect(await translationStore.count()).toBe(0);
  });

  it("edits made before the server are queued once", async () => {
    await adminTranslations.insert({ lexeme_id: "a", lemma: "a", translation: "a", examples: [], verified: true });
    await adminTranslations.insert({ lexeme_id: "b", lemma: "b", translation: "b", examples: [], verified: true });
    await queueExisting();
    expect(await translationStore.count()).toBeGreaterThanOrEqual(2);
  });

  it("server times are stored in the app's format", async () => {
    await applyRemoteTranslations([wire("дождь", "yomg'ir", "2026-11-20T09:00:00.123+00:00")]);
    const row = (await adminTranslations.listAll()).find((r) => r.lexeme_id === "дождь")!;
    expect(row.updated_at).toBe("2026-11-20T09:00:00.123Z");
  });
});
