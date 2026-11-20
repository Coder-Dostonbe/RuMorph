<script setup lang="ts">
// One multiple-choice question from the engine (exercises.py): the prompt for its kind, the four
// (or two, three) options, and after an answer whether it was right, with the rule behind it.
import { computed } from "vue";
import type { Question } from "../core/grammar";
import { format, useI18n } from "../i18n";
import { useGrammar } from "../stores/grammar";

const props = defineProps<{ question: Question; chosen: number | null; showRule?: boolean }>();
const emit = defineEmits<{ choose: [index: number] }>();
const m = useI18n();
const g = useGrammar();

const q = computed(() => props.question);
const grammemes = computed(() => q.value.prompt.grammemes ?? []);
const person = computed(() => {
  const [, p, n] = grammemes.value;
  return (m.value.tests.persons as Record<string, string>)[`${p}.${n}`] ?? "";
});

function optionText(option: string): string {
  return q.value.option_kind === "grammeme" ? g.name(option) : option;
}

function state(i: number): string {
  if (props.chosen === null) return "";
  if (i === q.value.answer) return "right";
  return i === props.chosen ? "wrong" : "dim";
}
const rule = computed(() => (q.value.rule ? g.rules[q.value.rule] ?? null : null));
</script>

<template>
  <article class="card question">
    <p class="muted small">{{ m.tests.kindHints[q.kind] }}</p>

    <div class="prompt">
      <template v-if="q.kind === 'case_form'">
        <span class="lemma" lang="ru">{{ q.lemma }}</span>
        <span class="arrow">→</span>
        <span class="target">{{ grammemes.map((c) => g.name(c)).join(", ") }}</span>
      </template>
      <template v-else-if="q.kind === 'conjugation'">
        <span class="lemma" lang="ru">{{ person }} ___</span>
        <span class="muted">(<span lang="ru">{{ q.lemma }}</span>; {{ g.name(grammemes[0] ?? "") }})</span>
      </template>
      <template v-else-if="q.kind === 'preposition'">
        <span class="lemma" lang="ru">{{ q.prompt.preposition }} ___</span>
        <span class="muted">(<span lang="ru">{{ q.lemma }}</span>; {{ g.name(grammemes[0] ?? "") }})</span>
      </template>
      <template v-else>
        <span class="lemma" lang="ru">{{ q.lemma }}</span>
        <span v-if="q.kind !== 'translation'" class="muted">— {{ m.tests.which }}</span>
      </template>
    </div>

    <div class="options" :class="{ two: q.options.length === 2 }">
      <button v-for="(option, i) in q.options" :key="i" type="button" class="btn option" :class="state(i)"
        :disabled="chosen !== null" :lang="q.option_kind === 'grammeme' || q.kind === 'translation' ? undefined : 'ru'"
        @click="emit('choose', i)">
        <span class="key" aria-hidden="true">{{ i + 1 }}</span>{{ optionText(option) }}
      </button>
    </div>

    <template v-if="chosen !== null">
      <p v-if="chosen === q.answer" class="verdict ok">{{ m.tests.right }}</p>
      <p v-else class="verdict err">{{ format(m.tests.wrong, { answer: optionText(q.options[q.answer] ?? "") }) }}</p>
      <p v-if="showRule && rule" class="muted small">
        {{ m.tests.rule }}: <RouterLink :to="{ path: '/grammar', query: { rule: rule.id } }">{{ rule.name }}</RouterLink>
      </p>
    </template>
  </article>
</template>

<style scoped>
.question {
  display: grid;
  gap: 0.7rem;
}
.question > p {
  margin: 0;
}
.prompt {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.5rem;
  font-size: 1.15rem;
}
.lemma {
  font-size: 1.6rem;
  font-weight: 700;
}
.target {
  font-weight: 600;
  color: var(--accent);
}
.options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
}
.option {
  justify-content: flex-start;
  min-height: 3rem;
  font-size: 1.02rem;
  gap: 0.6rem;
}
.key {
  font-size: 0.75rem;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0 0.3rem;
}
.option.right {
  border-color: var(--ok);
  background: var(--ok-soft);
  color: var(--ok);
  opacity: 1;
}
.option.wrong {
  border-color: var(--err);
  background: var(--err-soft);
  color: var(--err);
  opacity: 1;
}
.option.dim {
  opacity: 0.55;
}
.verdict {
  font-weight: 700;
}
.verdict.ok {
  color: var(--ok);
}
.verdict.err {
  color: var(--err);
}
@media (max-width: 420px) {
  .options {
    grid-template-columns: 1fr;
  }
}
</style>
