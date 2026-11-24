import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { grammar, type CardState } from "../core/grammar";
import { flashcards, nowIso, reviews, type Direction, type FlashcardRow, type ReviewRow } from "../data/userData";
import { keyValue } from "../data/keyValue";

export const DEFAULT_NEW_PER_DAY = 20;

/** Local calendar day of an ISO time, "2026-11-21". */
export function localDay(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function state(row: FlashcardRow): CardState {
  return {
    due_at: row.due_at, interval_days: row.interval_days, ease: row.ease, reps: row.reps, lapses: row.lapses,
    last_review_at: row.last_review_at,
  };
}

/** Flashcards and their review history. Scheduling (SM-2) runs in tilsim_core (srs.py). */
export const useCards = defineStore("cards", () => {
  const cards = ref<FlashcardRow[]>([]);
  const history = ref<ReviewRow[]>([]);
  const newPerDay = ref(DEFAULT_NEW_PER_DAY);
  const loaded = ref(false);

  async function load(): Promise<void> {
    if (loaded.value) return;
    const [c, h, limit] = await Promise.all([flashcards.list(), reviews.list(), keyValue.get("cards.new_per_day")]);
    cards.value = c;
    history.value = h;
    const n = Number(limit);
    if (limit !== null && Number.isInteger(n) && n >= 0 && n <= 200) newPerDay.value = n;
    loaded.value = true;
  }

  /** Reads the tables again (after a sync brought changes). Does nothing if they were never read. */
  async function reload(): Promise<void> {
    if (!loaded.value) return;
    loaded.value = false;
    await load();
  }

  async function setNewPerDay(n: number): Promise<void> {
    newPerDay.value = Math.max(0, Math.min(200, Math.round(n)));
    await keyValue.set("cards.new_per_day", String(newPerDay.value));
  }

  const byWord = computed(() => {
    const map = new Map<string, FlashcardRow>();
    for (const c of cards.value) map.set(`${c.lexeme_id}#${c.direction}`, c);
    return map;
  });

  function find(lexemeId: string, direction: Direction): FlashcardRow | undefined {
    return byWord.value.get(`${lexemeId}#${direction}`);
  }

  async function add(lexemeId: string, direction: Direction): Promise<void> {
    await load();
    if (find(lexemeId, direction)) return;
    const row = await flashcards.insert({
      lexeme_id: lexemeId, direction, due_at: nowIso(), interval_days: 0, ease: 2.5, reps: 0, lapses: 0, last_review_at: null,
    });
    cards.value = [...cards.value, row];
  }

  async function remove(lexemeId: string, direction: Direction): Promise<void> {
    const row = find(lexemeId, direction);
    if (!row) return;
    await flashcards.remove(row);
    cards.value = cards.value.filter((c) => c.id !== row.id);
  }

  /** Cards whose first review was today (they count against the daily limit of new cards). */
  const newSeenToday = computed(() => {
    const first = new Map<string, string>();
    for (const r of history.value) {
      const seen = first.get(r.card_id);
      if (!seen || r.reviewed_at < seen) first.set(r.card_id, r.reviewed_at);
    }
    const today = localDay(nowIso());
    return [...first.values()].filter((at) => localDay(at) === today).length;
  });

  const reviewedToday = computed(() => {
    const today = localDay(nowIso());
    return history.value.filter((r) => localDay(r.reviewed_at) === today).length;
  });

  /** Card ids to study now, in order (due reviews, then new cards within today's limit). */
  async function queue(): Promise<string[]> {
    await load();
    const result = await grammar.srsQueue(
      cards.value.map((c) => ({ id: c.id, ...state(c) })), nowIso(), newPerDay.value, newSeenToday.value,
    );
    return result.ids;
  }

  async function preview(row: FlashcardRow): Promise<Record<string, number>> {
    return (await grammar.srsPreview(state(row), nowIso())).days;
  }

  async function answer(row: FlashcardRow, grade: 0 | 1 | 2 | 3): Promise<FlashcardRow> {
    const now = nowIso();
    const { card } = await grammar.srsReview(state(row), grade, now);
    const updated = await flashcards.update(row, card);
    const entry = await reviews.insert({
      card_id: row.id, reviewed_at: now, grade, interval_after: card.interval_days, ease_after: card.ease,
    });
    cards.value = cards.value.map((c) => (c.id === row.id ? updated : c));
    history.value = [...history.value, entry];
    return updated;
  }

  return { cards, history, newPerDay, loaded, load, reload, setNewPerDay, find, add, remove, newSeenToday, reviewedToday, queue, preview, answer };
});
