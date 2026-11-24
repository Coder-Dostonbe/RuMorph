import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { vocabulary, type Example, type VocabularyRow } from "../data/userData";
import { useTranslations } from "./translations";

export interface WordRef {
  id: string;
  lemma: string;
  pos: string | null;
}

/**
 * The learner's own words (user_vocabulary), loaded once and kept in memory. Their old
 * `translation` column is no longer written: translations are in ./translations.ts.
 */
export const useVocabulary = defineStore("vocabulary", () => {
  const rows = ref<VocabularyRow[]>([]);
  const loaded = ref(false);
  const error = ref("");

  const byLexeme = computed(() => new Map(rows.value.map((r) => [r.lexeme_id, r])));

  async function load(): Promise<void> {
    if (loaded.value) return;
    try {
      rows.value = await vocabulary.list();
      loaded.value = true;
    } catch (e) {
      error.value = String(e);
    }
  }

  /** Reads the table again (after a sync brought changes). Does nothing if it was never read. */
  async function reload(): Promise<void> {
    if (!loaded.value) return;
    loaded.value = false;
    await load();
  }

  async function save(
    word: WordRef,
    fields: { note: string; examples: Example[]; status: VocabularyRow["status"] },
  ): Promise<VocabularyRow> {
    await load();
    const clean = {
      note: fields.note.trim(),
      examples: fields.examples.map((e) => ({ ru: e.ru.trim(), uz: e.uz.trim() })).filter((e) => e.ru || e.uz),
      status: fields.status,
    };
    const existing = byLexeme.value.get(word.id);
    const row = existing
      ? await vocabulary.update(existing, clean)
      : await vocabulary.insert({ lexeme_id: word.id, lemma: word.lemma, pos: word.pos, translation: "", ...clean });
    rows.value = [...rows.value.filter((r) => r.id !== row.id), row];
    return row;
  }

  async function remove(lexemeId: string): Promise<void> {
    const existing = byLexeme.value.get(lexemeId);
    if (!existing) return;
    await vocabulary.remove(existing);
    rows.value = rows.value.filter((r) => r.id !== existing.id);
  }

  /** Words whose translation, note or lemma contains the text (for Uzbek search). */
  function find(text: string): VocabularyRow[] {
    const needle = text.trim().toLocaleLowerCase();
    if (!needle) return [...rows.value].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
    const translations = useTranslations();
    return rows.value.filter((r) =>
      [translations.get(r.lexeme_id) ?? "", r.note, r.lemma].some((v) => v.toLocaleLowerCase().includes(needle)),
    );
  }

  return { rows, loaded, error, byLexeme, load, reload, save, remove, find };
});
