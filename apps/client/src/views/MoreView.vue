<script setup lang="ts">
// Every section, for the phone layout where the bottom bar holds only the main ones.
import { NAV } from "../app/nav";
import { useI18n } from "../i18n";
import AppIcon from "../ui/AppIcon.vue";

const m = useI18n();
</script>

<template>
  <section class="page">
    <h1>{{ m.more.title }}</h1>
    <nav class="list" :aria-label="m.nav.menu">
      <RouterLink v-for="item in NAV" :key="item.to" :to="item.to" class="item">
        <AppIcon :name="item.icon" />
        <span>{{ item.label(m) }}</span>
      </RouterLink>
    </nav>
  </section>
</template>

<style scoped>
.page {
  max-width: 640px;
}
.list {
  display: grid;
  gap: 0.4rem;
}
.item {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.85rem 1rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  text-decoration: none;
  font-weight: 600;
}
.item:hover {
  border-color: var(--accent);
}
</style>
