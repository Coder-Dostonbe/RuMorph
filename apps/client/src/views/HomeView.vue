<script setup lang="ts">
import { onMounted } from "vue";
import { format, useI18n } from "../i18n";
import { useCore } from "../stores/core";
import { useServer } from "../stores/server";
import { useSession } from "../stores/session";
import StatusBadge from "../ui/StatusBadge.vue";

const m = useI18n();
const core = useCore();
const server = useServer();
const session = useSession();

onMounted(() => {
  if (server.state === "unknown") void server.check();
});
</script>

<template>
  <section class="page">
    <h1>{{ m.home.title }}</h1>
    <p class="muted intro">{{ m.home.intro }}</p>

    <div class="grid">
      <article class="card">
        <header>
          <h2>{{ m.home.engineCard }}</h2>
          <StatusBadge v-if="core.status === 'ready'" tone="ok" :label="m.status.ready" />
          <StatusBadge v-else-if="core.status === 'failed'" tone="err" :label="m.status.failed" />
          <StatusBadge v-else tone="muted" :label="m.status.loading" />
        </header>
        <p v-if="core.status === 'ready' && core.version">
          {{ format(m.home.engineReady, { python: core.version.python, core: core.version.core }) }}
        </p>
        <p v-else-if="core.status === 'failed'" class="err-text">{{ format(m.home.engineFailed, { error: core.error }) }}</p>
        <template v-else>
          <p class="muted">{{ m.home.engineLoading }}</p>
          <span class="skeleton" style="width: 60%" />
        </template>
      </article>

      <article class="card">
        <header>
          <h2>{{ m.home.accountCard }}</h2>
          <StatusBadge v-if="session.signedIn" tone="ok" :label="m.status.online" />
          <StatusBadge v-else tone="muted" :label="m.status.signedOut" />
        </header>
        <p v-if="session.user">{{ format(m.home.signedInAs, { email: session.user.email }) }}</p>
        <p v-else class="muted">{{ m.home.signedOut }}</p>
        <RouterLink to="/account" class="btn">{{ session.signedIn ? m.nav.account : m.account.login }}</RouterLink>
      </article>

      <article class="card">
        <header>
          <h2>{{ m.home.serverCard }}</h2>
          <StatusBadge v-if="server.state === 'ok'" tone="ok" :label="m.status.online" />
          <StatusBadge v-else-if="server.state === 'unreachable'" tone="err" :label="m.status.offline" />
          <StatusBadge v-else-if="server.state === 'not_configured'" tone="warn" :label="m.status.notConfigured" />
          <StatusBadge v-else tone="muted" :label="m.status.loading" />
        </header>
        <p v-if="server.state === 'ok'">{{ format(m.home.serverOk, { ms: server.latencyMs ?? 0 }) }}</p>
        <p v-else-if="server.state === 'not_configured'" class="muted">{{ m.home.serverNotConfigured }}</p>
        <p v-else-if="server.state === 'unreachable'" class="muted">{{ format(m.home.serverUnreachable, { error: server.error }) }}</p>
        <RouterLink v-if="server.state === 'not_configured'" to="/settings" class="btn">{{ m.nav.settings }}</RouterLink>
        <button v-else class="btn" :disabled="server.state === 'checking'" @click="server.check()">{{ m.common.retry }}</button>
      </article>
    </div>
  </section>
</template>

<style scoped>
.page {
  max-width: 980px;
}
.intro {
  max-width: 60ch;
  margin-bottom: 1.5rem;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1rem;
}
.card header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}
.card h2 {
  margin: 0;
}
.err-text {
  color: var(--err);
}
.btn {
  text-decoration: none;
}
</style>
