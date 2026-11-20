<script setup lang="ts">
import { computed } from "vue";
import { compact } from "./app/platform";
import { useI18n } from "./i18n";
import AppIcon from "./ui/AppIcon.vue";

const m = useI18n();

const nav = computed(() => [
  { to: "/", label: m.value.nav.home, icon: "home" as const },
  { to: "/account", label: m.value.nav.account, icon: "user" as const },
  { to: "/settings", label: m.value.nav.settings, icon: "settings" as const },
  { to: "/about", label: m.value.nav.about, icon: "info" as const },
]);
</script>

<template>
  <div class="shell" :class="{ compact }">
    <aside v-if="!compact" class="sidebar">
      <div class="brand">
        <img src="/brand/tilsim-b.svg" alt="" class="logo" />
        <div>
          <div class="name">{{ m.app.name }}</div>
          <div class="tagline">{{ m.app.tagline }}</div>
        </div>
      </div>
      <nav :aria-label="m.nav.menu">
        <RouterLink v-for="item in nav" :key="item.to" :to="item.to" class="side-link">
          <AppIcon :name="item.icon" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
    </aside>

    <main class="content">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>

    <nav v-if="compact" class="bottom-nav" :aria-label="m.nav.menu">
      <RouterLink v-for="item in nav" :key="item.to" :to="item.to" class="bottom-link">
        <AppIcon :name="item.icon" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
  height: 100%;
  width: 100%;
  overflow: hidden;
}
.shell.compact {
  grid-template-columns: 1fr;
  grid-template-rows: 1fr auto;
}

.sidebar {
  background: var(--brand);
  border-right: 1px solid var(--border);
  overflow-y: auto;
  color: var(--on-brand);
  padding: 1.25rem 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0 0.5rem;
}
.logo {
  width: 42px;
  height: 42px;
}
.name {
  font-weight: 700;
  font-size: 1.15rem;
  letter-spacing: 0.01em;
}
.tagline {
  font-size: 0.8rem;
  color: var(--on-brand-muted);
}
.side-link {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.6rem 0.75rem;
  border-radius: var(--radius-sm);
  color: var(--on-brand-muted);
  text-decoration: none;
  font-weight: 550;
  transition: background 150ms var(--ease), color 150ms var(--ease);
}
.side-link:hover {
  background: rgb(255 255 255 / 6%);
  color: var(--on-brand);
}
.side-link.router-link-exact-active {
  background: rgb(60 194 188 / 16%);
  color: var(--on-brand);
  box-shadow: inset 3px 0 0 var(--gold);
}

.content {
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 2rem clamp(1rem, 4vw, 3rem);
}
.compact .content {
  padding: 1.25rem 1rem calc(1.25rem + env(safe-area-inset-top));
}

.bottom-nav {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  background: var(--surface);
  border-top: 1px solid var(--border);
  padding-bottom: env(safe-area-inset-bottom);
}
.bottom-link {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
  min-height: 3.6rem;
  justify-content: center;
  color: var(--muted);
  text-decoration: none;
  font-size: 0.72rem;
  font-weight: 600;
}
.bottom-link.router-link-exact-active {
  color: var(--accent);
}

.page-enter-active,
.page-leave-active {
  transition: opacity 160ms var(--ease), transform 160ms var(--ease);
}
.page-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.page-leave-to {
  opacity: 0;
}
</style>
