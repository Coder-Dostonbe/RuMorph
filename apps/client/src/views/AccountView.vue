<script setup lang="ts">
import { ref } from "vue";
import { secretsPersist } from "../data/secrets";
import { format, useI18n } from "../i18n";
import { useSession } from "../stores/session";
import { useSettings } from "../stores/settings";
import { describeError } from "../ui/errors";

const m = useI18n();
const session = useSession();
const settings = useSettings();

const mode = ref<"login" | "register">("login");
const email = ref("");
const password = ref("");
const displayName = ref("");
const deviceName = ref("");
const busy = ref(false);
const error = ref("");

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
</script>

<template>
  <section class="page">
    <h1>{{ m.account.title }}</h1>

    <div v-if="session.user" class="card">
      <p>{{ format(m.account.signedInAs, { email: session.user.email }) }}</p>
      <p class="muted small">{{ m.account.role }}: {{ session.user.role }}</p>
      <button class="btn" @click="session.logout()">{{ m.account.logout }}</button>
    </div>

    <div v-else-if="!settings.apiUrl" class="alert warn">
      {{ m.account.needServer }} <RouterLink to="/settings">{{ m.nav.settings }}</RouterLink>
    </div>

    <form v-else class="card form" @submit.prevent="submit">
      <h2>{{ mode === "login" ? m.account.login : m.account.register }}</h2>
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
        <input id="device" v-model="deviceName" class="input" maxlength="80" />
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
  max-width: 520px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem;
}
</style>
