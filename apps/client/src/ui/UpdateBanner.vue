<script setup lang="ts">
// Shown when a newer version of the app is available, and while it is being installed.
import { computed } from "vue";
import { format, useI18n } from "../i18n";
import { useAdmin } from "../stores/admin";
import { useUpdates } from "../stores/updates";

const m = useI18n();
const updates = useUpdates();
const admin = useAdmin();

const visible = computed(() =>
  !updates.dismissed && ["available", "installing", "permission", "installer"].includes(updates.state)
  || (updates.state === "failed" && updates.info !== null && !updates.dismissed),
);
</script>

<template>
  <div v-if="visible" class="banner" role="status">
    <div class="text">
      <strong>{{ format(m.update.available, { version: updates.info?.version ?? "" }) }}</strong>
      <span v-if="updates.state === 'installing'" class="small">{{ m.update.installing }}</span>
      <span v-else-if="updates.state === 'permission'" class="small">{{ m.update.permission }}</span>
      <span v-else-if="updates.state === 'installer'" class="small">{{ m.update.installer }}</span>
      <span v-else-if="updates.state === 'failed'" class="small err-text">
        {{ admin.unlocked ? format(m.update.failedDetail, { error: updates.error }) : m.update.failed }}
      </span>
      <span v-else class="small muted">{{ format(m.update.current, { version: updates.info?.current ?? "" }) }}</span>
    </div>
    <div class="actions">
      <button class="btn primary" type="button" :disabled="updates.state === 'installing'" @click="updates.install()">
        {{ updates.state === "installing" ? m.update.installingShort : m.update.install }}
      </button>
      <button v-if="updates.state !== 'installing'" class="btn" type="button" @click="updates.dismissed = true">{{ m.update.later }}</button>
    </div>
  </div>
</template>

<style scoped>
.banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem 1rem;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  background: var(--surface);
}
.text {
  display: grid;
  gap: 0.15rem;
  min-width: 0;
}
.actions {
  display: flex;
  gap: 0.5rem;
}
.err-text {
  color: var(--err);
  overflow-wrap: anywhere;
}
</style>
