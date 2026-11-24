<script setup lang="ts">
// One button, as in an ordinary dictionary: put the word on the learner's flashcards, or take it
// off. Adding saves the word to "My words" and makes the Russian → Uzbek card, and the
// Uzbek → Russian card too when the word has a translation (that card asks with it).
import { computed, ref } from "vue";
import type { VocabularyRow } from "../data/userData";
import { format, useI18n } from "../i18n";
import { useCards } from "../stores/cards";
import { useTranslations } from "../stores/translations";
import { useVocabulary, type WordRef } from "../stores/vocabulary";
import { callFailed } from "./failure";

const props = defineProps<{ word: WordRef }>();
const emit = defineEmits<{ saved: [row: VocabularyRow] }>();
const m = useI18n();
const vocab = useVocabulary();
const cards = useCards();
const tr = useTranslations();
void vocab.load();
void cards.load();

const added = computed(() => vocab.byLexeme.has(props.word.id));
const busy = ref(false);
const failure = ref("");

async function add(): Promise<void> {
  busy.value = true;
  failure.value = "";
  try {
    const existing = vocab.byLexeme.get(props.word.id);
    const row = await vocab.save(props.word, {
      note: existing?.note ?? "", examples: existing?.examples ?? [], status: existing?.status ?? "learning",
    });
    await cards.add(props.word.id, "ru_uz");
    if (tr.get(props.word.id) !== null) await cards.add(props.word.id, "uz_ru");
    emit("saved", row);
  } catch (e) {
    failure.value = format(m.value.dictionary.saveFailed, { error: callFailed(m.value, e) });
  } finally {
    busy.value = false;
  }
}

async function remove(): Promise<void> {
  busy.value = true;
  failure.value = "";
  try {
    await cards.remove(props.word.id, "ru_uz");
    await cards.remove(props.word.id, "uz_ru");
    await vocab.remove(props.word.id);
  } catch (e) {
    failure.value = format(m.value.dictionary.saveFailed, { error: callFailed(m.value, e) });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="cards-action">
    <button v-if="!added" class="btn primary" type="button" :disabled="busy" @click="add">
      {{ m.dictionary.addToCards }}
    </button>
    <template v-else>
      <span class="done">{{ m.dictionary.inCards }}</span>
      <button class="btn" type="button" :disabled="busy" @click="remove">{{ m.dictionary.removeFromCards }}</button>
    </template>
    <p v-if="failure" class="alert err" role="alert">{{ failure }}</p>
  </div>
</template>

<style scoped>
.cards-action {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  margin: 0.4rem 0 0.9rem;
}
.done {
  font-weight: 600;
  color: var(--accent);
}
.alert {
  flex-basis: 100%;
  margin: 0;
}
</style>
