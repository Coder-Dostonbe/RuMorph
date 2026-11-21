// The temporary admin mode (src/stores/admin.ts, src/admin/password.ts) and the translations it
// writes (src/stores/translations.ts), on the browser backends used outside the app.
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const storage = new Map<string, string>();
vi.stubGlobal("localStorage", {
  getItem: (k: string) => storage.get(k) ?? null,
  setItem: (k: string, v: string) => void storage.set(k, v),
});

const { hashPassword, parseRecord, verifyPassword } = await import("../src/admin/password");
const { useAdmin } = await import("../src/stores/admin");
const { mergeTranslations, toFile, useTranslations } = await import("../src/stores/translations");
const { vocabulary } = await import("../src/data/userData");
const { visibleNav } = await import("../src/app/nav");

const row = (lexeme_id: string, translation: string, updated_at: string, deleted_at: string | null = null) => ({
  id: lexeme_id, lexeme_id, lemma: lexeme_id.split("|")[0]!, translation, created_at: updated_at, updated_at, deleted_at, version: 1,
});
const shipped = (lexeme_id: string, translation: string, updated_at: string) => ({ lexeme_id, lemma: lexeme_id.split("|")[0]!, translation, updated_at });

describe("admin password", () => {
  it("keeps only a salted hash and checks it", async () => {
    const record = await hashPassword("tilsim-123", 1000);
    expect(JSON.stringify(record)).not.toContain("tilsim-123");
    expect(await verifyPassword("tilsim-123", record)).toBe(true);
    expect(await verifyPassword("tilsim-124", record)).toBe(false);
    const again = await hashPassword("tilsim-123", 1000);
    expect(again.salt).not.toBe(record.salt);
    expect(again.hash).not.toBe(record.hash);
  });

  it("treats an unreadable record as none", () => {
    expect(parseRecord(null)).toBeNull();
    expect(parseRecord("{")).toBeNull();
    expect(parseRecord(JSON.stringify({ alg: "md5", iterations: 1, salt: "", hash: "" }))).toBeNull();
  });
});

describe("admin mode", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("is set up once, then unlocks only with the password and locks again", async () => {
    const admin = useAdmin();
    await admin.load();
    expect(admin.configured).toBe(false);
    expect(await admin.create("12345", "12345")).toBe("too_short");
    expect(await admin.create("secret-1", "secret-2")).toBe("mismatch");
    expect(await admin.create("secret-1", "secret-1")).toBe("ok");
    expect(admin.unlocked).toBe(true);
    // A second setup cannot replace the password.
    expect(await admin.create("other-pass", "other-pass")).toBe("wrong");
    admin.lock();
    expect(admin.unlocked).toBe(false);
    expect(await admin.unlock("wrong-pass")).toBe("wrong");
    expect(await admin.unlock("secret-1")).toBe("ok");
    expect(await admin.change("wrong-pass", "secret-2", "secret-2")).toBe("wrong");
    expect(await admin.change("secret-1", "secret-2", "secret-2")).toBe("ok");
    admin.lock();
    expect(await admin.unlock("secret-1")).toBe("wrong");
    expect(await admin.unlock("secret-2")).toBe("ok");
  });

  it("waits after five wrong passwords", async () => {
    const admin = useAdmin();
    await admin.load();
    const results = [];
    for (let i = 0; i < 5; i++) results.push(await admin.unlock(`nope-${i}`));
    expect(results.slice(0, 4)).toEqual(["wrong", "wrong", "wrong", "wrong"]);
    expect(results[4]).toBe("locked_out");
    expect(await admin.unlock("secret-2")).toBe("locked_out");
  });

  it("hides the admin menu items while locked", () => {
    const locked = visibleNav(false).map((i) => i.to);
    expect(locked).not.toContain("/admin");
    expect(locked).not.toContain("/account");
    expect(visibleNav(true).map((i) => i.to)).toEqual(expect.arrayContaining(["/admin", "/account"]));
  });
});

describe("translations", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("takes the newer of the shipped and the local entry", () => {
    const merged = mergeTranslations(
      [shipped("a|X", "eski", "2026-01-01"), shipped("b|X", "yangi", "2026-03-01"), shipped("c|X", "bor", "2026-01-01")],
      [row("a|X", "yangiroq", "2026-02-01"), row("b|X", "eskiroq", "2026-02-01"), row("c|X", "", "2026-02-01", "2026-02-01"), row("d|X", "faqat shu yerda", "2026-02-01")],
    );
    expect(merged.get("a|X")?.translation).toBe("yangiroq");
    expect(merged.get("b|X")?.translation).toBe("yangi");
    expect(merged.has("c|X")).toBe(false);
    expect(merged.get("d|X")?.translation).toBe("faqat shu yerda");
  });

  it("exports every translation and the removals made on the device", () => {
    const local = [row("c|X", "", "2026-02-01", "2026-02-01"), row("e|X", "uy", "2026-02-01")];
    const file = toFile(mergeTranslations([shipped("c|X", "bor", "2026-01-01")], local).values(), local, "2026-02-02");
    expect(file.format).toBe("tilsim-translations");
    expect(file.translations.map((e) => e.lexeme_id)).toEqual(["e|X"]);
    expect(file.removed).toEqual([{ lexeme_id: "c|X", updated_at: "2026-02-01" }]);
  });

  it("are written only in the admin mode, and the learner's old translations move over once", async () => {
    await vocabulary.insert({ lexeme_id: "книга|NOUN,inan,femn", lemma: "книга", pos: "NOUN", translation: "kitob", note: "", examples: [], status: "learning" });
    const tr = useTranslations();
    await tr.load();
    expect(tr.get("книга|NOUN,inan,femn")).toBe("kitob");

    const word = { id: "дом|NOUN,inan,masc", lemma: "дом" };
    await expect(tr.set(word, "uy")).rejects.toThrow();
    expect(tr.get(word.id)).toBeNull();
  });
});

describe("translations (admin unlocked)", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("sets, corrects and removes a translation", async () => {
    expect(await useAdmin().unlock("secret-2")).toBe("ok");
    const tr = useTranslations();
    await tr.load();
    const word = { id: "дом|NOUN,inan,masc", lemma: "дом" };
    await tr.set(word, "  uy  ");
    expect(tr.get(word.id)).toBe("uy");
    await tr.set(word, "uy, bino");
    expect(tr.get(word.id)).toBe("uy, bino");
    await tr.set(word, "");
    expect(tr.get(word.id)).toBeNull();
    // Already moved over: loading again (a new start of the app) does not add the old one twice.
    setActivePinia(createPinia());
    const again = useTranslations();
    await again.load();
    expect(again.get("книга|NOUN,inan,femn")).toBe("kitob");
    expect(again.get(word.id)).toBeNull();
    const stored = JSON.parse(storage.get("tilsim.table.admin_translations") ?? "[]") as { lexeme_id: string }[];
    expect(stored.filter((r) => r.lexeme_id === "книга|NOUN,inan,femn")).toHaveLength(1);
    expect(JSON.parse(again.exportText()).removed).toEqual([expect.objectContaining({ lexeme_id: word.id })]);
  });
});
