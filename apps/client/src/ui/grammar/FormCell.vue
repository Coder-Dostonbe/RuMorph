<script setup lang="ts">
// The forms in one table cell. The form being analysed is highlighted; rare, variant and
// rule-built forms are marked in words, not only by colour.
import { cellIndices, type Cell } from "../../core/grammar";
import { useI18n } from "../../i18n";

// quiet: no per-form marks (a whole section that is marked once, like the compound future).
const props = defineProps<{ cells: Cell[]; selected?: number | null; quiet?: boolean }>();
const m = useI18n();

function isSelected(cell: Cell): boolean {
  return props.selected != null && cellIndices(cell).includes(props.selected);
}
</script>

<template>
  <span v-if="cells.length === 0" class="none" :title="m.analyze.noForm">—</span>
  <span v-else class="forms">
    <span v-for="(cell, i) in cells" :key="i" class="form"
      :class="{ selected: isSelected(cell), rare: cell.rare, variant: cell.variant }">
      <span lang="ru">{{ cell.form }}</span>
      <template v-if="quiet" />
      <small v-else-if="cell.rare" class="mark">{{ m.analyze.rare }}</small>
      <small v-else-if="cell.variant" class="mark">{{ m.analyze.variant }}</small>
      <small v-else-if="cell.constructed" class="mark">{{ m.analyze.constructed }}</small>
    </span>
  </span>
</template>

<style scoped>
.forms {
  display: flex;
  flex-wrap: wrap;
  gap: 0.15rem 0.6rem;
}
.form {
  display: inline-flex;
  align-items: baseline;
  gap: 0.3rem;
  border-radius: 6px;
  padding: 0 0.25rem;
  margin: 0 -0.25rem;
}
.form.selected {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 700;
  box-shadow: inset 0 0 0 1px var(--accent);
}
.form.rare,
.form.variant {
  color: var(--muted);
}
.mark {
  font-size: 0.72rem;
  color: var(--muted);
  font-weight: 500;
}
.none {
  color: var(--muted);
}
</style>
