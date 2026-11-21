<script setup lang="ts">
// Spell and grammar check of a Russian text (tilsim_core/spell.py), on the device.
import { computed, ref, watch } from "vue";
import { grammar, type SpellIssue, type SpellResult } from "../core/grammar";
import { format, locale, useI18n } from "../i18n";
import { useCore } from "../stores/core";
import { useGrammar } from "../stores/grammar";
import { callFailed, coreFailed } from "../ui/failure";

const MAX = 20000;
const m = useI18n();
const core = useCore();
const g = useGrammar();

const text = ref("");
const checkedText = ref("");
const result = ref<SpellResult | null>(null);
const failure = ref("");
const busy = ref(false);

const stale = computed(() => result.value !== null && text.value !== checkedText.value);

async function run(): Promise<void> {
  failure.value = "";
  if (text.value.length > MAX) {
    failure.value = format(m.value.spell.limit, { n: MAX });
    return;
  }
  busy.value = true;
  try {
    const snapshot = text.value;
    result.value = await grammar.spellcheck(snapshot, locale.value);
    checkedText.value = snapshot;
  } catch (e) {
    failure.value = callFailed(m.value, e);
  } finally {
    busy.value = false;
  }
}
watch(locale, () => {
  if (result.value && !stale.value) void run();
});

/** The checked text cut into plain parts and marked issues, for display. */
const pieces = computed(() => {
  const r = result.value;
  if (!r) return [];
  const out: { text: string; issue?: SpellIssue; index?: number }[] = [];
  let at = 0;
  const sorted = [...r.issues].sort((a, b) => a.start - b.start);
  sorted.forEach((issue, index) => {
    if (issue.start < at) return;               // two issues on one word: the first is marked
    out.push({ text: checkedText.value.slice(at, issue.start) });
    out.push({ text: checkedText.value.slice(issue.start, issue.end), issue, index });
    at = issue.end;
  });
  out.push({ text: checkedText.value.slice(at) });
  return out;
});

async function apply(issue: SpellIssue, suggestion: string): Promise<void> {
  if (stale.value) return;
  text.value = checkedText.value.slice(0, issue.replace_start) + suggestion + checkedText.value.slice(issue.replace_end);
  await run();
}

const hasUnknown = computed(() => result.value?.issues.some((i) => i.level === "unknown") ?? false);
</script>

<template>
  <section class="page">
    <h1>{{ m.spell.title }}</h1>
    <p class="muted intro">{{ m.spell.intro }}</p>
    <div v-if="core.status === 'failed'" class="alert err">{{ coreFailed(m, core.error) }}</div>
    <div v-else-if="core.status !== 'ready'" class="alert warn">{{ m.analyze.coreLoading }}</div>

    <div class="card">
      <textarea v-model="text" class="input area" lang="ru" rows="7" spellcheck="false" :maxlength="MAX"
        :placeholder="m.spell.placeholder" :aria-label="m.spell.title" />
      <div class="row">
        <button type="button" class="btn primary" :disabled="core.status !== 'ready' || busy || !text.trim()" @click="run">
          {{ m.spell.check }}
        </button>
        <span class="muted small">{{ text.length }} / {{ MAX }}</span>
      </div>
    </div>
    <div v-if="failure" class="alert err">{{ failure }}</div>

    <template v-if="result">
      <div v-if="stale" class="alert warn">{{ m.spell.stale }}</div>
      <p class="muted small">{{ format(m.spell.summary, { words: result.words, known: result.known, issues: result.issues.length }) }}</p>
      <div v-if="result.issues.length === 0" class="alert ok">{{ m.spell.clean }}</div>
      <template v-else>
        <div class="card marked" lang="ru"><template v-for="(p, i) in pieces" :key="i"><mark v-if="p.issue"
          :class="p.issue.level" :title="m.spell.levels[p.issue.level]">{{ p.text }}</mark><template v-else>{{ p.text }}</template></template></div>
        <ul class="issues">
          <li v-for="(issue, i) in result.issues" :key="i" class="card issue" :class="issue.level">
            <div class="head">
              <span class="word" lang="ru">{{ issue.word }}</span>
              <span class="level">{{ m.spell.levels[issue.level] }}</span>
            </div>
            <p v-for="msg in issue.messages" :key="msg" class="small">{{ msg }}</p>
            <div v-if="issue.suggestions.length" class="suggestions">
              <button v-for="s in issue.suggestions" :key="s" type="button" class="btn chip" lang="ru" :disabled="stale"
                :title="m.spell.apply" @click="apply(issue, s)">{{ s }}</button>
            </div>
          </li>
        </ul>
        <p v-if="hasUnknown && g.lexicon" class="muted small">{{ format(m.spell.unknownNote, { n: g.lexicon.lexemes }) }}</p>
      </template>
    </template>
  </section>
</template>

<style scoped>
.page {
  max-width: 860px;
  display: grid;
  gap: 0.9rem;
  align-content: start;
}
.intro {
  margin: 0;
}
.area {
  min-height: 9rem;
  padding: 0.7rem 0.8rem;
  resize: vertical;
  font-size: 1.02rem;
  line-height: 1.6;
}
.row {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  margin-top: 0.6rem;
}
.marked {
  white-space: pre-wrap;
  line-height: 1.9;
  font-size: 1.02rem;
}
mark {
  background: none;
  color: inherit;
  border-bottom: 2px solid;
  padding-bottom: 1px;
}
mark.error,
.issue.error .level {
  border-color: var(--err);
  color: var(--err);
}
mark.grammar,
.issue.grammar .level {
  border-color: var(--warn);
  color: var(--warn);
}
mark.unknown {
  border-bottom-style: dashed;
  border-color: var(--muted);
}
mark.note,
mark.repeat {
  border-bottom-style: dotted;
  border-color: var(--accent);
}
.issues {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.5rem;
}
.issue {
  padding: 0.7rem 0.9rem;
}
.issue p {
  margin: 0.25rem 0 0;
}
.head {
  display: flex;
  justify-content: space-between;
  gap: 0.6rem;
  align-items: baseline;
}
.word {
  font-weight: 700;
}
.level {
  font-size: 0.8rem;
  font-weight: 650;
  color: var(--muted);
}
.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.45rem;
}
.chip {
  min-height: 2rem;
  padding: 0 0.7rem;
}
</style>
