<script setup lang="ts">
// Flashcards: review session and the list of cards. Scheduling is SM-2 in tilsim_core (srs.py);
// the card faces come from the learner's own entries (translation, note, examples) and the
// lexicon (description, principal forms).
import { computed, onMounted, ref, watch } from "vue";
import { CoreError } from "../core/client";
import { grammar, type WordInfo } from "../core/grammar";
import type { FlashcardRow } from "../data/userData";
import { format, locale, useI18n } from "../i18n";
import { useCards } from "../stores/cards";
import { useCore } from "../stores/core";
import { useGrammar } from "../stores/grammar";
import { useVocabulary } from "../stores/vocabulary";
import { formatDays, formatUntil } from "../ui/duration";

const m = useI18n();
const core = useCore();
const cards = useCards();
const vocab = useVocabulary();
const g = useGrammar();
const PART_OF_SPEECH = new Set(["VERB", "ADJF", "indc"]);

/** "qaratqich kelishigi, birlik" for a principal form. */
function formLabel(grammemes: string[]): string {
  return grammemes.filter((c) => !PART_OF_SPEECH.has(c)).map((c) => g.name(c)).join(", ");
}

const words = ref<Record<string, WordInfo>>({});
const failure = ref("");
const queueIds = ref<string[]>([]);
const session = ref<{ ids: string[]; position: number; answered: number } | null>(null);
const revealed = ref(false);
const previewDays = ref<Record<string, number>>({});
const lastSessionAnswers = ref<number | null>(null);
const busy = ref(false);

function err(e: unknown): string {
  return e instanceof CoreError ? `${e.code}: ${e.message}` : String(e);
}

async function refresh(): Promise<void> {
  if (core.status !== "ready") return;
  try {
    await Promise.all([cards.load(), vocab.load()]);
    const ids = [...new Set(cards.cards.map((c) => c.lexeme_id))];
    words.value = ids.length ? await grammar.words(ids, locale.value) : {};
    queueIds.value = await cards.queue();
  } catch (e) {
    failure.value = err(e);
  }
}
onMounted(refresh);
watch([() => core.status, locale], refresh);

const current = computed<FlashcardRow | null>(() => {
  const s = session.value;
  if (!s) return null;
  const id = s.ids[s.position];
  return cards.cards.find((c) => c.id === id) ?? null;
});
const currentWord = computed(() => (current.value ? words.value[current.value.lexeme_id] ?? null : null));
const currentEntry = computed(() => (current.value ? vocab.byLexeme.get(current.value.lexeme_id) ?? null : null));

const newLeft = computed(() => Math.max(0, cards.newPerDay - cards.newSeenToday));
const nextDue = computed(() => {
  const upcoming = cards.cards.filter((c) => c.last_review_at).map((c) => c.due_at).sort();
  return upcoming[0] ?? null;
});

function start(): void {
  lastSessionAnswers.value = null;
  session.value = { ids: [...queueIds.value], position: 0, answered: 0 };
  revealed.value = false;
}

async function reveal(): Promise<void> {
  if (!current.value) return;
  revealed.value = true;
  try {
    previewDays.value = await cards.preview(current.value);
  } catch (e) {
    failure.value = err(e);
  }
}

async function grade(value: 0 | 1 | 2 | 3): Promise<void> {
  const s = session.value;
  const row = current.value;
  if (!s || !row || busy.value) return;
  busy.value = true;
  try {
    await cards.answer(row, value);
    s.answered += 1;
    // A forgotten card comes back at the end of this session.
    if (value === 0) s.ids.push(row.id);
    s.position += 1;
    revealed.value = false;
    if (s.position >= s.ids.length) finish();
  } catch (e) {
    failure.value = err(e);
  } finally {
    busy.value = false;
  }
}

function finish(): void {
  lastSessionAnswers.value = session.value?.answered ?? 0;
  session.value = null;
  void refresh();
}

function onKey(event: KeyboardEvent): void {
  if (!session.value || event.target instanceof HTMLInputElement) return;
  if (!revealed.value && (event.key === " " || event.key === "Enter")) {
    event.preventDefault();
    void reveal();
  } else if (revealed.value && ["1", "2", "3", "4"].includes(event.key)) {
    void grade((Number(event.key) - 1) as 0 | 1 | 2 | 3);
  }
}

const gradeKeys = [
  { value: 0, key: "again" }, { value: 1, key: "hard" }, { value: 2, key: "good" }, { value: 3, key: "easy" },
] as const;

const sortedCards = computed(() => [...cards.cards].sort((a, b) => a.due_at.localeCompare(b.due_at)));

async function onNewPerDay(event: Event): Promise<void> {
  await cards.setNewPerDay(Number((event.target as HTMLInputElement).value));
  queueIds.value = await cards.queue();
}
</script>

<template>
  <section class="page" tabindex="-1" @keydown="onKey">
    <h1>{{ m.cards.title }}</h1>
    <p class="muted intro">{{ m.cards.intro }}</p>
    <div v-if="core.status === 'failed'" class="alert err">{{ format(m.analyze.coreFailed, { error: core.error }) }}</div>
    <div v-else-if="core.status !== 'ready'" class="alert warn">{{ m.analyze.coreLoading }}</div>
    <div v-if="failure" class="alert err">{{ failure }}</div>

    <template v-if="!session">
      <div class="stats">
        <div class="card stat"><span class="num">{{ queueIds.length }}</span><span class="muted small">{{ m.cards.dueNow }}</span></div>
        <div class="card stat"><span class="num">{{ newLeft }}</span><span class="muted small">{{ m.cards.newLeft }}</span></div>
        <div class="card stat"><span class="num">{{ cards.cards.length }}</span><span class="muted small">{{ m.cards.total }}</span></div>
        <div class="card stat"><span class="num">{{ cards.reviewedToday }}</span><span class="muted small">{{ m.cards.reviewedToday }}</span></div>
      </div>

      <div v-if="lastSessionAnswers !== null" class="alert ok">{{ format(m.cards.sessionDone, { n: lastSessionAnswers }) }}</div>

      <div class="card">
        <template v-if="cards.cards.length === 0">
          <p>{{ m.cards.empty }}</p>
          <RouterLink to="/dictionary" class="btn primary">{{ m.cards.toDictionary }}</RouterLink>
        </template>
        <template v-else>
          <button v-if="queueIds.length" type="button" class="btn primary big" :disabled="core.status !== 'ready'" @click="start">
            {{ m.cards.start }} ({{ queueIds.length }})
          </button>
          <template v-else>
            <p>{{ m.cards.nothingDue }}</p>
            <p v-if="nextDue" class="muted">{{ format(m.cards.nextDue, { when: formatUntil(nextDue, m) }) }}</p>
          </template>
          <label class="limit">
            {{ m.cards.newPerDay }}
            <input class="input" type="number" min="0" max="200" :value="cards.newPerDay" @change="onNewPerDay" />
          </label>
        </template>
      </div>

      <details v-if="cards.cards.length" class="card">
        <summary>{{ m.cards.list }} ({{ cards.cards.length }})</summary>
        <table>
          <tbody>
            <tr v-for="c in sortedCards" :key="c.id">
              <td lang="ru" class="w">{{ words[c.lexeme_id]?.lemma ?? c.lexeme_id.split("|")[0] }}</td>
              <td>{{ vocab.byLexeme.get(c.lexeme_id)?.translation }}</td>
              <td class="muted small">{{ m.cards.directions[c.direction] }}</td>
              <td class="small">{{ m.cards.due }}: {{ formatUntil(c.due_at, m) }}</td>
              <td class="small">{{ m.cards.interval }}: {{ c.interval_days ? formatDays(c.interval_days, m) : "—" }}</td>
              <td><button type="button" class="btn link" @click="cards.remove(c.lexeme_id, c.direction).then(refresh)">{{ m.cards.remove }}</button></td>
            </tr>
          </tbody>
        </table>
      </details>
    </template>

    <div v-else-if="current" class="session">
      <div class="top">
        <span class="muted small">{{ format(m.cards.progress, { done: session.position + 1, total: session.ids.length }) }}</span>
        <button type="button" class="btn" @click="finish">{{ m.cards.stop }}</button>
      </div>
      <article class="card face">
        <p class="muted small">{{ m.cards.directions[current.direction] }}</p>
        <template v-if="current.direction === 'ru_uz'">
          <h2 class="prompt" lang="ru">{{ currentWord?.lemma ?? current.lexeme_id.split("|")[0] }}</h2>
          <p class="muted small">{{ currentWord?.description }}</p>
        </template>
        <h2 v-else class="prompt">{{ currentEntry?.translation || m.cards.noTranslation }}</h2>

        <div v-if="revealed" class="answer">
          <h2 v-if="current.direction === 'ru_uz'" class="tr">{{ currentEntry?.translation || m.cards.noTranslation }}</h2>
          <template v-else>
            <h2 class="tr" lang="ru">{{ currentWord?.lemma ?? current.lexeme_id.split("|")[0] }}</h2>
            <p class="muted small">{{ currentWord?.description }}</p>
          </template>
          <p v-if="!currentWord" class="alert warn">{{ m.cards.missingWord }}</p>
          <div v-if="currentWord?.key_forms.length" class="forms">
            <span class="muted small">{{ m.cards.keyForms }}</span>
            <ul>
              <li v-for="f in currentWord.key_forms" :key="f.index">
                <span lang="ru" class="kf">{{ f.form }}</span> <span class="muted small">{{ formLabel(f.grammemes) }}</span>
              </li>
            </ul>
          </div>
          <p v-if="currentEntry?.note" class="small">{{ currentEntry.note }}</p>
          <ul v-if="currentEntry?.examples.length" class="examples">
            <li v-for="(ex, i) in currentEntry.examples" :key="i"><span lang="ru">{{ ex.ru }}</span> — {{ ex.uz }}</li>
          </ul>
        </div>
      </article>
      <div class="buttons">
        <button v-if="!revealed" type="button" class="btn primary big" @click="reveal">{{ m.cards.showAnswer }}</button>
        <template v-else>
          <button v-for="gk in gradeKeys" :key="gk.value" type="button" class="btn grade" :class="gk.key"
            :disabled="busy" @click="grade(gk.value)">
            <span>{{ m.cards.grades[gk.key] }}</span>
            <small v-if="previewDays[gk.value] !== undefined" class="muted">{{ formatDays(previewDays[gk.value]!, m) }}</small>
          </button>
        </template>
      </div>
    </div>
  </section>
</template>

<style scoped>
.page {
  max-width: 820px;
  display: grid;
  gap: 1rem;
  align-content: start;
  outline: none;
}
.intro {
  max-width: 70ch;
  margin: 0;
}
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.75rem;
}
.stat {
  display: grid;
  gap: 0.1rem;
}
.num {
  font-size: 1.7rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.big {
  min-height: 3rem;
  font-size: 1.02rem;
  padding: 0 1.4rem;
}
.limit {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-top: 1rem;
  font-size: 0.9rem;
}
.limit .input {
  width: 5.5rem;
}
details summary {
  cursor: pointer;
  font-weight: 600;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 0.6rem;
}
td {
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid var(--border);
  vertical-align: baseline;
}
.w {
  font-weight: 700;
}
.session {
  display: grid;
  gap: 0.8rem;
}
.top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.face {
  min-height: 15rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.3rem;
  padding: 1.6rem;
}
.prompt {
  font-size: 2rem;
  margin: 0.3rem 0;
}
.answer {
  border-top: 1px solid var(--border);
  margin-top: 1rem;
  padding-top: 1rem;
}
.tr {
  color: var(--accent);
  font-size: 1.5rem;
}
.forms ul {
  list-style: none;
  padding: 0;
  margin: 0.3rem 0 0.6rem;
  display: grid;
  gap: 0.15rem;
}
.kf {
  font-weight: 650;
}
.examples {
  list-style: none;
  padding: 0;
  margin: 0.4rem 0 0;
  font-size: 0.92rem;
}
.buttons {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.5rem;
}
.buttons .big {
  grid-column: 1 / -1;
}
.grade {
  flex-direction: column;
  gap: 0;
  min-height: 3.4rem;
}
.grade.again {
  border-color: var(--err);
  color: var(--err);
}
.grade.good {
  border-color: var(--accent);
}
</style>
