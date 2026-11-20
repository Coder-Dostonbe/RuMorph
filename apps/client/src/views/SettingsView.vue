<script setup lang="ts">
import { computed, ref } from "vue";
import { isValidBaseUrl } from "../api/http";
import { format, isLocale, localeNames, locales, locale, useI18n } from "../i18n";
import { useServer } from "../stores/server";
import { themes, useSettings, type Theme } from "../stores/settings";
import StatusBadge from "../ui/StatusBadge.vue";

const m = useI18n();
const settings = useSettings();
const server = useServer();

const apiDraft = ref(settings.apiUrl);
const apiValid = computed(() => apiDraft.value.trim() === "" || isValidBaseUrl(apiDraft.value));
const apiSaved = ref(false);

async function saveApi(): Promise<void> {
  if (!apiValid.value) return;
  await settings.setApiUrl(apiDraft.value);
  apiDraft.value = settings.apiUrl;
  apiSaved.value = true;
  await server.check();
}

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

    <form class="card" @submit.prevent="saveApi">
      <div class="field">
        <label for="api">{{ m.settings.server }}</label>
        <input id="api" v-model="apiDraft" class="input" inputmode="url" autocomplete="off" spellcheck="false"
          :aria-invalid="!apiValid" @input="apiSaved = false" />
        <span class="muted small">{{ m.settings.serverHint }}</span>
      </div>
      <div class="row">
        <button class="btn primary" type="submit" :disabled="!apiValid">{{ m.common.save }}</button>
        <span v-if="apiSaved && server.state === 'ok'">
          <StatusBadge tone="ok" :label="format(m.home.serverOk, { ms: server.latencyMs ?? 0 })" />
        </span>
        <span v-else-if="apiSaved && server.state === 'unreachable'">
          <StatusBadge tone="err" :label="m.status.offline" />
        </span>
      </div>
    </form>

    <p class="muted small">
      {{ m.settings.storage }}: {{ settings.storageKind === "sqlite" ? m.settings.storageDb : m.settings.storageBrowser }}
    </p>
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
.row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
</style>
