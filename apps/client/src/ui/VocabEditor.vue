<script setup lang="ts">
// The learner's own entry for a word: note, examples, learning status, flashcards.
// The translation is not theirs to write while the app is in testing: it comes from the admin
// (src/stores/translations.ts) and is shown above, in the word's header.
import { computed, ref, watch } from "vue";
import type { Example, VocabularyRow } from "../data/userData";
import { format, useI18n } from "../i18n";
import { callFailed } from "./failure";
import { useCards } from "../stores/cards";
import { useTranslations } from "../stores/translations";
import { useVocabulary, type WordRef } from "../stores/vocabulary";

const props = defineProps<{ word: WordRef }>();
const emit = defineEmits<{ saved: [row: VocabularyRow] }>();
const m = useI18n();
const vocab = useVocabulary();
const cards = useCards();
void cards.load();

const tr = useTranslations();
const directions = ["ru_uz", "uz_ru"] as const;
// The Uzbek → Russian card asks with the translation, so it needs one.
const hasTranslation = computed(() => tr.get(props.word.id) !== null);

async function toggleCard(direction: (typeof directions)[number]): Promise<void> {
  if (cards.find(props.word.id, direction)) await cards.remove(props.word.id, direction);
  else await cards.add(props.word.id, direction);
}

const existing = computed(() => vocab.byLexeme.get(props.word.id) ?? null);
const note = ref("");
const examples = ref<Example[]>([]);
const status = ref<VocabularyRow["status"]>("learning");
const savedAt = ref("");
const failure = ref("");
const busy = ref(false);

function reset(): void {
  const row = existing.value;
  note.value = row?.note ?? "";
  examples.value = row ? row.examples.map((e) => ({ ...e })) : [];
  status.value = row?.status ?? "learning";
  savedAt.value = "";
  failure.value = "";
}
watch(() => props.word.id, reset, { immediate: true });
watch(() => vocab.loaded, reset);

async function save(): Promise<void> {
  busy.value = true;
  failure.value = "";
  try {
    const row = await vocab.save(props.word, {
      note: note.value, examples: examples.value, status: status.value,
    });
    savedAt.value = new Date().toLocaleTimeString();
    emit("saved", row);
  } catch (e) {
    failure.value = format(m.value.dictionary.saveFailed, { error: callFailed(m.value, e) });
  } finally {
    busy.value = false;
  }
}

async function remove(): Promise<void> {
  busy.value = true;
  try {
    await vocab.remove(props.word.id);
    reset();
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <form class="editor" @submit.prevent="save">
    <h3>{{ existing ? m.dictionary.myEntry : m.dictionary.addToMine }}</h3>
    <div class="field">
      <label :for="`note-${word.id}`">{{ m.dictionary.note }}</label>
      <textarea :id="`note-${word.id}`" v-model="note" class="input area" rows="2" maxlength="1000" />
    </div>
    <fieldset class="field">
      <legend>{{ m.dictionary.examples }}</legend>
      <div v-for="(ex, i) in examples" :key="i" class="example">
        <input v-model="ex.ru" class="input" lang="ru" maxlength="300" :placeholder="m.dictionary.exampleRu" :aria-label="m.dictionary.exampleRu" />
        <input v-model="ex.uz" class="input" maxlength="300" :placeholder="m.dictionary.exampleUz" :aria-label="m.dictionary.exampleUz" />
        <button type="button" class="btn" :aria-label="m.dictionary.removeExample" @click="examples.splice(i, 1)">×</button>
      </div>
      <button type="button" class="btn link" @click="examples.push({ ru: '', uz: '' })">{{ m.dictionary.addExample }}</button>
    </fieldset>
    <fieldset class="field">
      <legend>{{ m.dictionary.status }}</legend>
      <div class="segmented">
        <button v-for="s in (['learning', 'known'] as const)" :key="s" type="button" class="seg"
          :class="{ active: status === s }" :aria-pressed="status === s" @click="status = s">
          {{ m.dictionary.statuses[s] }}
        </button>
      </div>
    </fieldset>
    <fieldset class="field">
      <legend>{{ m.cards.cardsFor }}</legend>
      <div class="toggles">
        <label v-for="d in directions" :key="d" class="toggle" :class="{ off: d === 'uz_ru' && !hasTranslation && !cards.find(word.id, d) }">
          <input type="checkbox" :checked="!!cards.find(word.id, d)"
            :disabled="d === 'uz_ru' && !hasTranslation && !cards.find(word.id, d)" @change="toggleCard(d)" />
          {{ m.cards.directions[d] }}
        </label>
      </div>
      <p v-if="!hasTranslation" class="muted small">{{ m.cards.needTranslation }}</p>
    </fieldset>
    <div v-if="failure" class="alert err">{{ failure }}</div>
    <div class="actions">
      <button class="btn primary" type="submit" :disabled="busy">{{ m.common.save }}</button>
      <button v-if="existing" class="btn" type="button" :disabled="busy" @click="remove">{{ m.dictionary.removeFromMine }}</button>
      <span v-if="savedAt" class="muted small">{{ m.common.saved }}</span>
    </div>
  </form>
</template>

<style scoped>
.editor {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0.8rem 0.9rem;
  margin: 0.6rem 0 0.4rem;
}
h3 {
  margin: 0 0 0.6rem;
  font-size: 0.95rem;
}
fieldset {
  border: none;
  padding: 0;
  margin: 0 0 0.9rem;
}
legend {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 0.35rem;
}
.area {
  min-height: 3.2rem;
  padding: 0.5rem 0.8rem;
  resize: vertical;
}
.example {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 0.4rem;
  margin-bottom: 0.4rem;
}
@media (max-width: 520px) {
  .example {
    grid-template-columns: 1fr auto;
  }
  .example input:nth-child(2) {
    grid-column: 1;
  }
}
.toggles {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 1.2rem;
}
.toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  cursor: pointer;
}
.toggle.off {
  color: var(--muted);
  cursor: default;
}
.toggle input {
  width: 1.1rem;
  height: 1.1rem;
  accent-color: var(--accent);
}
.field > .btn.link {
  justify-self: start;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: center;
}
</style>
