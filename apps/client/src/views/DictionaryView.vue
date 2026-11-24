<script setup lang="ts">
// Dictionary: every word of the lexicon in alphabetical order, in two directions. Russian → Uzbek is
// searched by the Russian word (its form or beginning), Uzbek → Russian by the Uzbek translation.
// A letter column on the right jumps to that letter's section. Translations come from
// stores/translations.ts. Runs offline.
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { POS_FILTERS, type LexemeInfo, type PosFilter } from "../core/grammar";
import { keyValue } from "../data/keyValue";
import {
  compareRu, compareUz, ruInitial, sections, uzHead, uzInitial, uzMatch, RU_LETTERS, UZ_LETTERS, type Section,
} from "../dictionary/alphabet";
import { allWords, searchAll, type ListedWord } from "../dictionary/words";
import { format, locale, useI18n } from "../i18n";
import { useCore } from "../stores/core";
import { useGrammar } from "../stores/grammar";
import { useTranslations } from "../stores/translations";
import { useVocabulary } from "../stores/vocabulary";
import VocabEditor from "../ui/VocabEditor.vue";
import LexemeDetail from "../ui/grammar/LexemeDetail.vue";
import UncheckedMark from "../ui/UncheckedMark.vue";
import WordDialog from "../ui/WordDialog.vue";
import { callFailed, coreFailed } from "../ui/failure";

type Direction = "ru_uz" | "uz_ru";
interface UzRow {
  word: ListedWord;
  translation: string;
  head: string;
}

const m = useI18n();
const core = useCore();
const g = useGrammar();
const vocab = useVocabulary();
const tr = useTranslations();
const route = useRoute();
const router = useRouter();

const tab = ref<"all" | "mine">(route.query.tab === "mine" ? "mine" : "all");
const dir = ref<Direction>(route.query.dir === "uz_ru" ? "uz_ru" : "ru_uz");
const query = ref(typeof route.query.q === "string" ? route.query.q : "");
const pos = ref<PosFilter | "">("");
const words = ref<ListedWord[] | null>(null);
const hits = ref<ListedWord[] | null>(null);
const busy = ref(false);
const failure = ref("");
const openId = ref<string | null>(typeof route.query.word === "string" ? route.query.word : null);
const openInfo = ref<LexemeInfo | null>(null);

const q = computed(() => query.value.trim());
const mine = computed(() => vocab.find(query.value));
/** The query is written in the other direction's alphabet: offer to switch instead of finding nothing. */
const mismatch = computed<Direction | null>(() => {
  if (dir.value === "ru_uz" && /[a-z]/i.test(q.value) && !/[а-яё]/i.test(q.value)) return "uz_ru";
  if (dir.value === "uz_ru" && /[а-яё]/i.test(q.value)) return "ru_uz";
  return null;
});

// Russian → Uzbek
const ruSections = computed<Section<ListedWord>[]>(() =>
  words.value ? sections([...words.value].sort((a, b) => compareRu(a.lemma, b.lemma)), (w) => ruInitial(w.lemma), RU_LETTERS) : [],
);
/** Exact forms first (книги → книга), then the words beginning with the query, alphabetically. */
const ruHits = computed(() => {
  if (!hits.value) return [];
  const forms = hits.value.filter((h) => h.match === "form");
  const rest = hits.value.filter((h) => h.match !== "form").sort((a, b) => compareRu(a.lemma, b.lemma));
  return [...forms, ...rest];
});

// Uzbek → Russian: every word with a translation, under its Uzbek headword.
const uzRows = computed<UzRow[]>(() => {
  if (!words.value) return [];
  const rows: UzRow[] = [];
  for (const word of words.value) {
    const translation = tr.get(word.id);
    if (translation) rows.push({ word, translation, head: uzHead(translation) });
  }
  return rows.sort((a, b) => compareUz(a.head, b.head) || compareRu(a.word.lemma, b.word.lemma));
});
const uzSections = computed(() => sections(uzRows.value, (r) => uzInitial(r.head), UZ_LETTERS));
/** Meanings equal to the query first, then meanings beginning with it, then the rest. */
const uzHits = computed(() =>
  uzRows.value
    .map((row) => ({ row, score: uzMatch(q.value, row.translation) }))
    .filter((x) => x.score >= 0)
    .sort((a, b) => a.score - b.score)
    .map((x) => x.row),
);

const browsing = computed(() => tab.value === "all" && !q.value);
const letters = computed<string[]>(() => [...(dir.value === "ru_uz" ? RU_LETTERS : UZ_LETTERS), "#"]);
const present = computed(() => new Set((dir.value === "ru_uz" ? ruSections.value : uzSections.value).map((s) => s.letter)));
const shown = computed(() => {
  if (tab.value !== "all") return 0;
  if (dir.value === "ru_uz") return q.value ? ruHits.value.length : words.value?.length ?? 0;
  return q.value ? uzHits.value.length : uzRows.value.length;
});

let seq = 0;
let timer: ReturnType<typeof setTimeout> | undefined;

/** Reads the word list (once per part of speech) and, for a Russian query, every match. */
async function refresh(): Promise<void> {
  if (core.status !== "ready" || tab.value !== "all") return;
  const mySeq = ++seq;
  busy.value = true;
  failure.value = "";
  try {
    const p = pos.value || null;
    const list = await allWords(locale.value, p);
    const found = dir.value === "ru_uz" && q.value && !mismatch.value ? await searchAll(q.value, locale.value, p) : null;
    if (mySeq !== seq) return;
    words.value = list;
    hits.value = found;
  } catch (e) {
    if (mySeq === seq) failure.value = callFailed(m.value, e);
  } finally {
    if (mySeq === seq) busy.value = false;
  }
}

watch(query, () => {
  clearTimeout(timer);
  timer = setTimeout(() => void refresh(), 180);
});
watch([() => core.status, locale, tab, pos, dir], () => void refresh());
watch(dir, (d) => void keyValue.set("dictionary.direction", d));
watch([tab, dir, query, openId], () => {
  void router.replace({
    query: {
      ...(tab.value === "mine" ? { tab: "mine" } : {}),
      ...(dir.value === "uz_ru" ? { dir: "uz_ru" } : {}),
      ...(query.value ? { q: query.value } : {}),
      ...(openId.value ? { word: openId.value } : {}),
    },
  });
});
// The page stays mounted when only its query changes (a link to another word): follow it.
watch(() => route.query, (rq) => {
  if (typeof rq.q === "string" && rq.q !== query.value) query.value = rq.q;
  if (typeof rq.word === "string" && rq.word !== openId.value) open(rq.word);
  if ((rq.tab === "mine") !== (tab.value === "mine")) tab.value = rq.tab === "mine" ? "mine" : "all";
});
onMounted(async () => {
  void vocab.load();
  void tr.load();
  if (route.query.dir === undefined) {
    const saved = await keyValue.get("dictionary.direction");
    if (saved === "ru_uz" || saved === "uz_ru") dir.value = saved;
  }
  void refresh();
});

function open(id: string): void {
  openId.value = id;
  openInfo.value = null;
}

const openWord = computed(() =>
  openInfo.value && openInfo.value.id === openId.value
    ? { id: openInfo.value.id, lemma: openInfo.value.lemma, pos: openInfo.value.pos }
    : null,
);

// Letter column: a tap jumps to the letter; on a phone the finger can also slide along the column.
const sectionEls = new Map<string, HTMLElement>();
const current = ref<string | null>(null);
const sliding = ref(false);

function setSection(letter: string, el: unknown): void {
  if (el instanceof HTMLElement) sectionEls.set(letter, el);
  else sectionEls.delete(letter);
}

function jump(letter: string): void {
  if (!present.value.has(letter)) return;
  current.value = letter;
  sectionEls.get(letter)?.scrollIntoView({ block: "start" });
}

function letterAt(x: number, y: number): string | null {
  const el = document.elementFromPoint(x, y)?.closest<HTMLElement>("[data-letter]");
  return el?.dataset.letter ?? null;
}

function slideStart(e: PointerEvent): void {
  if (e.pointerType === "mouse") return;
  sliding.value = true;
  (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  slideMove(e);
}

function slideMove(e: PointerEvent): void {
  if (!sliding.value) return;
  const letter = letterAt(e.clientX, e.clientY);
  if (letter && letter !== current.value) jump(letter);
}

function slideEnd(): void {
  sliding.value = false;
}
</script>

<template>
  <section class="page">
    <h1>{{ m.dictionary.title }}</h1>
    <p class="muted intro">{{ m.dictionary.intro }}</p>
    <div v-if="core.status === 'failed'" class="alert err">{{ coreFailed(m, core.error) }}</div>
    <div v-else-if="core.status !== 'ready'" class="alert warn">{{ m.analyze.coreLoading }}</div>

    <div class="card controls">
      <div class="segmented" role="tablist">
        <button type="button" role="tab" class="seg" :class="{ active: tab === 'all' }" :aria-selected="tab === 'all'" @click="tab = 'all'">
          {{ m.dictionary.tabAll }}
        </button>
        <button type="button" role="tab" class="seg" :class="{ active: tab === 'mine' }" :aria-selected="tab === 'mine'" @click="tab = 'mine'">
          {{ m.dictionary.tabMine }} ({{ vocab.rows.length }})
        </button>
      </div>
      <div v-if="tab === 'all'" class="segmented" role="radiogroup" :aria-label="m.dictionary.direction">
        <button type="button" role="radio" class="seg" :class="{ active: dir === 'ru_uz' }" :aria-checked="dir === 'ru_uz'" @click="dir = 'ru_uz'">
          {{ m.dictionary.dirRuUz }}
        </button>
        <button type="button" role="radio" class="seg" :class="{ active: dir === 'uz_ru' }" :aria-checked="dir === 'uz_ru'" @click="dir = 'uz_ru'">
          {{ m.dictionary.dirUzRu }}
        </button>
      </div>
      <input v-model="query" class="input" type="search" autocomplete="off" spellcheck="false" maxlength="60"
        :lang="tab === 'all' ? (dir === 'ru_uz' ? 'ru' : 'uz') : undefined"
        :placeholder="tab === 'mine' ? m.dictionary.searchMine : dir === 'ru_uz' ? m.dictionary.searchAll : m.dictionary.searchUz"
        :aria-label="m.dictionary.search" />
      <select v-if="tab === 'all'" v-model="pos" class="input" :aria-label="m.dictionary.pos">
        <option value="">{{ m.dictionary.allPos }}</option>
        <option v-for="p in POS_FILTERS" :key="p" :value="p">{{ g.name(p === 'VERB' ? 'INFN' : p) }}</option>
      </select>
    </div>

    <div v-if="failure" class="alert err">{{ failure }}</div>

    <template v-if="tab === 'all'">
      <div v-if="mismatch" class="alert warn switch">
        <span>{{ mismatch === 'uz_ru' ? m.dictionary.latinQuery : m.dictionary.cyrillicQuery }}</span>
        <button type="button" class="btn small-btn" @click="dir = mismatch">
          {{ mismatch === 'uz_ru' ? m.dictionary.dirUzRu : m.dictionary.dirRuUz }}
        </button>
      </div>
      <p v-else-if="words === null || (dir === 'uz_ru' && !tr.loaded)" class="muted small">{{ m.dictionary.loadingWords }}</p>
      <p v-else class="muted small">
        {{ format(q ? m.dictionary.found : m.dictionary.total, { n: shown }) }}
      </p>

      <!-- Browsing: letter sections and the letter column. -->
      <div v-if="browsing && words" class="browse">
        <div class="sections">
          <template v-if="dir === 'ru_uz'">
            <section v-for="s in ruSections" :key="'ru' + s.letter" :ref="(el) => setSection(s.letter, el)" class="letter-section">
              <h2 class="letter" lang="ru">{{ s.letter }}</h2>
              <ul class="words" :style="{ containIntrinsicSize: `auto ${Math.ceil(s.items.length / 2) * 64}px` }">
                <li v-for="w in s.items" :key="w.id">
                  <button type="button" class="word" :class="{ active: w.id === openId }" @click="open(w.id)">
                    <span class="lemma" lang="ru">{{ w.lemma }}</span>
                    <span v-if="tr.get(w.id)" class="tr" lang="uz">{{ tr.get(w.id) }}</span>
                    <UncheckedMark v-if="tr.entry(w.id)?.verified === false" />
                    <span class="muted small desc">{{ w.description }}</span>
                  </button>
                </li>
              </ul>
            </section>
          </template>
          <template v-else>
            <section v-for="s in uzSections" :key="'uz' + s.letter" :ref="(el) => setSection(s.letter, el)" class="letter-section">
              <h2 class="letter" lang="uz">{{ s.letter }}</h2>
              <ul class="words" :style="{ containIntrinsicSize: `auto ${Math.ceil(s.items.length / 2) * 64}px` }">
                <li v-for="r in s.items" :key="r.word.id">
                  <button type="button" class="word" :class="{ active: r.word.id === openId }" @click="open(r.word.id)">
                    <span class="lemma" lang="uz">{{ r.translation }}</span>
                    <span class="tr" lang="ru">{{ r.word.lemma }}</span>
                    <UncheckedMark v-if="tr.entry(r.word.id)?.verified === false" />
                    <span class="muted small desc">{{ r.word.description }}</span>
                  </button>
                </li>
              </ul>
            </section>
          </template>
        </div>

        <nav class="index" :aria-label="m.dictionary.alphabet" @pointerdown="slideStart" @pointermove="slideMove"
          @pointerup="slideEnd" @pointercancel="slideEnd">
          <button v-for="l in letters.filter((x) => x !== '#' || present.has('#'))" :key="l" type="button" class="index-letter"
            :class="{ off: !present.has(l), current: current === l }" :data-letter="l" :disabled="!present.has(l)"
            :aria-label="format(m.dictionary.jumpTo, { letter: l })" @click="jump(l)">
            {{ l }}
          </button>
        </nav>
        <div v-if="sliding && current" class="bubble" aria-hidden="true">{{ current }}</div>
      </div>

      <!-- Searching: one list, best matches first. -->
      <template v-else-if="q && !mismatch">
        <ul v-if="dir === 'ru_uz'" class="words">
          <li v-for="w in ruHits" :key="w.id">
            <button type="button" class="word" :class="{ active: w.id === openId }" @click="open(w.id)">
              <span class="lemma" lang="ru">{{ w.lemma }}</span>
              <span v-if="tr.get(w.id)" class="tr" lang="uz">{{ tr.get(w.id) }}</span>
              <UncheckedMark v-if="tr.entry(w.id)?.verified === false" />
              <span class="muted small desc">{{ w.description }}</span>
            </button>
          </li>
        </ul>
        <ul v-else class="words">
          <li v-for="r in uzHits" :key="r.word.id">
            <button type="button" class="word" :class="{ active: r.word.id === openId }" @click="open(r.word.id)">
              <span class="lemma" lang="uz">{{ r.translation }}</span>
              <span class="tr" lang="ru">{{ r.word.lemma }}</span>
              <UncheckedMark v-if="tr.entry(r.word.id)?.verified === false" />
              <span class="muted small desc">{{ r.word.description }}</span>
            </button>
          </li>
        </ul>
        <p v-if="!busy && shown === 0 && words" class="muted">{{ m.dictionary.nothing }}</p>
      </template>
    </template>

    <template v-else>
      <p v-if="vocab.rows.length === 0" class="muted">{{ m.dictionary.mineEmpty }}</p>
      <ul v-else class="words">
        <li v-for="row in mine" :key="row.id">
          <button type="button" class="word" :class="{ active: row.lexeme_id === openId }" @click="open(row.lexeme_id)">
            <span class="lemma" lang="ru">{{ row.lemma }}</span>
            <span v-if="tr.get(row.lexeme_id)" class="tr" lang="uz">{{ tr.get(row.lexeme_id) }}</span>
            <UncheckedMark v-if="tr.entry(row.lexeme_id)?.verified === false" />
            <span class="muted small">{{ m.dictionary.statuses[row.status] }}</span>
          </button>
        </li>
      </ul>
      <p v-if="vocab.rows.length && mine.length === 0" class="muted">{{ m.dictionary.nothing }}</p>
    </template>

    <WordDialog v-if="openId" @close="openId = null">
      <LexemeDetail :id="openId" closable @close="openId = null" @loaded="openInfo = $event">
        <VocabEditor v-if="openWord" :word="openWord" />
      </LexemeDetail>
    </WordDialog>

    <p v-if="g.lexicon" class="muted small source">
      {{ format(m.dictionary.sources, {
        name: g.lexicon.packages[0]?.source.name ?? '', license: g.lexicon.packages[0]?.source.license ?? '',
        lexemes: g.lexicon.lexemes,
      }) }}
    </p>
  </section>
</template>

<style scoped>
.page {
  max-width: 1180px;
}
.intro {
  max-width: 70ch;
}
.controls {
  display: grid;
  gap: 0.6rem;
  padding: 0.8rem;
  margin-bottom: 0.8rem;
}
.controls .segmented {
  display: flex;
}
.controls .seg {
  flex: 1;
}
.switch {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.8rem;
}
.small-btn {
  padding: 0.3rem 0.8rem;
}

/* The list and, on its right, the letter column that stays in view while the list scrolls. */
.browse {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.5rem;
  align-items: start;
}
.letter-section {
  margin-bottom: 0.6rem;
}
.letter {
  position: sticky;
  top: 0;
  z-index: 1;
  margin: 0 0 0.4rem;
  padding: 0.3rem 0.2rem;
  font-size: 1.15rem;
  color: var(--accent);
  background: var(--bg);
  border-bottom: 1px solid var(--border);
}
.letter-section .words {
  /* Sections off screen are not laid out until they come near, so the full list stays fast on a phone. */
  content-visibility: auto;
}

.index {
  position: sticky;
  top: 0.5rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: calc(100dvh - 9rem);
  max-height: 46rem;
  min-height: 16rem;
  padding: 0.25rem 0;
  border-radius: 999px;
  background: var(--surface);
  border: 1px solid var(--border);
  touch-action: none;
  user-select: none;
}
.index-letter {
  flex: 1 1 0;
  min-height: 0;
  max-height: 1.6rem;
  min-width: 1.9rem;
  padding: 0 0.3rem;
  border: 0;
  background: none;
  color: var(--accent);
  font: inherit;
  font-size: clamp(0.6rem, 1.9dvh, 0.82rem);
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  white-space: nowrap;
}
.index-letter:hover:not(:disabled),
.index-letter.current {
  background: var(--accent-soft);
}
.index-letter.off {
  color: var(--muted);
  opacity: 0.45;
  cursor: default;
}
.bubble {
  position: fixed;
  top: 40%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 20;
  min-width: 4.5rem;
  padding: 0.6rem 0.9rem;
  border-radius: var(--radius);
  background: var(--accent);
  color: var(--on-accent);
  font-size: 2.2rem;
  font-weight: 700;
  text-align: center;
  pointer-events: none;
}

.words {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 0.45rem;
}
.word {
  width: 100%;
  text-align: left;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.25rem 0.6rem;
  padding: 0.55rem 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font: inherit;
  cursor: pointer;
}
.word:hover {
  border-color: var(--accent);
}
.word.active {
  border-color: var(--accent);
  box-shadow: inset 3px 0 0 var(--accent);
}
.lemma {
  font-weight: 700;
  font-size: 1.02rem;
}
.tr {
  color: var(--accent);
  font-weight: 600;
}
.desc {
  flex-basis: 100%;
}
.source {
  margin-top: 1.2rem;
}
</style>
