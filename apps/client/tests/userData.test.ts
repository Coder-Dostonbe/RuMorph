// The learner's data layer (src/data/userData.ts) with its browser backend, which keeps the same
// rules as the SQLite one: ids are UUID v7, rows are marked deleted rather than removed, and every
// change raises version.
import { beforeEach, describe, expect, it, vi } from "vitest";

const storage = new Map<string, string>();
vi.stubGlobal("localStorage", {
  getItem: (k: string) => storage.get(k) ?? null,
  setItem: (k: string, v: string) => void storage.set(k, v),
});

const { uuidv7, vocabulary, storageKind } = await import("../src/data/userData");

describe("uuidv7", () => {
  it("has the version and variant bits and sorts by time", () => {
    const a = uuidv7(1_700_000_000_000);
    const b = uuidv7(1_700_000_000_001);
    expect(a).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(a < b).toBe(true);
    expect(uuidv7()).not.toBe(uuidv7());
  });
});

describe("tables (browser backend)", () => {
  beforeEach(() => storage.clear());

  it("runs on the browser backend outside the app", () => {
    expect(storageKind).toBe("browser");
  });

  it("inserts, updates and marks rows deleted", async () => {
    const row = await vocabulary.insert({
      lexeme_id: "книга|NOUN,inan,femn", lemma: "книга", pos: "NOUN", translation: "kitob", note: "",
      examples: [{ ru: "Это книга.", uz: "Bu kitob." }], status: "learning",
    });
    expect(row.version).toBe(1);
    expect(row.deleted_at).toBeNull();
    const updated = await vocabulary.update(row, { status: "known" });
    expect(updated.version).toBe(2);
    expect((await vocabulary.list()).map((r) => r.status)).toEqual(["known"]);
    await vocabulary.remove(updated);
    expect(await vocabulary.list()).toEqual([]);
    // The deleted row is still stored (for sync), with its deletion time.
    const stored = JSON.parse(storage.get("tilsim.table.user_vocabulary") ?? "[]");
    expect(stored).toHaveLength(1);
    expect(stored[0].deleted_at).toBeTruthy();
    expect(stored[0].version).toBe(3);
  });
});
