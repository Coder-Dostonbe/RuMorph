<script setup lang="ts">
// Word analysis: one word, or a preposition and a word. Everything runs in tilsim_core on the
// device, so it works offline. The engine's status is shown as it is: several readings stay
// several, and an unknown word is an error with suggestions, never a guess.
import { computed, nextTick, ref, watch } from "vue";
import { CoreError } from "../core/client";
import { grammar, type Analysis, type LexemeInfo, type PhraseAnalysis, type Reading } from "../core/grammar";
import VocabEditor from "../ui/VocabEditor.vue";
import LexemeDetail from "../ui/grammar/LexemeDetail.vue";
import { format, locale, useI18n } from "../i18n";
import { useCore } from "../stores/core";
import { useGrammar } from "../stores/grammar";
import StatusBadge from "../ui/StatusBadge.vue";

const m = useI18n();
const core = useCore();
const g = useGrammar();

const query = ref("");
const lastText = ref("");
const busy = ref(false);
const failure = ref("");
const inputError = ref("");
const result = ref<Analysis | PhraseAnalysis | null>(null);
const selected = ref<Reading | null>(null);
const lexeme = ref<LexemeInfo | null>(null);
const detailOpen = ref(false);
const detail = ref<HTMLElement | null>(null);

const phrase = computed(() => (result.value && "preposition" in result.value ? result.value : null));
const heading = computed(() => {
  const r = result.value;
  if (!r) return "";
  return "preposition" in r ? `${r.preposition} ${r.word}` : r.word || r.input;
});
const tone = computed(() =>
  result.value?.status === "ok" ? "ok" : result.value?.status === "ambiguous" ? "warn" : "err",
);
const source = computed(() => {
  const info = g.lexicon;
  const src = info?.packages[0]?.source;
  if (!info || !src) return "";
  return format(m.value.analyze.source, { name: src.name, license: src.license, lexemes: info.lexemes, forms: info.forms });
});

function describeError(e: unknown): string {
  return e instanceof CoreError ? `${e.code}: ${e.message}` : String(e);
}

async function run(text = query.value): Promise<void> {
  const words = text.trim().split(/\s+/).filter(Boolean);
  inputError.value = "";
  failure.value = "";
  if (words.length > 2) {
    inputError.value = m.value.analyze.tooManyWords;
    return;
  }
  busy.value = true;
  lastText.value = text;
  try {
    const lang = locale.value;
    const [first = "", second] = words;
    result.value = second !== undefined ? await grammar.phrase(first, second, lang) : await grammar.analyze(first, lang);
    const readings = result.value.readings;
    const previous = selected.value;
    const keep = previous ? readings.find((r) => r.lexeme === previous.lexeme && r.form_index === previous.form_index) : undefined;
    selected.value = keep ?? (readings.length === 1 ? readings[0] ?? null : null);
    detailOpen.value = selected.value !== null;
  } catch (e) {
    failure.value = format(m.value.analyze.callFailed, { error: describeError(e) });
  } finally {
    busy.value = false;
  }
}

async function open(reading: Reading): Promise<void> {
  selected.value = reading;
  detailOpen.value = true;
  await nextTick();
  detail.value?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function suggest(text: string): void {
  query.value = text;
  void run(text);
}

// Engine messages are rendered in the interface language: analyse again when it changes.
watch(locale, () => {
  if (result.value) void run(lastText.value);
});

const word = computed(() =>
  lexeme.value && selected.value && lexeme.value.id === selected.value.lexeme
    ? { id: lexeme.value.id, lemma: lexeme.value.lemma, pos: lexeme.value.pos }
    : null,
);
</script>

<template>
  <section class="page">
    <h1>{{ m.analyze.title }}</h1>
    <p class="muted intro">{{ m.analyze.intro }}</p>

    <div v-if="core.status === 'failed'" class="alert err">{{ format(m.analyze.coreFailed, { error: core.error }) }}</div>
    <div v-else-if="core.status !== 'ready'" class="alert warn">{{ m.analyze.coreLoading }}</div>

    <form class="card search" @submit.prevent="run()">
      <label for="word" class="visually-hidden">{{ m.analyze.label }}</label>
      <input id="word" v-model="query" class="input" lang="ru" autocomplete="off" autocapitalize="off"
        spellcheck="false" maxlength="60" :placeholder="m.analyze.placeholder" :aria-invalid="inputError !== ''" />
      <button class="btn primary" type="submit" :disabled="core.status !== 'ready' || busy || query.trim() === ''">
        {{ m.analyze.submit }}
      </button>
    </form>
    <div v-if="inputError" class="alert err">{{ inputError }}</div>
    <div v-if="failure" class="alert err">{{ failure }}</div>

    <div v-if="result" class="layout">
      <div class="results">
        <article class="card">
          <header class="head">
            <h2 lang="ru">{{ heading }}</h2>
            <StatusBadge :tone="tone" :label="m.analyze.status[result.status]" />
          </header>

          <div v-for="w in result.warnings" :key="w" class="alert warn">{{ w }}</div>
          <div v-for="e in result.errors" :key="e.code + e.message" class="alert err">{{ e.message }}</div>
          <div v-if="result.suggestions.length" class="suggestions">
            <span class="muted small">{{ m.analyze.suggestions }}</span>
            <button v-for="s in result.suggestions" :key="s" type="button" class="btn chip" lang="ru" @click="suggest(s)">
              {{ s }}
            </button>
          </div>

          <div v-if="phrase && phrase.governs.length" class="governs small">
            <span class="muted">{{ format(m.analyze.governs, { prep: phrase.preposition }) }}:</span>
            <ul>
              <li v-for="gv in phrase.governs" :key="gv.case">
                <strong>{{ g.name(gv.case) }}</strong> — {{ gv.meaning }}
                <span class="muted" lang="ru">({{ gv.example }})</span>
              </li>
            </ul>
          </div>
          <p v-if="result.status === 'ambiguous'" class="muted small">{{ m.analyze.ambiguousNote }}</p>
        </article>

        <article v-if="result.readings.length" class="card">
          <h3>{{ m.analyze.readings }}</h3>
          <ul class="readings">
            <li v-for="(r, i) in result.readings" :key="`${r.lexeme}:${r.form_index}:${i}`"
              :class="{ active: selected?.lexeme === r.lexeme && selected?.form_index === r.form_index }">
              <div class="reading-main">
                <span class="form" lang="ru">{{ r.form }}</span>
                <span class="muted small">{{ m.analyze.lemma }}: <span lang="ru">{{ r.lemma }}</span></span>
              </div>
              <p class="desc">{{ r.description }}</p>
              <p v-if="r.government" class="small gov">{{ g.name(r.government.case) }} — {{ r.government.meaning }}</p>
              <p v-for="n in r.notes" :key="n" class="small note">{{ n }}</p>
              <button type="button" class="btn link" @click="open(r)">{{ m.analyze.openTable }}</button>
            </li>
          </ul>
        </article>
      </div>

      <div v-if="detailOpen && selected" ref="detail">
        <LexemeDetail :id="selected.lexeme" :selected="selected.form_index" closable
          @close="detailOpen = false" @loaded="lexeme = $event">
          <VocabEditor v-if="word" :word="word" />
        </LexemeDetail>
      </div>
    </div>

    <p v-if="source" class="muted small source">{{ source }}</p>
  </section>
</template>

<style scoped>
.page {
  max-width: 1180px;
}
.intro {
  max-width: 70ch;
}
.search {
  display: flex;
  gap: 0.6rem;
  margin-bottom: 0.9rem;
  padding: 0.8rem;
}
.search .input {
  font-size: 1.05rem;
}
.search .btn {
  white-space: nowrap;
}
.layout {
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
  gap: 1rem;
  align-items: start;
}
@media (max-width: 860px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }
}
.results {
  display: grid;
  gap: 1rem;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 0.6rem;
}
.head h2 {
  margin: 0;
  font-size: 1.35rem;
}
h3 {
  font-size: 0.95rem;
  margin: 0 0 0.5rem;
}
.table-title {
  margin-top: 1.1rem;
}
.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
  margin-bottom: 0.6rem;
}
.chip {
  min-height: 2rem;
  padding: 0 0.7rem;
  font-weight: 600;
}
.governs ul {
  margin: 0.3rem 0 0.6rem;
  padding-left: 1.1rem;
}
.governs li {
  margin-bottom: 0.2rem;
}
.readings {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.6rem;
}
.readings li {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0.6rem 0.75rem;
}
.readings li.active {
  border-color: var(--accent);
  box-shadow: inset 3px 0 0 var(--accent);
}
.reading-main {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: baseline;
}
.form {
  font-weight: 700;
  font-size: 1.05rem;
}
.desc,
.gov,
.note {
  margin: 0.2rem 0 0;
}
.desc {
  font-size: 0.9rem;
}
.gov {
  color: var(--accent);
}
.note {
  color: var(--warn);
}
.readings .btn.link {
  margin-top: 0.35rem;
  font-size: 0.88rem;
}
.detail {
  min-width: 0;
}
.source {
  margin-top: 1.2rem;
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
</style>
