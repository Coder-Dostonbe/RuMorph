<script setup lang="ts">
// A word's translation where a learner sees the word. While the app is in testing only the admin
// enters translations: in the admin mode this line is a field; otherwise it shows the
// translation, or "the app is in test mode" when the word has none yet.
import { computed, onMounted, ref, watch } from "vue";
import { format, useI18n } from "../i18n";
import { useAdmin } from "../stores/admin";
import { MAX_TRANSLATION, useTranslations } from "../stores/translations";
import { errorDetail } from "./failure";
import UncheckedMark from "./UncheckedMark.vue";

const props = defineProps<{ word: { id: string; lemma: string } }>();
const m = useI18n();
const admin = useAdmin();
const tr = useTranslations();
onMounted(() => void tr.load());

const text = computed(() => tr.get(props.word.id));
const unchecked = computed(() => tr.entry(props.word.id)?.verified === false);
const draft = ref("");
const saved = ref(false);
const failure = ref("");
watch(text, (t) => (draft.value = t ?? ""), { immediate: true });
watch(() => props.word.id, () => {
  draft.value = text.value ?? "";
  saved.value = false;
  failure.value = "";
});

async function approve(): Promise<void> {
  failure.value = "";
  try {
    await tr.approve(props.word);
  } catch (e) {
    failure.value = format(m.value.admin.saveFailed, { error: errorDetail(e) });
  }
}

async function save(): Promise<void> {
  failure.value = "";
  try {
    await tr.set(props.word, draft.value);
    saved.value = true;
  } catch (e) {
    failure.value = format(m.value.admin.saveFailed, { error: errorDetail(e) });
  }
}
</script>

<template>
  <form v-if="admin.unlocked" class="admin-edit" @submit.prevent="save">
    <label :for="`atr-${word.id}`" class="small">{{ m.admin.editorLabel }}</label>
    <div class="row">
      <input :id="`atr-${word.id}`" v-model="draft" class="input" :maxlength="MAX_TRANSLATION" :placeholder="m.admin.placeholder"
        @input="saved = false" />
      <button class="btn" type="submit" :disabled="draft.trim() === (text ?? '')">{{ m.common.save }}</button>
    </div>
    <div v-if="unchecked" class="row check">
      <UncheckedMark />
      <button class="btn" type="button" :disabled="draft.trim() !== (text ?? '')" @click="approve">{{ m.admin.approve }}</button>
    </div>
    <span class="muted small">{{ saved ? m.common.saved : m.admin.editorHint }}</span>
    <div v-if="failure" class="alert err">{{ failure }}</div>
  </form>
  <p v-else-if="text" class="tr">{{ text }} <UncheckedMark v-if="unchecked" /></p>
  <p v-else class="tr none">{{ m.common.testMode }}</p>
</template>

<style scoped>
.tr {
  margin: 0.2rem 0 0.4rem;
  font-size: 1.05rem;
  font-weight: 600;
}
.tr.none {
  font-size: 0.9rem;
  font-weight: 400;
  color: var(--muted);
  font-style: italic;
}
.admin-edit {
  display: grid;
  gap: 0.25rem;
  margin: 0.3rem 0 0.5rem;
  padding: 0.5rem 0.6rem;
  border: 1px dashed var(--border);
  border-radius: var(--radius-sm);
}
.row {
  display: flex;
  gap: 0.4rem;
}
.check {
  align-items: center;
}
.row .input {
  flex: 1;
  min-width: 0;
}
</style>
