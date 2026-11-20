<script setup lang="ts">
import { computed } from "vue";
import { platform } from "../app/platform";
import { SUPPORTED_PROTOCOL } from "../core/protocol";
import { format, useI18n } from "../i18n";
import { useCore } from "../stores/core";

const m = useI18n();
const core = useCore();
const appVersion = __APP_VERSION__;

const timings = computed(() => core.info?.timings ?? null);
const protocolMismatch = computed(() => core.version !== null && core.version.protocol !== SUPPORTED_PROTOCOL);
const ms = (value: number) => `${Math.round(value)} ${m.value.common.ms}`;
</script>

<template>
  <section class="page">
    <h1>{{ m.about.title }}</h1>

    <div class="card">
      <dl>
        <dt>{{ m.about.appVersion }}</dt>
        <dd>{{ appVersion }}</dd>
        <dt>{{ m.about.platform }}</dt>
        <dd>{{ m.about.platforms[platform] }}</dd>
        <dt>{{ m.about.core }}</dt>
        <dd>
          <template v-if="core.version">{{ core.version.core }} ({{ core.info?.bundleHash }})</template>
          <span v-else-if="core.status === 'failed'" class="err-text">{{ core.error }}</span>
          <span v-else class="skeleton" style="width: 6rem" />
        </dd>
        <dt>{{ m.about.python }}</dt>
        <dd>{{ core.version?.python ?? "—" }}</dd>
        <dt>{{ m.about.protocol }}</dt>
        <dd>{{ core.version?.protocol ?? "—" }}</dd>
      </dl>
      <div v-if="protocolMismatch && core.version" class="alert warn">
        {{ format(m.about.protocolMismatch, { expected: SUPPORTED_PROTOCOL, actual: core.version.protocol }) }}
      </div>
    </div>

    <div class="card">
      <h2>{{ m.about.startup }}</h2>
      <dl v-if="timings">
        <dt>{{ m.about.startupRuntime }}</dt>
        <dd>{{ ms(timings.runtimeMs) }}</dd>
        <dt>{{ m.about.startupPackage }}</dt>
        <dd>{{ ms(timings.packageMs) }}</dd>
        <dt>{{ m.about.startupTotal }}</dt>
        <dd><strong>{{ ms(timings.totalMs) }}</strong></dd>
      </dl>
      <span v-else-if="core.status !== 'failed'" class="skeleton" style="width: 40%" />
      <p class="muted small">{{ m.about.measuredHere }}</p>
    </div>

    <details v-if="core.stderr.length" class="card">
      <summary>{{ m.about.coreLog }} ({{ core.stderr.length }})</summary>
      <pre>{{ core.stderr.join("\n") }}</pre>
    </details>
  </section>
</template>

<style scoped>
.page {
  max-width: 640px;
  display: grid;
  gap: 1rem;
  align-content: start;
}
dl {
  display: grid;
  grid-template-columns: minmax(10rem, max-content) 1fr;
  gap: 0.45rem 1.25rem;
  margin: 0 0 0.5rem;
}
dt {
  color: var(--muted);
}
dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}
@media (max-width: 520px) {
  dl {
    grid-template-columns: 1fr;
    gap: 0.1rem;
  }
  dd {
    margin-bottom: 0.6rem;
  }
}
.err-text {
  color: var(--err);
}
pre {
  white-space: pre-wrap;
  font-size: 0.8rem;
  max-height: 16rem;
  overflow: auto;
}
</style>
