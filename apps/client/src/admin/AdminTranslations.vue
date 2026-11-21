<script setup lang="ts">
// Admin: word translations. Untranslated words come most frequent first, with a field to type
// the translation; translated ones can be searched, corrected or removed. "Export" writes every
// translation to one file, which goes into the next build (tools/translations/merge.py).
import { computed, onMounted, ref, watch } from "vue";
import { grammar, type WordSummary } from "../core/grammar";
import { format, locale, useI18n } from "../i18n";
import { useCore } from "../stores/core";
import { MAX_TRANSLATION, useTranslations } from "../stores/translations";
import { callFailed, errorDetail } from "../ui/failure";

const PAGE = 60;
const m = useI18n();
const core = useCore();
const tr = useTranslations();

const tab = ref<"untranslated" | "translated">("untranslated");
const query = ref("");
const failure = ref("");
const exportNote = ref("");
const exporting = ref(false);

// Untranslated: pages of the frequency list (or of a Russian search) without the translated words.
const seen = ref<WordSummary[]>([]);
const total = ref(0);
const loading = ref(false);
const drafts = ref<Record<string, string>>({});
const untranslated = computed(() => seen.value.filter((w) => !tr.all.has(w.id)));

let seq = 0;
async function loadWords(append = false): Promise<void> {
  if (core.status !== "ready") return;
  const mySeq = ++seq;
  loading.value = true;
  failure.value = "";
  try {
    const cyrillic = /[а-яё]/i.test(query.value) ? query.value : "";
    const page = await grammar.search(cyrillic, locale.value, { limit: PAGE, offset: append ? seen.value.length : 0 });
    if (mySeq !== seq) return;
    seen.value = append ? [...seen.value, ...page.items] : page.items;
    total.value = page.total;
  } catch (e) {
    if (mySeq === seq) failure.value = callFailed(m.value, e);
  } finally {
    if (mySeq === seq) loading.value = false;
  }
}

const translated = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase();
  const list = [...tr.all.values()];
  const hits = needle ? list.filter((e) => e.lemma.toLocaleLowerCase().includes(needle) || e.translation.toLocaleLowerCase().includes(needle)) : list;
  return hits.sort((a, b) => b.updated_at.localeCompare(a.updated_at));
});

let timer: ReturnType<typeof setTimeout> | undefined;
watch(query, () => {
  clearTimeout(timer);
  timer = setTimeout(() => void loadWords(), 200);
});
watch(() => core.status, () => void loadWords());
onMounted(async () => {
  await tr.load();
  void loadWords();
});

async function save(word: { id: string; lemma: string }, text: string): Promise<void> {
  failure.value = "";
  try {
    await tr.set(word, text);
    delete drafts.value[word.id];
  } catch (e) {
    failure.value = format(m.value.admin.saveFailed, { error: errorDetail(e) });
  }
}

async function exportAll(): Promise<void> {
  exporting.value = true;
  exportNote.value = "";
  failure.value = "";
  try {
    const result = await tr.exportAll();
    exportNote.value =
      result.kind === "file" ? format(m.value.admin.exportedFile, { path: result.path })
        : result.kind === "clipboard" ? m.value.admin.exportedClipboard
          : m.value.admin.exportedDownload;
  } catch (e) {
    failure.value = format(m.value.admin.exportFailed, { error: errorDetail(e) });
  } finally {
    exporting.value = false;
  }
}
</script>

<template>
  <div class="card">
    <p class="intro">{{ m.admin.translationsIntro }}</p>
    <p class="muted small">{{ format(m.admin.counts, { total: tr.all.size, bundled: tr.bundledCount, local: tr.localCount }) }}</p>
    <div class="row">
      <button class="btn primary" type="button" :disabled="exporting" @click="exportAll">{{ m.admin.export }}</button>
      <span v-if="exportNote" class="small ok-text">{{ exportNote }}</span>
    </div>
  </div>

  <div class="card">
    <div class="controls">
      <div class="segmented" role="tablist">
        <button type="button" role="tab" class="seg" :class="{ active: tab === 'untranslated' }" :aria-selected="tab === 'untranslated'"
          @click="tab = 'untranslated'">{{ m.admin.untranslated }}</button>
        <button type="button" role="tab" class="seg" :class="{ active: tab === 'translated' }" :aria-selected="tab === 'translated'"
          @click="tab = 'translated'">{{ m.admin.translated }} ({{ tr.all.size }})</button>
      </div>
      <input v-model="query" class="input" type="search" autocomplete="off" spellcheck="false" maxlength="60"
        :placeholder="tab === 'translated' ? m.admin.searchTranslated : m.dictionary.searchAll" :aria-label="m.dictionary.search" />
    </div>
    <div v-if="failure" class="alert err">{{ failure }}</div>

    <template v-if="tab === 'untranslated'">
      <p class="muted small">{{ m.admin.untranslatedHint }}</p>
      <div v-if="core.status !== 'ready'" class="alert warn">{{ m.analyze.coreLoading }}</div>
      <ul class="rows">
        <li v-for="w in untranslated" :key="w.id">
          <div class="word">
            <span class="lemma" lang="ru">{{ w.lemma }}</span>
            <span class="muted small">{{ w.description }}</span>
          </div>
          <form class="edit" @submit.prevent="save(w, drafts[w.id] ?? '')">
            <input v-model="drafts[w.id]" class="input" :maxlength="MAX_TRANSLATION" :placeholder="m.admin.placeholder"
              :aria-label="format('{w}: {p}', { w: w.lemma, p: m.admin.placeholder })" />
            <button class="btn" type="submit" :disabled="!(drafts[w.id] ?? '').trim()">{{ m.common.save }}</button>
          </form>
        </li>
      </ul>
      <p v-if="seen.length && !untranslated.length" class="muted">{{ m.admin.allTranslated }}</p>
      <button v-if="seen.length < total" type="button" class="btn" :disabled="loading" @click="loadWords(true)">
        {{ format(m.dictionary.more, { n: total - seen.length }) }}
      </button>
    </template>

    <template v-else>
      <p v-if="tr.all.size === 0" class="muted">{{ m.admin.noneYet }}</p>
      <ul class="rows">
        <li v-for="e in translated" :key="e.lexeme_id">
          <div class="word">
            <RouterLink class="lemma" lang="ru" :to="{ path: '/dictionary', query: { word: e.lexeme_id } }">{{ e.lemma }}</RouterLink>
          </div>
          <form class="edit" @submit.prevent="save({ id: e.lexeme_id, lemma: e.lemma }, drafts[e.lexeme_id] ?? e.translation)">
            <input class="input" :value="drafts[e.lexeme_id] ?? e.translation" :maxlength="MAX_TRANSLATION"
              :aria-label="format('{w}: {p}', { w: e.lemma, p: m.admin.placeholder })"
              @input="drafts[e.lexeme_id] = ($event.target as HTMLInputElement).value" />
            <button class="btn" type="submit" :disabled="drafts[e.lexeme_id] === undefined">{{ m.common.save }}</button>
            <button class="btn" type="button" @click="save({ id: e.lexeme_id, lemma: e.lemma }, '')">{{ m.admin.remove }}</button>
          </form>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.intro {
  margin: 0 0 0.4rem;
  max-width: 70ch;
}
.row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 0.6rem;
}
.ok-text {
  color: var(--ok);
  overflow-wrap: anywhere;
}
.controls {
  display: grid;
  gap: 0.6rem;
  margin-bottom: 0.6rem;
}
.rows {
  list-style: none;
  margin: 0.4rem 0 0.8rem;
  padding: 0;
}
.rows li {
  display: grid;
  grid-template-columns: minmax(9rem, 14rem) 1fr;
  gap: 0.4rem 0.8rem;
  align-items: center;
  padding: 0.45rem 0;
  border-bottom: 1px solid var(--border);
}
.word {
  display: grid;
  min-width: 0;
}
.lemma {
  font-weight: 600;
}
.edit {
  display: flex;
  gap: 0.4rem;
  min-width: 0;
}
.edit .input {
  flex: 1;
  min-width: 0;
}
@media (max-width: 560px) {
  .rows li {
    grid-template-columns: 1fr;
  }
}
</style>
