<script setup lang="ts">
// Daily reading: the learner's own texts. A text is prepared by tilsim_core (reading.py): its
// words linked to the dictionary and its difficulty measured. Tapping a word opens its card.
// Finishing a text logs a reading session (reading_history).
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { grammar, type PreparedText, type ReadingToken } from "../core/grammar";
import { readings, readingTexts, type ReadingRow, type ReadingTextRow } from "../data/userData";
import { dateLocale, format, useI18n } from "../i18n";
import { useCore } from "../stores/core";
import { useVocabulary } from "../stores/vocabulary";
import VocabEditor from "../ui/VocabEditor.vue";
import LexemeDetail from "../ui/grammar/LexemeDetail.vue";
import type { LexemeInfo } from "../core/grammar";
import { callFailed, coreFailed } from "../ui/failure";

const MAX = 50000;
const m = useI18n();
const core = useCore();
const vocab = useVocabulary();
const route = useRoute();
const router = useRouter();

const texts = ref<ReadingTextRow[]>([]);
const history = ref<ReadingRow[]>([]);
const failure = ref("");
const draft = ref({ title: "", body: "", source: "" });
const openId = ref<string | null>(typeof route.query.text === "string" ? route.query.text : null);
const prepared = ref<PreparedText | null>(null);
const selected = ref<ReadingToken | null>(null);
const selectedLexeme = ref<string | null>(null);
const lexemeInfo = ref<LexemeInfo | null>(null);
const looked = ref(new Set<number>());
const openedAt = ref(0);
const finishedNote = ref("");

function err(e: unknown): string {
  return callFailed(m.value, e);
}

async function load(): Promise<void> {
  [texts.value, history.value] = await Promise.all([readingTexts.list(), readings.list()]);
}
onMounted(async () => {
  await Promise.all([load(), vocab.load()]);
  if (openId.value) void prepare();
});

const lastRead = computed(() => {
  const map = new Map<string, string>();
  for (const h of history.value) if ((map.get(h.text_id) ?? "") < h.read_at) map.set(h.text_id, h.read_at);
  return map;
});
/** Today's text: the one unread the longest (never-read texts first, oldest added first). */
const today = computed(() =>
  [...texts.value].sort((a, b) => (lastRead.value.get(a.id) ?? "").localeCompare(lastRead.value.get(b.id) ?? "") || a.created_at.localeCompare(b.created_at))[0] ?? null,
);
const current = computed(() => texts.value.find((t) => t.id === openId.value) ?? null);

async function add(): Promise<void> {
  failure.value = "";
  const title = draft.value.title.trim();
  const body = draft.value.body.trim();
  if (!title || !body) return;
  if (body.length > MAX) {
    failure.value = format(m.value.reading.tooLong, { n: MAX });
    return;
  }
  await readingTexts.insert({ title: title.slice(0, 200), body, source: draft.value.source.trim() });
  draft.value = { title: "", body: "", source: "" };
  await load();
}

async function remove(row: ReadingTextRow): Promise<void> {
  await readingTexts.remove(row);
  await load();
}

async function prepare(): Promise<void> {
  if (!current.value || core.status !== "ready") return;
  try {
    prepared.value = await grammar.reading(current.value.body);
    selected.value = null;
    looked.value = new Set();
    openedAt.value = Date.now();
    finishedNote.value = "";
  } catch (e) {
    failure.value = err(e);
  }
}

function open(id: string): void {
  openId.value = id;
  prepared.value = null;
  void router.replace({ query: { text: id } });
  void prepare();
}
function close(): void {
  openId.value = null;
  prepared.value = null;
  void router.replace({ query: {} });
}
watch(() => core.status, () => void prepare());

/** The text cut into plain parts and word tokens. */
const pieces = computed(() => {
  const body = current.value?.body ?? "";
  const out: { text: string; token?: ReadingToken; index?: number }[] = [];
  let at = 0;
  (prepared.value?.tokens ?? []).forEach((token, index) => {
    out.push({ text: body.slice(at, token.start) });
    out.push({ text: body.slice(token.start, token.end), token, index });
    at = token.end;
  });
  out.push({ text: body.slice(at) });
  return out;
});

function wordClass(token: ReadingToken): string {
  if (!token.known) return "unknown";
  const entry = token.lexemes.map((id) => vocab.byLexeme.get(id)).find(Boolean);
  if (!entry) return "";
  return entry.status === "known" ? "known" : "mine";
}

function pick(token: ReadingToken, index: number): void {
  selected.value = token;
  selectedLexeme.value = token.lexemes[0] ?? null;
  looked.value.add(index);
}

const word = computed(() =>
  lexemeInfo.value && lexemeInfo.value.id === selectedLexeme.value
    ? { id: lexemeInfo.value.id, lemma: lexemeInfo.value.lemma, pos: lexemeInfo.value.pos }
    : null,
);

async function finish(): Promise<void> {
  if (!current.value || !prepared.value) return;
  const duration = Date.now() - openedAt.value;
  await readings.insert({
    text_id: current.value.id, read_at: new Date().toISOString(), words: prepared.value.words,
    looked_up: looked.value.size, duration_ms: duration,
  });
  finishedNote.value = format(m.value.reading.finished, { words: prepared.value.words, looked: looked.value.size, min: Math.max(1, Math.round(duration / 60000)) });
  await load();
}
</script>

<template>
  <section class="page">
    <h1>{{ m.reading.title }}</h1>
    <div v-if="core.status === 'failed'" class="alert err">{{ coreFailed(m, core.error) }}</div>
    <div v-else-if="core.status !== 'ready'" class="alert warn">{{ m.analyze.coreLoading }}</div>
    <div v-if="failure" class="alert err">{{ failure }}</div>

    <template v-if="!current">
      <p class="muted intro">{{ m.reading.intro }}</p>
      <article v-if="today" class="card today">
        <p class="muted small">{{ m.reading.today }} · {{ m.reading.todayHint }}</p>
        <h2>{{ today.title }}</h2>
        <p class="preview" lang="ru">{{ today.body.slice(0, 220) }}{{ today.body.length > 220 ? "…" : "" }}</p>
        <button type="button" class="btn primary" @click="open(today.id)">{{ m.reading.open }}</button>
      </article>

      <div class="card">
        <h2>{{ m.reading.library }}</h2>
        <p v-if="texts.length === 0" class="muted">{{ m.reading.empty }}</p>
        <ul v-else class="texts">
          <li v-for="t in texts" :key="t.id">
            <div>
              <strong>{{ t.title }}</strong>
              <span class="muted small">
                {{ lastRead.get(t.id) ? format(m.reading.lastRead, { date: new Date(lastRead.get(t.id)!).toLocaleDateString(dateLocale()) }) : m.reading.neverRead }}
                <template v-if="t.source"> · {{ t.source }}</template>
              </span>
            </div>
            <div class="actions">
              <button type="button" class="btn" @click="open(t.id)">{{ m.reading.open }}</button>
              <button type="button" class="btn link" @click="remove(t)">{{ m.reading.remove }}</button>
            </div>
          </li>
        </ul>
      </div>

      <form class="card" @submit.prevent="add">
        <h2>{{ m.reading.add }}</h2>
        <div class="field">
          <label for="r-title">{{ m.reading.titleLabel }}</label>
          <input id="r-title" v-model="draft.title" class="input" maxlength="200" />
        </div>
        <div class="field">
          <label for="r-body">{{ m.reading.body }}</label>
          <textarea id="r-body" v-model="draft.body" class="input area" lang="ru" rows="8" :maxlength="MAX" />
        </div>
        <div class="field">
          <label for="r-source">{{ m.reading.source }}</label>
          <input id="r-source" v-model="draft.source" class="input" maxlength="300" />
        </div>
        <button class="btn primary" type="submit" :disabled="!draft.title.trim() || !draft.body.trim()">{{ m.reading.save }}</button>
      </form>
    </template>

    <template v-else>
      <button type="button" class="btn back" @click="close">{{ m.reading.back }}</button>
      <div class="layout">
        <article class="card reader">
          <h2>{{ current.title }}</h2>
          <p v-if="prepared" class="muted small">
            {{ format(m.reading.stats, { words: prepared.words, lemmas: prepared.distinct_lemmas }) }} ·
            {{ format(m.reading.coverage, { p: prepared.coverage["1000"], n: 1000 }) }} ·
            {{ format(m.reading.unknown, { p: prepared.unknown }) }}
          </p>
          <p class="legend small">
            <span class="mine">{{ m.reading.legendMine }}</span>
            <span class="known">{{ m.reading.legendKnown }}</span>
            <span class="unknown">{{ m.reading.legendUnknown }}</span>
          </p>
          <div v-if="prepared" class="text" lang="ru"><template v-for="(p, i) in pieces" :key="i"><button v-if="p.token"
            type="button" class="w" :class="[wordClass(p.token), { active: selected === p.token }]"
            @click="pick(p.token, p.index!)">{{ p.text }}</button><template v-else>{{ p.text }}</template></template></div>
          <div v-else class="text" lang="ru">{{ current.body }}</div>
          <p v-if="current.source" class="muted small">{{ current.source }}</p>
          <div class="finish">
            <button type="button" class="btn primary" :disabled="!prepared" @click="finish">{{ m.reading.finish }}</button>
            <span v-if="finishedNote" class="muted small">{{ finishedNote }}</span>
          </div>
        </article>
        <div class="side">
          <p v-if="!selected" class="muted">{{ m.reading.tapHint }}</p>
          <template v-else>
            <div v-if="selected.lexemes.length > 1" class="choices">
              <button v-for="id in selected.lexemes" :key="id" type="button" class="btn chip" :class="{ active: id === selectedLexeme }"
                lang="ru" @click="selectedLexeme = id">{{ id.split("|")[0] }}</button>
            </div>
            <LexemeDetail v-if="selectedLexeme" :id="selectedLexeme" @loaded="lexemeInfo = $event">
              <VocabEditor v-if="word" :word="word" />
            </LexemeDetail>
            <p v-else class="alert warn">{{ m.reading.legendUnknown }}</p>
          </template>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.page {
  max-width: 1180px;
  display: grid;
  gap: 1rem;
  align-content: start;
}
.intro {
  margin: 0;
  max-width: 70ch;
}
.today h2 {
  margin: 0.2rem 0 0.4rem;
}
.preview {
  color: var(--muted);
}
.texts {
  list-style: none;
  margin: 0;
  padding: 0;
}
.texts li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.6rem 0;
  border-bottom: 1px solid var(--border);
}
.texts li > div:first-child {
  display: grid;
}
.actions {
  display: flex;
  gap: 0.6rem;
  align-items: center;
}
.area {
  min-height: 10rem;
  padding: 0.6rem 0.8rem;
  resize: vertical;
}
.back {
  justify-self: start;
}
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
  gap: 1rem;
  align-items: start;
}
@media (max-width: 900px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }
}
.text {
  white-space: pre-wrap;
  font-size: 1.12rem;
  line-height: 1.95;
  margin: 0.6rem 0 1rem;
}
.w {
  font: inherit;
  color: inherit;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  border-radius: 3px;
}
.w:hover,
.w.active {
  background: var(--accent-soft);
}
.mine {
  border-bottom: 2px solid var(--gold);
}
.known {
  color: var(--ok);
}
.unknown {
  border-bottom: 1px dashed var(--muted);
}
.legend {
  display: flex;
  gap: 1rem;
}
.finish {
  display: flex;
  gap: 0.8rem;
  align-items: center;
  flex-wrap: wrap;
}
.side {
  position: sticky;
  top: 0;
}
.choices {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.6rem;
}
.chip.active {
  border-color: var(--accent);
  color: var(--accent);
}
</style>
