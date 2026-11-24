<script setup lang="ts">
// The learner's account: sign in or create one; once signed in, what the account holds on the
// server, the sync of this device, and every device that used the account (another one can
// be signed out from here). Figures come from GET /v1/account; nothing is estimated.
import { computed, onMounted, ref, watch } from "vue";
import type { AccountDevice, AccountOverview } from "../api/types";
import { secretsPersist } from "../data/secrets";
import { dateLocale, format, useI18n } from "../i18n";
import { useAdmin } from "../stores/admin";
import { useSession } from "../stores/session";
import { useSettings } from "../stores/settings";
import { useSync } from "../stores/sync";
import StatusBadge from "../ui/StatusBadge.vue";
import { describeError } from "../ui/errors";

const m = useI18n();
const session = useSession();
const settings = useSettings();
const sync = useSync();
const admin = useAdmin();

const mode = ref<"login" | "register">("login");
const email = ref("");
const password = ref("");
const displayName = ref("");
const deviceName = ref("");
const busy = ref(false);
const error = ref("");

const overview = ref<AccountOverview | null>(null);
const overviewError = ref("");
const loadingOverview = ref(false);
const confirmRevoke = ref<string | null>(null);
const revoking = ref<string | null>(null);
const confirmReplace = ref(false);
const signingOut = ref(false);

async function submit(): Promise<void> {
  error.value = "";
  busy.value = true;
  try {
    if (mode.value === "login") await session.login(email.value, password.value, deviceName.value);
    else await session.register(email.value, password.value, displayName.value, deviceName.value);
    password.value = "";
  } catch (e) {
    error.value = describeError(e, m.value);
  } finally {
    busy.value = false;
  }
}

function toggle(): void {
  mode.value = mode.value === "login" ? "register" : "login";
  error.value = "";
}

async function loadOverview(): Promise<void> {
  if (!session.user || loadingOverview.value) return;
  loadingOverview.value = true;
  try {
    overview.value = await session.authorized<AccountOverview>("/v1/account");
    overviewError.value = "";
  } catch (e) {
    overviewError.value = describeError(e, m.value);
  } finally {
    loadingOverview.value = false;
  }
}

async function revoke(device: AccountDevice): Promise<void> {
  if (confirmRevoke.value !== device.id) {
    confirmRevoke.value = device.id;
    return;
  }
  confirmRevoke.value = null;
  revoking.value = device.id;
  try {
    await session.authorized("/v1/devices/revoke", { body: { device_id: device.id } });
    await loadOverview();
  } catch (e) {
    overviewError.value = describeError(e, m.value);
  } finally {
    revoking.value = null;
  }
}

async function logout(): Promise<void> {
  signingOut.value = true;
  try {
    await sync.flush();
    await session.logout();
    overview.value = null;
  } finally {
    signingOut.value = false;
  }
}

async function replace(): Promise<void> {
  confirmReplace.value = false;
  await sync.replaceLocalData();
}

function when(iso: string | null | undefined): string {
  return iso ? new Date(iso).toLocaleString(dateLocale(), {
        day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
      }) : m.value.account.never;
}

const platformName = (p: AccountDevice["platform"]): string => m.value.account.platforms[p];

const progressItems = computed(() => {
  const p = overview.value?.progress;
  if (!p) return [];
  const a = m.value.account.progress;
  return [
    { label: a.words, value: p.words, note: p.words ? format(a.known, { n: p.known_words }) : "" },
    { label: a.cards, value: p.cards, note: "" },
    { label: a.reviews, value: p.reviews, note: "" },
    { label: a.readings, value: p.readings, note: p.texts ? format(a.texts, { n: p.texts }) : "" },
    { label: a.tests, value: p.tests, note: "" },
  ];
});

const syncText = computed(() => {
  const a = m.value.account.sync;
  switch (sync.state) {
    case "syncing":
      return a.running;
    case "ok":
      return format(a.done, { time: when(sync.lastSyncAt) });
    case "offline":
      return a.offline;
    case "failed":
      return a.failed;
    default:
      return sync.lastSyncAt ? format(a.done, { time: when(sync.lastSyncAt) }) : a.notYet;
  }
});

onMounted(() => void loadOverview());
watch(() => session.user?.id, () => void loadOverview());
watch(() => sync.lastSyncAt, () => void loadOverview());
</script>

<template>
  <section class="page">
    <h1>{{ m.account.title }}</h1>

    <template v-if="session.user">
      <article class="card who">
        <div>
          <p class="name">{{ session.user.display_name || session.user.email }}</p>
          <p v-if="session.user.display_name" class="muted small">{{ session.user.email }}</p>
          <p v-if="admin.unlocked" class="muted small">{{ m.account.role }}: {{ session.user.role }}</p>
        </div>
        <button class="btn" :disabled="signingOut" @click="logout">
          {{ signingOut ? m.common.loading : m.account.logout }}
        </button>
      </article>

      <article v-if="sync.state === 'other_account'" class="card alert warn" role="alert">
        <p>{{ format(m.account.otherAccount, { email: session.user.email }) }}</p>
        <p v-if="sync.pending">{{ format(m.account.otherAccountUnsent, { n: sync.pending }) }}</p>
        <div class="row">
          <button v-if="!confirmReplace" class="btn primary" @click="confirmReplace = true">{{ m.account.replaceData }}</button>
          <template v-else>
            <span>{{ m.account.areYouSure }}</span>
            <button class="btn primary" @click="replace">{{ m.common.yes }}</button>
            <button class="btn" @click="confirmReplace = false">{{ m.common.no }}</button>
          </template>
          <button class="btn" @click="logout">{{ m.account.logout }}</button>
        </div>
      </article>

      <article v-else class="card">
        <header>
          <h2>{{ m.account.sync.title }}</h2>
          <StatusBadge v-if="sync.state === 'ok'" tone="ok" :label="m.account.sync.ok" />
          <StatusBadge v-else-if="sync.state === 'offline'" tone="warn" :label="m.status.offline" />
          <StatusBadge v-else-if="sync.state === 'failed'" tone="err" :label="m.status.failed" />
          <StatusBadge v-else tone="muted" :label="m.status.loading" />
        </header>
        <p class="small">{{ syncText }}</p>
        <p v-if="sync.pending" class="muted small">{{ format(m.account.sync.pending, { n: sync.pending }) }}</p>
        <p v-if="sync.rejected" class="muted small">{{ format(m.account.sync.rejected, { n: sync.rejected }) }}</p>
        <p v-if="admin.unlocked && sync.detail" class="muted small mono">{{ sync.detail }}</p>
        <button class="btn" :disabled="sync.state === 'syncing'" @click="sync.syncNow()">{{ m.account.sync.now }}</button>
      </article>

      <article class="card">
        <header>
          <h2>{{ m.account.progress.title }}</h2>
        </header>
        <p v-if="overviewError" class="muted small">{{ overviewError }}</p>
        <p v-else-if="!overview" class="muted small">{{ m.common.loading }}</p>
        <template v-else>
          <div class="stats">
            <div v-for="item in progressItems" :key="item.label" class="stat">
              <span class="value">{{ item.value }}</span>
              <span class="label">{{ item.label }}</span>
              <span v-if="item.note" class="muted small">{{ item.note }}</span>
            </div>
          </div>
          <p class="muted small">
            {{ overview.progress.last_change_at
              ? format(m.account.progress.lastChange, { time: when(overview.progress.last_change_at) })
              : m.account.progress.empty }}
          </p>
        </template>
      </article>

      <article class="card">
        <header>
          <h2>{{ m.account.devices.title }}</h2>
        </header>
        <p v-if="!overview && !overviewError" class="muted small">{{ m.common.loading }}</p>
        <ul v-else-if="overview" class="devices">
          <li v-for="d in overview.devices" :key="d.id" :class="{ off: !d.signed_in }">
            <div class="device">
              <p class="name">
                {{ d.name }}
                <span class="muted small">· {{ platformName(d.platform) }}</span>
                <StatusBadge v-if="d.current" tone="ok" :label="m.account.devices.current" />
                <StatusBadge v-else-if="!d.signed_in" tone="muted" :label="m.account.devices.signedOut" />
              </p>
              <p class="muted small">{{ format(m.account.devices.lastSeen, { time: when(d.last_seen_at) }) }}</p>
              <p class="muted small">{{ format(m.account.devices.lastSync, { time: when(d.last_sync_at) }) }}</p>
            </div>
            <div v-if="d.signed_in && !d.current" class="row">
              <span v-if="confirmRevoke === d.id" class="small">{{ m.account.areYouSure }}</span>
              <button class="btn" :disabled="revoking === d.id" @click="revoke(d)">
                {{ confirmRevoke === d.id ? m.common.yes : m.account.devices.signOut }}
              </button>
              <button v-if="confirmRevoke === d.id" class="btn" @click="confirmRevoke = null">{{ m.common.no }}</button>
            </div>
          </li>
        </ul>
        <p class="muted small">{{ m.account.devices.hint }}</p>
      </article>
    </template>

    <div v-else-if="!settings.apiUrl" class="alert warn">{{ m.account.needServer }}</div>

    <form v-else class="card form" @submit.prevent="submit">
      <h2>{{ mode === "login" ? m.account.login : m.account.register }}</h2>
      <p class="muted small">{{ m.account.why }}</p>
      <div v-if="error" class="alert err" role="alert">{{ error }}</div>
      <div v-if="!secretsPersist" class="alert warn">{{ m.account.sessionNotSaved }}</div>

      <div v-if="mode === 'register'" class="field">
        <label for="name">{{ m.account.displayName }}</label>
        <input id="name" v-model="displayName" class="input" autocomplete="name" maxlength="80" />
      </div>
      <div class="field">
        <label for="email">{{ m.account.email }}</label>
        <input id="email" v-model="email" class="input" type="email" autocomplete="email" required maxlength="254" />
      </div>
      <div class="field">
        <label for="password">{{ m.account.password }}</label>
        <input id="password" v-model="password" class="input" type="password" required minlength="10" maxlength="200"
          :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" />
        <span v-if="mode === 'register'" class="muted small">{{ m.account.passwordHint }}</span>
      </div>
      <div class="field">
        <label for="device">{{ m.account.deviceName }}</label>
        <input id="device" v-model="deviceName" class="input" maxlength="80" :placeholder="m.account.deviceNameHint" />
      </div>

      <div class="actions">
        <button class="btn primary" type="submit" :disabled="busy">
          {{ busy ? m.common.loading : mode === "login" ? m.account.login : m.account.register }}
        </button>
        <button class="btn link" type="button" @click="toggle">
          {{ mode === "login" ? m.account.switchToRegister : m.account.switchToLogin }}
        </button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.page {
  max-width: 640px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
h2 {
  margin: 0;
  font-size: 1.05rem;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
.who {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}
.name {
  margin: 0;
  font-weight: 600;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
}
p {
  margin: 0.25rem 0;
}
.row,
.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(7rem, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}
.stat {
  display: flex;
  flex-direction: column;
}
.stat .value {
  font-size: 1.5rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.stat .label {
  font-size: 0.9rem;
}
.devices {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}
.devices li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
  padding: 0.6rem 0;
  border-bottom: 1px solid var(--border);
}
.devices li:last-child {
  border-bottom: none;
}
.devices li.off {
  opacity: 0.65;
}
.mono {
  font-family: ui-monospace, monospace;
  word-break: break-all;
}
</style>
