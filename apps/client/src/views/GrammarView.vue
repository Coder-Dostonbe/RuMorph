<script setup lang="ts">
// Grammar: every rule the engine knows, grouped by part of speech, with its explanation and the
// dictionary words it applies to (found by the engine's classification, most frequent first),
// and the table of prepositions with their cases.
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { grammar, type Catalog, type CatalogRule, type PrepositionInfo, type RuleExamples } from "../core/grammar";
import { format, locale, useI18n } from "../i18n";
import { useCore } from "../stores/core";
import { useGrammar } from "../stores/grammar";
import FrequencyBadge from "../ui/grammar/FrequencyBadge.vue";
import { callFailed, coreFailed } from "../ui/failure";

const m = useI18n();
const core = useCore();
const g = useGrammar();
const route = useRoute();
const router = useRouter();

const catalog = ref<Catalog | null>(null);
const prepositions = ref<PrepositionInfo[] | null>(null);
const failure = ref("");
const loading = ref(false);
const filter = ref("");
const openRule = ref<string | null>(typeof route.query.rule === "string" ? route.query.rule : null);
const section = ref<"rules" | "prepositions">(route.query.section === "prepositions" ? "prepositions" : "rules");
const examples = ref<RuleExamples | null>(null);
const examplesBusy = ref(false);

function err(e: unknown): string {
  return callFailed(m.value, e);
}

async function load(): Promise<void> {
  if (core.status !== "ready") return;
  loading.value = true;
  failure.value = "";
  try {
    const [c, p] = await Promise.all([grammar.catalog(locale.value), grammar.prepositions(locale.value)]);
    catalog.value = c;
    prepositions.value = p;
    if (openRule.value) await loadExamples(openRule.value);
  } catch (e) {
    failure.value = err(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
watch([() => core.status, locale], load);
watch([openRule, section], () => {
  void router.replace({ query: { ...(section.value === "prepositions" ? { section: "prepositions" } : {}), ...(openRule.value ? { rule: openRule.value } : {}) } });
});
watch(() => route.query.rule, (rule) => {
  if (typeof rule === "string" && rule !== openRule.value) void open(rule);
});

async function loadExamples(rule: string, more = false): Promise<void> {
  examplesBusy.value = true;
  try {
    const offset = more && examples.value ? examples.value.items.length : 0;
    const page = await grammar.ruleExamples(rule, locale.value, offset);
    examples.value = more && examples.value ? { total: page.total, items: [...examples.value.items, ...page.items] } : page;
  } catch (e) {
    failure.value = err(e);
  } finally {
    examplesBusy.value = false;
  }
}

async function open(rule: string): Promise<void> {
  if (openRule.value === rule) {
    openRule.value = null;
    return;
  }
  openRule.value = rule;
  examples.value = null;
  await loadExamples(rule);
}

function matches(rule: CatalogRule): boolean {
  const needle = filter.value.trim().toLocaleLowerCase();
  return !needle || [rule.name, rule.explanation, rule.example].some((t) => t.toLocaleLowerCase().includes(needle));
}

const groups = computed(() =>
  (catalog.value?.groups ?? []).map((group) => ({ ...group, rules: group.rules.filter(matches) })).filter((group) => group.rules.length),
);
const kindLabel = (kind: string): string => (m.value.grammar.kinds as Record<string, string>)[kind] ?? kind;
</script>

<template>
  <section class="page">
    <h1>{{ m.grammar.title }}</h1>
    <p class="muted intro">{{ m.grammar.intro }}</p>
    <div v-if="core.status === 'failed'" class="alert err">{{ coreFailed(m, core.error) }}</div>
    <div v-else-if="core.status !== 'ready'" class="alert warn">{{ m.analyze.coreLoading }}</div>
    <div v-if="failure" class="alert err">{{ failure }}</div>

    <div class="controls">
      <div class="segmented" role="tablist">
        <button type="button" role="tab" class="seg" :class="{ active: section === 'rules' }" :aria-selected="section === 'rules'" @click="section = 'rules'">
          {{ m.grammar.rules }}
        </button>
        <button type="button" role="tab" class="seg" :class="{ active: section === 'prepositions' }" :aria-selected="section === 'prepositions'" @click="section = 'prepositions'">
          {{ m.grammar.prepositions }}
        </button>
      </div>
      <input v-if="section === 'rules'" v-model="filter" class="input" type="search" :placeholder="m.grammar.filter" :aria-label="m.grammar.filter" />
    </div>

    <p v-if="loading && !catalog" class="muted">{{ m.grammar.building }}</p>

    <template v-if="section === 'rules'">
      <section v-for="group in groups" :key="group.id" class="group">
        <h2>{{ m.grammar.groups[group.id] }}</h2>
        <article v-for="rule in group.rules" :key="rule.id" class="card rule" :class="{ open: openRule === rule.id }">
          <button type="button" class="rule-head" :aria-expanded="openRule === rule.id" @click="open(rule.id)">
            <span class="rule-name">{{ rule.name }}</span>
            <span class="muted small">{{ kindLabel(rule.kind) }}<template v-if="rule.words"> · {{ format(m.grammar.words, { n: rule.words }) }}</template></span>
          </button>
          <div v-if="openRule === rule.id" class="rule-body">
            <p>{{ rule.explanation }}</p>
            <p v-if="rule.example" class="example" lang="ru">{{ rule.example }}</p>
            <p class="muted small">{{ m.grammar.reference }}: {{ rule.reference }}<template v-if="rule.review_status === 'pending_specialist_review'"> · {{ m.grammar.pending }}</template></p>
            <template v-if="rule.words">
              <h3>{{ m.grammar.inDictionary }}</h3>
              <ul v-if="examples" class="examples">
                <li v-for="item in examples.items" :key="item.id">
                  <RouterLink :to="{ path: '/dictionary', query: { q: item.lemma, word: item.id } }" class="ex">
                    <span lang="ru" class="detail">{{ item.detail }}</span>
                    <FrequencyBadge :rank="item.rank" />
                  </RouterLink>
                </li>
              </ul>
              <span v-else class="skeleton" style="width: 40%" />
              <button v-if="examples && examples.items.length < examples.total" type="button" class="btn link"
                :disabled="examplesBusy" @click="loadExamples(rule.id, true)">
                {{ format(m.dictionary.more, { n: examples.total - examples.items.length }) }}
              </button>
            </template>
          </div>
        </article>
      </section>
      <p v-if="catalog && groups.length === 0" class="muted">{{ m.dictionary.nothing }}</p>
    </template>

    <div v-else-if="prepositions" class="card scroll">
      <table class="preps">
        <thead>
          <tr>
            <th scope="col">{{ m.grammar.preposition }}</th>
            <th scope="col">{{ m.grammar.case }}</th>
            <th scope="col">{{ m.grammar.meaning }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="p in prepositions" :key="p.preposition">
            <tr v-for="(gv, i) in p.governs" :key="gv.case" :class="{ rare: gv.rare }">
              <th v-if="i === 0" scope="row" :rowspan="p.governs.length" lang="ru" class="prep">{{ p.preposition }}</th>
              <td>{{ g.name(gv.case) }}</td>
              <td>
                {{ gv.meaning }}
                <span class="muted" lang="ru">({{ gv.example }})</span>
                <small v-if="gv.rare" class="muted"> · {{ m.analyze.rare }}</small>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.page {
  max-width: 900px;
  display: grid;
  gap: 0.9rem;
  align-content: start;
}
.intro {
  max-width: 70ch;
  margin: 0;
}
.controls {
  display: grid;
  gap: 0.6rem;
}
.controls .segmented {
  justify-self: start;
}
.group h2 {
  margin: 0.8rem 0 0.5rem;
}
.rule {
  padding: 0;
  margin-bottom: 0.5rem;
}
.rule.open {
  border-color: var(--accent);
}
.rule-head {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.3rem 1rem;
  padding: 0.85rem 1.1rem;
  background: none;
  border: none;
  color: var(--text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.rule-name {
  font-weight: 650;
}
.rule-body {
  padding: 0 1.1rem 1rem;
}
.example {
  color: var(--accent);
  font-weight: 600;
}
h3 {
  font-size: 0.92rem;
  margin: 0.8rem 0 0.4rem;
}
.examples {
  list-style: none;
  padding: 0;
  margin: 0 0 0.5rem;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.35rem;
}
.ex {
  display: flex;
  flex-wrap: wrap;
  gap: 0.2rem 0.5rem;
  align-items: baseline;
  padding: 0.4rem 0.6rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  color: var(--text);
  text-decoration: none;
}
.ex:hover {
  border-color: var(--accent);
}
.detail {
  font-weight: 600;
}
.scroll {
  overflow-x: auto;
}
.preps {
  width: 100%;
  border-collapse: collapse;
}
.preps th,
.preps td {
  text-align: left;
  padding: 0.45rem 0.6rem;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
.preps thead th {
  font-size: 0.8rem;
  color: var(--muted);
}
.prep {
  font-weight: 700;
  font-size: 1.05rem;
}
.rare td {
  color: var(--muted);
}
</style>
