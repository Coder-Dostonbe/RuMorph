<script setup lang="ts">
// Line icons drawn on a 24 × 24 grid; colour follows the text colour.
import type { IconName } from "../app/nav";

defineProps<{ name: IconName }>();
</script>

<template>
  <svg class="icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8"
    stroke-linecap="round" stroke-linejoin="round">
    <template v-if="name === 'home'">
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5.5 9v11h13V9" />
      <path d="M10 20v-6h4v6" />
    </template>
    <template v-else-if="name === 'search'">
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m15.5 15.5 5 5" />
    </template>
    <template v-else-if="name === 'book'">
      <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z" />
      <path d="M4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5" />
      <path d="M8 7h8M8 11h6" />
    </template>
    <template v-else-if="name === 'cards'">
      <rect x="3" y="6" width="14" height="15" rx="2" />
      <path d="M7 3h12a2 2 0 0 1 2 2v13" />
    </template>
    <template v-else-if="name === 'more'">
      <circle cx="5" cy="12" r="1.4" />
      <circle cx="12" cy="12" r="1.4" />
      <circle cx="19" cy="12" r="1.4" />
    </template>
    <template v-else-if="name === 'user'">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" />
    </template>
    <template v-else-if="name === 'settings'">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1" />
    </template>
    <template v-else>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6M12 7.5v.5" />
    </template>
  </svg>
</template>

<style scoped>
.icon {
  width: 1.25rem;
  height: 1.25rem;
  flex: none;
}
</style>
