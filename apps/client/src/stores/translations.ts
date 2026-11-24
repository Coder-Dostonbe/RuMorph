import { invoke } from "@tauri-apps/api/core";
import { defineStore } from "pinia";
import { computed, ref, shallowRef, watch } from "vue";
import { inTauri, platform } from "../app/platform";
import { keyValue } from "../data/keyValue";
import { copyText } from "../ui/clipboard";
import { adminTranslations, translationStore, vocabulary, type AdminTranslationRow, type Example } from "../data/userData";
import { ApiError, request } from "../api/http";
import {
  pullTranslations, pushTranslations, queueExisting,
  type TranslationApi, type TranslationPullResult, type TranslationPushResult, type WireTranslation,
} from "../sync/translations";
import { useAdmin } from "./admin";
import { useSession } from "./session";
import { useSettings } from "./settings";

/** One translation as shipped with the app and as exported from the admin panel. */
export interface TranslationEntry {
  lexeme_id: string;
  lemma: string;
  translation: string;
  updated_at: string;
  /** Example sentences, Russian with the Uzbek translation (file version 2). */
  examples?: Example[];
  /** false: a draft nobody has checked yet; the learner sees a "not checked" mark. Default true. */
  verified?: boolean;
}

export interface TranslationFile {
  format: "tilsim-translations";
  version: 1 | 2;
  exported_at?: string;
  translations: TranslationEntry[];
  /** Words whose translation the admin removed on the exporting device. */
  removed?: { lexeme_id: string; updated_at: string }[];
}

export const MAX_TRANSLATION = 200;
const MIGRATED_KEY = "translations_migrated";
const QUEUED_KEY = "translations.queued_for_server";
const CURSOR_KEY = "translations.cursor";
const LAST_KEY = "translations.last_at";
const EVERY_MS = 30 * 60_000;
const AFTER_EDIT_MS = 3_000;

/**
 * The state of the shared translations on this device:
 * ok (up to date), offline, failed, or the edits that wait for an admin account
 * (signed_out: nobody is signed in; not_admin: the account is not an admin).
 */
export type TranslationSyncState = "idle" | "syncing" | "ok" | "offline" | "failed" | "signed_out" | "not_admin";

/**
 * The newest of each word's shipped and local translation wins; a local row marked deleted
 * removes the word's translation if it is newer than the shipped one.
 */
export function mergeTranslations(bundled: TranslationEntry[], local: AdminTranslationRow[]): Map<string, TranslationEntry> {
  const out = new Map(bundled.map((e) => [e.lexeme_id, e]));
  for (const row of local) {
    const base = out.get(row.lexeme_id);
    if (base && base.updated_at > row.updated_at) continue;
    const text = row.translation.trim();
    if (row.deleted_at || !text) out.delete(row.lexeme_id);
    else {
      out.set(row.lexeme_id, {
        lexeme_id: row.lexeme_id, lemma: row.lemma, translation: text, updated_at: row.updated_at,
        examples: row.examples ?? [], verified: row.verified ?? true,
      });
    }
  }
  return out;
}

const byId = (a: { lexeme_id: string }, b: { lexeme_id: string }) => (a.lexeme_id < b.lexeme_id ? -1 : a.lexeme_id > b.lexeme_id ? 1 : 0);

/** The export: every translation this device knows, and the removals made here. */
export function toFile(entries: Iterable<TranslationEntry>, local: AdminTranslationRow[], exportedAt: string): TranslationFile {
  const translations = [...entries].sort(byId);
  const live = new Set(translations.map((e) => e.lexeme_id));
  const removed = local
    .filter((r) => (r.deleted_at || !r.translation.trim()) && !live.has(r.lexeme_id))
    .map((r) => ({ lexeme_id: r.lexeme_id, updated_at: r.updated_at }))
    .sort(byId);
  return { format: "tilsim-translations", version: 2, exported_at: exportedAt, translations, removed };
}

export type ExportResult = { kind: "file"; path: string } | { kind: "clipboard" } | { kind: "download" };

/**
 * Word translations. Only the admin writes them (the learner sees "the app is in test mode"
 * instead). They are shared through the server (src/sync/translations.ts): every device downloads
 * them, without an account, and keeps them for offline use; the admin's edits go up from the admin
 * panel with an admin account. The file shipped with the app (from exports) is the base.
 */
export const useTranslations = defineStore("translations", () => {
  // The shipped file (about 1 MB with the drafts) is its own chunk, loaded after the app opens.
  const bundled = shallowRef<TranslationEntry[]>([]);
  const local = ref<AdminTranslationRow[]>([]);
  const loaded = ref(false);

  const all = computed(() => mergeTranslations(bundled.value, local.value));
  const bundledCount = computed(() => bundled.value.length);
  const state = ref<TranslationSyncState>("idle");
  const pending = ref(0);
  const rejected = ref(0);
  const lastSyncAt = ref<string | null>(null);
  /** Technical detail of the last failure (shown in the admin panel only). */
  const detail = ref("");
  let running: Promise<void> | null = null;
  let again = false;
  let started = false;
  let editTimer: ReturnType<typeof setTimeout> | null = null;
  const localCount = computed(() => local.value.filter((r) => !r.deleted_at && r.translation.trim()).length);

  /** The word's full entry: translation, examples, whether it was checked. */
  function entry(lexemeId: string): TranslationEntry | null {
    return all.value.get(lexemeId) ?? null;
  }

  /** Marks an unchecked translation as checked, unchanged. Admin mode only. */
  async function approve(word: { id: string; lemma: string }): Promise<void> {
    const current = all.value.get(word.id);
    if (current) await set(word, current.translation);
  }

  function get(lexemeId: string): string | null {
    return all.value.get(lexemeId)?.translation ?? null;
  }

  /** Translations containing the text, for searching the dictionary in Uzbek. */
  function search(text: string): TranslationEntry[] {
    const needle = text.trim().toLocaleLowerCase();
    if (!needle) return [];
    return [...all.value.values()].filter((e) => e.translation.toLocaleLowerCase().includes(needle));
  }

  async function load(): Promise<void> {
    if (loaded.value) return;
    const [file, rows] = await Promise.all([import("../data/translations.json"), adminTranslations.listAll()]);
    bundled.value = (file.default as TranslationFile).translations;
    local.value = rows;
    // Translations typed into the learner's own word entries before the admin mode existed
    // become admin translations, once.
    if ((await keyValue.get(MIGRATED_KEY)) === null) {
      const have = new Set(local.value.map((r) => r.lexeme_id));
      for (const row of await vocabulary.list()) {
        const text = row.translation.trim();
        if (!text || have.has(row.lexeme_id)) continue;
        local.value.push(await adminTranslations.insert({
          lexeme_id: row.lexeme_id, lemma: row.lemma, translation: text.slice(0, MAX_TRANSLATION), examples: [], verified: true,
        }));
        have.add(row.lexeme_id);
      }
      await keyValue.set(MIGRATED_KEY, "1");
    }
    // Edits made before translations were on the server go up once.
    if ((await keyValue.get(QUEUED_KEY)) === null) {
      await queueExisting();
      await keyValue.set(QUEUED_KEY, "1");
    }
    pending.value = await translationStore.count();
    loaded.value = true;
  }

  function api(): TranslationApi {
    const settings = useSettings();
    const session = useSession();
    return {
      push: (changes: WireTranslation[]) =>
        session.authorized<TranslationPushResult>("/v1/translations", { body: { changes }, timeoutMs: 60_000 }),
      pull: (since: number) =>
        request<TranslationPullResult>(settings.apiUrl, `/v1/translations?since=${since}`, { timeoutMs: 60_000 }),
    };
  }

  async function run(): Promise<void> {
    await load();
    if (!useSettings().apiUrl) return;
    const session = useSession();
    state.value = "syncing";
    detail.value = "";
    let waiting: TranslationSyncState | null = null;
    let changed = false;
    try {
      if (pending.value) {
        if (!session.user) {
          waiting = "signed_out";
        } else {
          try {
            const pushed = await pushTranslations(api());
            changed ||= pushed.changed;
            rejected.value = pushed.rejected;
            if (pushed.rejected) detail.value = `rejected: ${pushed.rejectedCodes.join(", ")}`;
          } catch (e) {
            if (!(e instanceof ApiError) || !["not_admin", "session_expired"].includes(e.code)) throw e;
            waiting = e.code === "not_admin" ? "not_admin" : "signed_out";
          }
        }
      }
      const cursor = Number((await keyValue.get(CURSOR_KEY)) ?? "0") || 0;
      const pulled = await pullTranslations(api(), cursor, (c) => keyValue.set(CURSOR_KEY, String(c)));
      changed ||= pulled.changed;
      lastSyncAt.value = new Date().toISOString();
      await keyValue.set(LAST_KEY, lastSyncAt.value);
      state.value = waiting ?? "ok";
    } catch (e) {
      detail.value = e instanceof ApiError ? `${e.code}: ${e.message}` : String(e);
      state.value = e instanceof ApiError && e.code === "network" ? "offline" : "failed";
    } finally {
      if (changed) local.value = await adminTranslations.listAll();
      pending.value = await translationStore.count();
    }
  }

  /** Sends the admin's edits (with an admin account) and brings the latest translations. */
  async function syncNow(): Promise<void> {
    if (running) {
      again = true;
      return running;
    }
    running = (async () => {
      do {
        again = false;
        await run();
      } while (again);
    })().finally(() => {
      running = null;
    });
    return running;
  }

  function start(): void {
    if (started) return;
    started = true;
    void keyValue.get(LAST_KEY).then((v) => (lastSyncAt.value ??= v));
    void syncNow();
    setInterval(() => void syncNow(), EVERY_MS);
    window.addEventListener("online", () => void syncNow());
    // Edits waiting for an admin account go up once one signs in.
    watch(() => useSession().user?.id, (id) => {
      if (id && pending.value) void syncNow();
    });
  }

  /**
   * Sets (or, with an empty text, removes) a word's translation. Admin mode only. The admin's entry
   * is verified; it keeps the word's example sentences.
   */
  async function set(word: { id: string; lemma: string }, text: string): Promise<void> {
    if (!useAdmin().unlocked) throw new Error("admin mode is locked");
    await load();
    const clean = text.trim().slice(0, MAX_TRANSLATION);
    const examples = all.value.get(word.id)?.examples ?? [];
    const existing = local.value.find((r) => r.lexeme_id === word.id);
    let row: AdminTranslationRow;
    if (existing) {
      if (!clean) row = existing.deleted_at ? existing : await adminTranslations.remove(existing);
      else row = await adminTranslations.update(existing, { translation: clean, lemma: word.lemma, examples, verified: true });
    } else {
      if (!clean && !all.value.has(word.id)) return;
      row = await adminTranslations.insert({ lexeme_id: word.id, lemma: word.lemma, translation: clean, examples, verified: true });
      if (!clean) row = await adminTranslations.remove(row);
    }
    local.value = [...local.value.filter((r) => r.lexeme_id !== word.id), row];
    await translationStore.mark([row]);
    pending.value = await translationStore.count();
    if (editTimer) clearTimeout(editTimer);
    editTimer = setTimeout(() => void syncNow(), AFTER_EDIT_MS);
  }

  function exportText(): string {
    return `${JSON.stringify(toFile(all.value.values(), local.value, new Date().toISOString()), null, 2)}\n`;
  }

  /** Desktop: a file on the Desktop. Android: the clipboard. Plain browser: a download. */
  async function exportAll(): Promise<ExportResult> {
    await load();
    const text = exportText();
    if (inTauri && platform === "windows") {
      return { kind: "file", path: await invoke<string>("export_translations", { contents: text }) };
    }
    if (inTauri) {
      await copyText(text);
      return { kind: "clipboard" };
    }
    const url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "Zabon-tarjimalar.json";
    a.click();
    URL.revokeObjectURL(url);
    return { kind: "download" };
  }

  return {
    all, bundledCount, localCount, loaded, state, pending, rejected, lastSyncAt, detail,
    get, entry, approve, search, load, set, exportText, exportAll, syncNow, start,
  };
});
