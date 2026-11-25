<script setup lang="ts">
// One word from the lexicon: its pronunciation, its translation, what it is, how frequent, the rules that explain it
// and every form.
// Used by the analysis page and the dictionary.
import { computed, ref, watch } from "vue";
import { grammar, type LexemeInfo } from "../../core/grammar";
import { locale, useI18n } from "../../i18n";
import FrequencyBadge from "./FrequencyBadge.vue";
import PronounceButton from "../PronounceButton.vue";
import ParadigmTable from "./ParadigmTable.vue";
import ProfileView from "./ProfileView.vue";
import TranslationExamples from "../TranslationExamples.vue";
import TranslationLine from "../TranslationLine.vue";
import { callFailed } from "../failure";

const props = defineProps<{ id: string; selected?: number | null; closable?: boolean }>();
const emit = defineEmits<{ close: []; loaded: [info: LexemeInfo] }>();
const m = useI18n();

const info = ref<LexemeInfo | null>(null);
const failure = ref("");

async function load(): Promise<void> {
  failure.value = "";
  try {
    info.value = await grammar.lexeme(props.id, locale.value);
    emit("loaded", info.value);
  } catch (e) {
    info.value = null;
    failure.value = callFailed(m.value, e);
  }
}

watch([() => props.id, locale], () => void load(), { immediate: true });
const selectedIndex = computed(() => (info.value?.id === props.id ? props.selected ?? null : null));
</script>

<template>
  <article class="card detail">
    <div v-if="failure" class="alert err">{{ failure }}</div>
    <template v-else-if="info">
      <header class="head">
        <div>
          <h2 lang="ru">{{ info.lemma }}</h2>
          <PronounceButton :lemma="info.lemma" />
          <TranslationLine :word="{ id: info.id, lemma: info.lemma }" />
          <p class="muted small">{{ info.description }}</p>
          <FrequencyBadge :rank="info.rank" :frequency="info.frequency" />
        </div>
        <button v-if="closable" type="button" class="btn" @click="emit('close')">{{ m.analyze.close }}</button>
      </header>
      <TranslationExamples :id="info.id" />
      <slot />
      <h3>{{ m.analyze.rules }}</h3>
      <ProfileView :profile="info.profile" />
      <h3 class="table-title">{{ m.analyze.table }}</h3>
      <ParadigmTable :table="info.table" :selected="selectedIndex" />
    </template>
    <span v-else class="skeleton" style="width: 50%" />
  </article>
</template>

<style scoped>
.detail {
  min-width: 0;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 0.6rem;
}
.head > div {
  flex: 1;
  min-width: 0;
}
.head h2 {
  margin: 0;
  font-size: 1.35rem;
}
.head p {
  margin: 0.1rem 0 0.35rem;
}
h3 {
  font-size: 0.95rem;
  margin: 1rem 0 0.5rem;
}
</style>
