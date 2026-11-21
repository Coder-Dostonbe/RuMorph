<script setup lang="ts">
// Language and theme. The server address is in the admin panel (src/admin/AdminServer.vue).
import { isLocale, localeNames, locales, locale, useI18n } from "../i18n";
import { themes, useSettings, type Theme } from "../stores/settings";

const m = useI18n();
const settings = useSettings();

function onLocale(event: Event): void {
  const value = (event.target as HTMLSelectElement).value;
  if (isLocale(value)) void settings.setLocale(value);
}
</script>

<template>
  <section class="page">
    <h1>{{ m.settings.title }}</h1>

    <div class="card">
      <div class="field">
        <label for="locale">{{ m.settings.language }}</label>
        <select id="locale" class="input" :value="locale" @change="onLocale">
          <option v-for="code in locales" :key="code" :value="code">{{ localeNames[code] }}</option>
        </select>
      </div>

      <fieldset class="field">
        <legend>{{ m.settings.theme }}</legend>
        <div class="segmented">
          <button v-for="t in themes" :key="t" type="button" class="seg" :class="{ active: settings.theme === t }"
            :aria-pressed="settings.theme === t" @click="settings.setTheme(t as Theme)">
            {{ m.settings.themes[t] }}
          </button>
        </div>
      </fieldset>
    </div>

  </section>
</template>

<style scoped>
.page {
  max-width: 560px;
  display: grid;
  gap: 1rem;
  align-content: start;
}
fieldset {
  border: none;
  padding: 0;
  margin: 0;
}
legend {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 0.35rem;
}
</style>
