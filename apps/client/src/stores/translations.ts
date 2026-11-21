import { invoke } from "@tauri-apps/api/core";
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { inTauri, platform } from "../app/platform";
import shipped from "../data/translations.json";
import { keyValue } from "../data/keyValue";
import { copyText } from "../ui/clipboard";
import { adminTranslations, vocabulary, type AdminTranslationRow } from "../data/userData";
import { useAdmin } from "./admin";

/** One translation as shipped with the app and as exported from the admin panel. */
export interface TranslationEntry {
  lexeme_id: string;
  lemma: string;
  translation: string;
  updated_at: string;
}

export interface TranslationFile {
  format: "tilsim-translations";
  version: 1;
  exported_at?: string;
  translations: TranslationEntry[];
  /** Words whose translation the admin removed on the exporting device. */
  removed?: { lexeme_id: string; updated_at: string }[];
}

export const MAX_TRANSLATION = 200;
const MIGRATED_KEY = "translations_migrated";

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
    else out.set(row.lexeme_id, { lexeme_id: row.lexeme_id, lemma: row.lemma, translation: text, updated_at: row.updated_at });
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
  return { format: "tilsim-translations", version: 1, exported_at: exportedAt, translations, removed };
}

export type ExportResult = { kind: "file"; path: string } | { kind: "clipboard" } | { kind: "download" };

/**
 * Word translations. While the app is in testing only the admin writes them (the learner sees
 * "the app is in test mode" instead); they reach other devices through the file shipped with the
 * app, which is rebuilt from the admin's exports.
 */
export const useTranslations = defineStore("translations", () => {
  const bundled = (shipped as TranslationFile).translations;
  const local = ref<AdminTranslationRow[]>([]);
  const loaded = ref(false);

  const all = computed(() => mergeTranslations(bundled, local.value));
  const localCount = computed(() => local.value.filter((r) => !r.deleted_at && r.translation.trim()).length);

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
    local.value = await adminTranslations.listAll();
    // Translations typed into the learner's own word entries before the admin mode existed
    // become admin translations, once.
    if ((await keyValue.get(MIGRATED_KEY)) === null) {
      const have = new Set(local.value.map((r) => r.lexeme_id));
      for (const row of await vocabulary.list()) {
        const text = row.translation.trim();
        if (!text || have.has(row.lexeme_id)) continue;
        local.value.push(await adminTranslations.insert({ lexeme_id: row.lexeme_id, lemma: row.lemma, translation: text.slice(0, MAX_TRANSLATION) }));
        have.add(row.lexeme_id);
      }
      await keyValue.set(MIGRATED_KEY, "1");
    }
    loaded.value = true;
  }

  /** Sets (or, with an empty text, removes) a word's translation. Admin mode only. */
  async function set(word: { id: string; lemma: string }, text: string): Promise<void> {
    if (!useAdmin().unlocked) throw new Error("admin mode is locked");
    await load();
    const clean = text.trim().slice(0, MAX_TRANSLATION);
    const existing = local.value.find((r) => r.lexeme_id === word.id);
    let row: AdminTranslationRow;
    if (existing) {
      if (!clean) row = existing.deleted_at ? existing : await adminTranslations.remove(existing);
      else row = await adminTranslations.update(existing, { translation: clean, lemma: word.lemma });
    } else {
      if (!clean && !all.value.has(word.id)) return;
      row = await adminTranslations.insert({ lexeme_id: word.id, lemma: word.lemma, translation: clean });
      if (!clean) row = await adminTranslations.remove(row);
    }
    local.value = [...local.value.filter((r) => r.lexeme_id !== word.id), row];
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
    a.download = "Tilsim-tarjimalar.json";
    a.click();
    URL.revokeObjectURL(url);
    return { kind: "download" };
  }

  return { all, bundledCount: bundled.length, localCount, loaded, get, search, load, set, exportText, exportAll };
});
