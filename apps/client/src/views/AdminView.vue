<script setup lang="ts">
// The temporary admin panel (testing period): asks for this device's password (or for a new
// one the first time), then shows the technical pages and the translations. Reached only from
// the hidden entry in "About"; the router keeps the other admin pages behind it.
import { computed, onMounted, ref } from "vue";
import AdminStatus from "../admin/AdminStatus.vue";
import AdminSystem from "../admin/AdminSystem.vue";
import AdminTranslations from "../admin/AdminTranslations.vue";
import { MIN_LENGTH } from "../admin/password";
import { secretsPersist } from "../data/secrets";
import { format, useI18n } from "../i18n";
import { useAdmin, type AdminResult } from "../stores/admin";

const m = useI18n();
const admin = useAdmin();

type Tab = "translations" | "status" | "system" | "password";
const tab = ref<Tab>("translations");
const tabs = computed<{ id: Tab; label: string }[]>(() => [
  { id: "translations", label: m.value.admin.tabTranslations },
  { id: "status", label: m.value.admin.tabServer },
  { id: "system", label: m.value.admin.tabSystem },
  { id: "password", label: m.value.admin.tabPassword },
]);

const password = ref("");
const repeat = ref("");
const current = ref("");
const message = ref("");
const ok = ref("");
const busy = ref(false);

onMounted(() => void admin.load());

function explain(result: AdminResult): string {
  switch (result) {
    case "too_short":
      return format(m.value.admin.tooShort, { n: MIN_LENGTH });
    case "mismatch":
      return m.value.admin.mismatch;
    case "locked_out":
      return format(m.value.admin.lockedOut, { s: Math.max(1, Math.ceil((admin.lockedUntil - Date.now()) / 1000)) });
    case "wrong":
      return m.value.admin.wrong;
    case "ok":
      return "";
  }
}

async function run(action: () => Promise<AdminResult>, done?: string): Promise<void> {
  busy.value = true;
  message.value = "";
  ok.value = "";
  try {
    const result = await action();
    message.value = explain(result);
    if (result === "ok") {
      password.value = repeat.value = current.value = "";
      if (done) ok.value = done;
    }
  } finally {
    busy.value = false;
  }
}

const create = () => run(() => admin.create(password.value, repeat.value));
const unlock = () => run(() => admin.unlock(password.value));
const change = () => run(() => admin.change(current.value, password.value, repeat.value), m.value.admin.changed);
</script>

<template>
  <section class="page">
    <template v-if="!admin.unlocked">
      <h1>{{ m.admin.title }}</h1>
      <form v-if="admin.configured === false" class="card gate" @submit.prevent="create">
        <h2>{{ m.admin.setupTitle }}</h2>
        <p class="muted small">{{ m.admin.setupIntro }}</p>
        <div class="field">
          <label for="pw">{{ m.admin.password }}</label>
          <input id="pw" v-model="password" class="input" type="password" autocomplete="new-password" />
        </div>
        <div class="field">
          <label for="pw2">{{ m.admin.repeat }}</label>
          <input id="pw2" v-model="repeat" class="input" type="password" autocomplete="new-password" />
        </div>
        <p v-if="!secretsPersist" class="muted small">{{ m.admin.browserNote }}</p>
        <div v-if="message" class="alert err">{{ message }}</div>
        <button class="btn primary" type="submit" :disabled="busy || !password">{{ m.admin.create }}</button>
      </form>
      <form v-else-if="admin.configured" class="card gate" @submit.prevent="unlock">
        <h2>{{ m.admin.loginTitle }}</h2>
        <div class="field">
          <label for="pw">{{ m.admin.password }}</label>
          <input id="pw" v-model="password" class="input" type="password" autocomplete="current-password" />
        </div>
        <div v-if="message" class="alert err">{{ message }}</div>
        <button class="btn primary" type="submit" :disabled="busy || !password">{{ m.admin.unlock }}</button>
      </form>
      <span v-else class="skeleton" style="width: 40%" />
    </template>

    <template v-else>
      <header class="head">
        <h1>{{ m.admin.title }}</h1>
        <button class="btn" type="button" @click="admin.lock()">{{ m.admin.logout }}</button>
      </header>
      <p class="muted intro">{{ m.admin.intro }}</p>
      <div class="segmented tabs" role="tablist">
        <button v-for="t in tabs" :key="t.id" type="button" role="tab" class="seg" :class="{ active: tab === t.id }"
          :aria-selected="tab === t.id" @click="tab = t.id">{{ t.label }}</button>
      </div>

      <AdminTranslations v-if="tab === 'translations'" />
      <AdminStatus v-else-if="tab === 'status'" />
      <AdminSystem v-else-if="tab === 'system'" />
      <form v-else class="card gate" @submit.prevent="change">
        <h2>{{ m.admin.changeTitle }}</h2>
        <div class="field">
          <label for="cur">{{ m.admin.current }}</label>
          <input id="cur" v-model="current" class="input" type="password" autocomplete="current-password" />
        </div>
        <div class="field">
          <label for="pw">{{ m.admin.newPassword }}</label>
          <input id="pw" v-model="password" class="input" type="password" autocomplete="new-password" />
        </div>
        <div class="field">
          <label for="pw2">{{ m.admin.repeat }}</label>
          <input id="pw2" v-model="repeat" class="input" type="password" autocomplete="new-password" />
        </div>
        <div v-if="message" class="alert err">{{ message }}</div>
        <div v-if="ok" class="alert ok">{{ ok }}</div>
        <button class="btn primary" type="submit" :disabled="busy || !current || !password">{{ m.admin.change }}</button>
      </form>
    </template>
  </section>
</template>

<style scoped>
.page {
  max-width: 1000px;
  display: grid;
  gap: 1rem;
  align-content: start;
}
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}
.head h1 {
  margin: 0;
}
.intro {
  margin: 0;
  max-width: 70ch;
}
.tabs {
  flex-wrap: wrap;
  justify-self: start;
}
.gate {
  max-width: 420px;
  display: grid;
  gap: 0.8rem;
}
.gate h2 {
  margin: 0;
  font-size: 1.05rem;
}
.gate p {
  margin: 0;
}
.gate .btn {
  justify-self: start;
}
</style>
