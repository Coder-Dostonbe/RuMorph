<script setup lang="ts">
// Dictionary: every word of the lexicon (search by form or beginning, or browse by frequency),
// and the learner's own words. Translations come from the admin (stores/translations.ts). Runs offline.
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { grammar, POS_FILTERS, type LexemeInfo, type PosFilter, type SearchResult } from "../core/grammar";
import { format, locale, useI18n } from "../i18n";
import { useCore } from "../stores/core";
import { useGrammar } from "../stores/grammar";
import { useTranslations } from "../stores/translations";
import { useVocabulary } from "../stores/vocabulary";
import VocabEditor from "../ui/VocabEditor.vue";
import FrequencyBadge from "../ui/grammar/FrequencyBadge.vue";
import LexemeDetail from "../ui/grammar/LexemeDetail.vue";
import UncheckedMark from "../ui/UncheckedMark.vue";
import WordDialog from "../ui/WordDialog.vue";
import { callFailed, coreFailed } from "../ui/failure";

const PAGE = 40;
const m = useI18n();
const core = useCore();
const g = useGrammar();
const vocab = useVocabulary();
const tr = useTranslations();
const route = useRoute();
const router = useRouter();

const tab = ref<"all" | "mine">(route.query.tab === "mine" ? "mine" : "all");
const query = ref(typeof route.query.q === "string" ? route.query.q : "");
const pos = ref<PosFilter | "">("");
const result = ref<SearchResult | null>(null);
const busy = ref(false);
const failure = ref("");
const openId = ref<string | null>(typeof route.query.word === "string" ? route.query.word : null);
const openInfo = ref<LexemeInfo | null>(null);

const latin = computed(() => /[a-z]/i.test(query.value));
const mine = computed(() => vocab.find(query.value));
// Latin letters: the query is Uzbek, so the translations are searched instead of the lexicon.
const byTranslation = computed(() => (latin.value ? tr.search(query.value).slice(0, 200) : []));

let timer: ReturnType<typeof setTimeout> | undefined;
let seq = 0;

async function search(append = false): Promise<void> {
  if (core.status !== "ready" || tab.value !== "all") return;
  const mySeq = ++seq;
  busy.value = true;
  failure.value = "";
  try {
    const offset = append && result.value ? result.value.items.length : 0;
    const page = await grammar.search(latin.value ? "" : query.value, locale.value, { pos: pos.value || null, limit: PAGE, offset });
    if (mySeq !== seq) return;
    result.value = append && result.value ? { total: page.total, items: [...result.value.items, ...page.items] } : page;
  } catch (e) {
    if (mySeq === seq) failure.value = callFailed(m.value, e);
  } finally {
    if (mySeq === seq) busy.value = false;
  }
}

watch([query, pos], () => {
  clearTimeout(timer);
  timer = setTimeout(() => void search(), 180);
});
watch([() => core.status, locale, tab], () => void search());
watch([tab, query, openId], () => {
  void router.replace({ query: { ...(tab.value === "mine" ? { tab: "mine" } : {}), ...(query.value ? { q: query.value } : {}), ...(openId.value ? { word: openId.value } : {}) } });
});
// The page stays mounted when only its query changes (a link to another word): follow it.
watch(() => route.query, (q) => {
  if (typeof q.q === "string" && q.q !== query.value) query.value = q.q;
  if (typeof q.word === "string" && q.word !== openId.value) open(q.word);
  if ((q.tab === "mine") !== (tab.value === "mine")) tab.value = q.tab === "mine" ? "mine" : "all";
});
onMounted(() => {
  void vocab.load();
  void tr.load();
  void search();
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
</script>

<template>
  <section class="page">
    <h1>{{ m.dictionary.title }}</h1>
    <p class="muted intro">{{ m.dictionary.intro }}</p>
    <div v-if="core.status === 'failed'" class="alert err">{{ coreFailed(m, core.error) }}</div>
    <div v-else-if="core.status !== 'ready'" class="alert warn">{{ m.analyze.coreLoading }}</div>

    <div class="layout">
      <div class="list-col">
        <div class="card controls">
          <div class="segmented" role="tablist">
            <button type="button" role="tab" class="seg" :class="{ active: tab === 'all' }" :aria-selected="tab === 'all'" @click="tab = 'all'">
              {{ m.dictionary.tabAll }}
            </button>
            <button type="button" role="tab" class="seg" :class="{ active: tab === 'mine' }" :aria-selected="tab === 'mine'" @click="tab = 'mine'">
              {{ m.dictionary.tabMine }} ({{ vocab.rows.length }})
            </button>
          </div>
          <input v-model="query" class="input" type="search" autocomplete="off" spellcheck="false" maxlength="60"
            :placeholder="tab === 'all' ? m.dictionary.searchAll : m.dictionary.searchMine" :aria-label="m.dictionary.search" />
          <select v-if="tab === 'all'" v-model="pos" class="input" :aria-label="m.dictionary.pos">
            <option value="">{{ m.dictionary.allPos }}</option>
            <option v-for="p in POS_FILTERS" :key="p" :value="p">{{ g.name(p === 'VERB' ? 'INFN' : p) }}</option>
          </select>
        </div>

        <div v-if="failure" class="alert err">{{ failure }}</div>

        <template v-if="tab === 'all'">
          <template v-if="latin">
            <p class="muted small">{{ m.dictionary.latinHint }} {{ format(m.dictionary.translatedFound, { n: byTranslation.length }) }}</p>
            <ul class="words">
              <li v-for="e in byTranslation" :key="e.lexeme_id">
                <button type="button" class="word" :class="{ active: e.lexeme_id === openId }" @click="open(e.lexeme_id)">
                  <span class="lemma" lang="ru">{{ e.lemma }}</span>
                  <span class="tr">{{ e.translation }}</span>
                </button>
              </li>
            </ul>
          </template>
          <p v-else-if="result" class="muted small">
            {{ query ? format(m.dictionary.found, { n: result.total }) : m.dictionary.browsing }}
          </p>
          <ul v-if="result && !latin" class="words">
            <li v-for="item in result.items" :key="item.id">
              <button type="button" class="word" :class="{ active: item.id === openId }" @click="open(item.id)">
                <span class="lemma" lang="ru">{{ item.lemma }}</span>
                <span v-if="tr.get(item.id)" class="tr">{{ tr.get(item.id) }}</span>
                <UncheckedMark v-if="tr.entry(item.id)?.verified === false" />
                <span class="muted small desc">{{ item.description }}</span>
                <FrequencyBadge :rank="item.rank" />
              </button>
            </li>
          </ul>
          <p v-if="result && !latin && result.items.length === 0" class="muted">{{ m.dictionary.nothing }}</p>
          <button v-if="result && !latin && result.items.length < result.total" type="button" class="btn more" :disabled="busy"
            @click="search(true)">
            {{ format(m.dictionary.more, { n: result.total - result.items.length }) }}
          </button>
        </template>

        <template v-else>
          <p v-if="vocab.rows.length === 0" class="muted">{{ m.dictionary.mineEmpty }}</p>
          <ul v-else class="words">
            <li v-for="row in mine" :key="row.id">
              <button type="button" class="word" :class="{ active: row.lexeme_id === openId }" @click="open(row.lexeme_id)">
                <span class="lemma" lang="ru">{{ row.lemma }}</span>
                <span v-if="tr.get(row.lexeme_id)" class="tr">{{ tr.get(row.lexeme_id) }}</span>
                <UncheckedMark v-if="tr.entry(row.lexeme_id)?.verified === false" />
                <span class="muted small">{{ m.dictionary.statuses[row.status] }}</span>
              </button>
            </li>
          </ul>
          <p v-if="vocab.rows.length && mine.length === 0" class="muted">{{ m.dictionary.nothing }}</p>
        </template>
      </div>

      <WordDialog v-if="openId" @close="openId = null">
        <LexemeDetail :id="openId" closable @close="openId = null" @loaded="openInfo = $event">
          <VocabEditor v-if="openWord" :word="openWord" />
        </LexemeDetail>
      </WordDialog>
    </div>

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
/* A word opens in a window over the page (WordDialog), so the list takes the whole width. */
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1rem;
  align-items: start;
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
.words {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
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
.more {
  margin-top: 0.7rem;
  width: 100%;
}
.source {
  margin-top: 1.2rem;
}
</style>
