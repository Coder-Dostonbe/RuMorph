<script setup lang="ts">
// How common a word is, from its frequency rank in the lexicon (wordfreq): "among the 500 most
// frequent words". Nothing is shown when the frequency is unknown.
import { computed } from "vue";
import { format, useI18n } from "../../i18n";

const props = defineProps<{ rank: number | null | undefined; frequency?: number | null }>();
const m = useI18n();
const BANDS = [100, 500, 1000, 2000, 3000];

const text = computed(() => {
  if (props.rank == null) return "";
  const band = BANDS.find((b) => props.rank! <= b);
  return band ? format(m.value.dictionary.band, { n: band }) : m.value.dictionary.bandRare;
});
const tone = computed(() => (props.rank != null && props.rank <= 1000 ? "top" : "other"));
</script>

<template>
  <span v-if="text" class="freq" :class="tone" :title="format(m.dictionary.rankTitle, { rank: rank ?? 0 })">{{ text }}</span>
</template>

<style scoped>
.freq {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.1rem 0.55rem;
  border-radius: 999px;
  background: var(--surface-2);
  color: var(--muted);
}
.freq.top {
  background: var(--accent-soft);
  color: var(--accent);
}
</style>
