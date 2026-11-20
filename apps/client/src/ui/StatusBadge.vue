<script setup lang="ts">
defineProps<{ tone: "ok" | "warn" | "err" | "muted"; label: string }>();
</script>

<template>
  <span class="badge" :class="tone"><span class="dot" aria-hidden="true" />{{ label }}</span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  white-space: nowrap;
}
.dot {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: currentColor;
}
.ok { color: var(--ok); background: var(--ok-soft); }
.warn { color: var(--warn); background: var(--warn-soft); }
.err { color: var(--err); background: var(--err-soft); }
.muted { color: var(--muted); background: var(--surface-2); }
</style>
