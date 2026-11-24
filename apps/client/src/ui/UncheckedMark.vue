<script setup lang="ts">
// The mark next to a translation nobody has checked yet (a draft shipped with the app).
import { useI18n } from "../i18n";

const m = useI18n();
</script>

<template>
  <span class="unchecked" :title="m.common.uncheckedHint">{{ m.common.unchecked }}</span>
</template>

<style scoped>
.unchecked {
  display: inline-block;
  padding: 0.05rem 0.45rem;
  border-radius: 999px;
  border: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.72rem;
  font-weight: 500;
  line-height: 1.5;
  vertical-align: middle;
  white-space: nowrap;
}
</style>
