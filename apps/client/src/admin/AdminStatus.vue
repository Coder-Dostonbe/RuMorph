<script setup lang="ts">
// Admin: the state of the grammar module, the account, the server, and the server address
// (moved here from the home page and the settings).
import { computed, onMounted, ref } from "vue";
import { isValidBaseUrl } from "../api/http";
import { format, useI18n } from "../i18n";
import { useCore } from "../stores/core";
import { useServer } from "../stores/server";
import { useSession } from "../stores/session";
import { useSettings } from "../stores/settings";
import StatusBadge from "../ui/StatusBadge.vue";

const m = useI18n();
const core = useCore();
const server = useServer();
const session = useSession();
const settings = useSettings();

onMounted(() => {
  if (server.state === "unknown") void server.check();
});

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
</script>

<template>
  <div class="grid">
    <article class="card">
      <header>
        <h3>{{ m.home.engineCard }}</h3>
        <StatusBadge v-if="core.status === 'ready'" tone="ok" :label="m.status.ready" />
        <StatusBadge v-else-if="core.status === 'failed'" tone="err" :label="m.status.failed" />
        <StatusBadge v-else tone="muted" :label="m.status.loading" />
      </header>
      <p v-if="core.status === 'ready' && core.version" class="small">
        {{ format(m.home.engineReady, { python: core.version.python, core: core.version.core }) }}
      </p>
      <p v-else-if="core.status === 'failed'" class="err-text small">{{ format(m.home.engineFailed, { error: core.error }) }}</p>
      <p v-else class="muted small">{{ m.home.engineLoading }}</p>
    </article>
    <article class="card">
      <header>
        <h3>{{ m.home.accountCard }}</h3>
        <StatusBadge v-if="session.signedIn" tone="ok" :label="m.status.online" />
        <StatusBadge v-else tone="muted" :label="m.status.signedOut" />
      </header>
      <p v-if="session.user" class="small">{{ format(m.home.signedInAs, { email: session.user.email }) }}</p>
      <p v-else class="muted small">{{ m.home.signedOut }}</p>
      <RouterLink to="/account" class="btn link">{{ m.admin.openAccount }}</RouterLink>
    </article>
    <article class="card">
      <header>
        <h3>{{ m.home.serverCard }}</h3>
        <StatusBadge v-if="server.state === 'ok'" tone="ok" :label="m.status.online" />
        <StatusBadge v-else-if="server.state === 'unreachable'" tone="err" :label="m.status.offline" />
        <StatusBadge v-else-if="server.state === 'not_configured'" tone="warn" :label="m.status.notConfigured" />
        <StatusBadge v-else tone="muted" :label="m.status.loading" />
      </header>
      <p v-if="server.state === 'ok'" class="small">{{ format(m.home.serverOk, { ms: server.latencyMs ?? 0 }) }}</p>
      <p v-else-if="server.state === 'not_configured'" class="muted small">{{ m.home.serverNotConfigured }}</p>
      <p v-else-if="server.state === 'unreachable'" class="muted small">{{ format(m.home.serverUnreachable, { error: server.error }) }}</p>
    </article>
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
    {{ m.admin.storage }}: {{ settings.storageKind === "sqlite" ? m.settings.storageDb : m.settings.storageBrowser }}
  </p>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 1rem;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}
h3 {
  margin: 0;
  font-size: 1rem;
}
.row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.err-text {
  color: var(--err);
}
.btn.link {
  padding-left: 0;
}
</style>
