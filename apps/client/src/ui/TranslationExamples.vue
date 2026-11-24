<script setup lang="ts">
// A word's example sentences: Russian, with the Uzbek translation under it.
import { computed } from "vue";
import { useI18n } from "../i18n";
import { useTranslations } from "../stores/translations";

const props = defineProps<{ id: string }>();
const m = useI18n();
const tr = useTranslations();
const examples = computed(() => tr.entry(props.id)?.examples ?? []);
</script>

<template>
  <section v-if="examples.length" class="examples">
    <h3>{{ m.dictionary.examples }}</h3>
    <ul>
      <li v-for="(ex, i) in examples" :key="i">
        <p class="ru" lang="ru">{{ ex.ru }}</p>
        <p class="uz">{{ ex.uz }}</p>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.examples {
  margin: 0.4rem 0 0.8rem;
}
h3 {
  margin: 0 0 0.4rem;
  font-size: 0.95rem;
}
ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.5rem;
}
li {
  padding: 0.5rem 0.7rem;
  border-left: 3px solid var(--accent);
  background: var(--surface-2, var(--surface));
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}
p {
  margin: 0;
}
.ru {
  font-weight: 600;
}
.uz {
  color: var(--muted);
  font-size: 0.92rem;
}
</style>
