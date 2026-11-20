<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { deviceReport, type DeviceReport } from "../app/device";
import { platform } from "../app/platform";
import { SUPPORTED_PROTOCOL } from "../core/protocol";
import { format, useI18n } from "../i18n";
import { useCore } from "../stores/core";
import { useGrammar } from "../stores/grammar";

const m = useI18n();
const core = useCore();
const grammarInfo = useGrammar();
// Attribution required by the dictionary's licence (CC BY-SA).
const lexiconSource = computed(() => {
  const src = grammarInfo.lexicon?.packages[0]?.source;
  if (!src) return "";
  return format(m.value.about.lexiconSource, {
    name: src.name, url: src.url, license: src.license, version: `${src.version ?? "?"} (rev. ${src.revision ?? "?"})`,
  });
});
const appVersion = __APP_VERSION__;

const device = ref<DeviceReport | null>(null);
onMounted(async () => (device.value = await deviceReport()));

const info = computed(() => core.info);
const timings = computed(() => core.info?.timings ?? null);
const protocolMismatch = computed(() => core.version !== null && core.version.protocol !== SUPPORTED_PROTOCOL);
const ms = (value: number) => `${Math.round(value)} ${m.value.common.ms}`;
const mb = (bytes: number) => (bytes / 1024 / 1024).toFixed(1);

const copied = ref(false);
const forgotten = ref(false);

function reportText(): string {
  const d = device.value;
  const t = timings.value;
  const lines = [
    `Tilsim ${appVersion} (${platform})`,
    `Model: ${d?.model ?? "?"}; ${d?.osVersion ?? "?"}; ${d?.browser ?? "?"}`,
    `CPU: ${d?.cores ?? "?"} cores; RAM: ${d?.memoryGb ?? "?"} GB`,
    `Core: ${core.version?.core ?? "?"} (${info.value?.bundleHash ?? "?"}), Python ${core.version?.python ?? "?"}`,
  ];
  if (t) {
    lines.push(
      `Start: ${t.mode}; total ${Math.round(t.totalMs)} ms; runtime ${Math.round(t.runtimeMs)} ms` +
        ` (compile ${Math.round(t.compileMs)} ms); package ${Math.round(t.packageMs)} ms` +
        (info.value?.snapshotReadMs !== undefined ? `; snapshot read ${Math.round(info.value.snapshotReadMs)} ms` : "") +
        (t.snapshotBytes ? `; snapshot ${mb(t.snapshotBytes)} MB` : ""),
    );
    if (t.snapshotError) lines.push(`Snapshot error: ${t.snapshotError}`);
  } else if (core.status === "failed") {
    lines.push(`Start failed: ${core.error}`);
  }
  for (const r of info.value?.resources ?? []) lines.push(`File ${r.name}: ${Math.round(r.ms)} ms, ${mb(r.bytes)} MB`);
  if (core.snapshotSaved) {
    lines.push(`Snapshot saved: ${core.snapshotSaved.saved} (${Math.round(core.snapshotSaved.ms)} ms)`);
  }
  lines.push(`UA: ${d?.userAgent ?? navigator.userAgent}`);
  return lines.join("\n");
}

async function copyReport(): Promise<void> {
  const text = reportText();
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    // The clipboard API needs a secure context; fall back to a selected text area.
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
  copied.value = true;
  setTimeout(() => (copied.value = false), 2500);
}

function forgetSnapshot(): void {
  core.forgetSnapshot();
  forgotten.value = true;
}
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
          <template v-if="core.version">{{ core.version.core }} ({{ info?.bundleHash }})</template>
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
        <dt>{{ m.about.mode }}</dt>
        <dd>{{ timings.mode === "snapshot" ? m.about.modeSnapshot : m.about.modeFresh }}</dd>
        <template v-if="info?.snapshotReadMs !== undefined">
          <dt>{{ m.about.snapshotRead }}</dt>
          <dd>{{ ms(info.snapshotReadMs) }} ({{ mb(timings.snapshotBytes ?? 0) }} MB)</dd>
        </template>
        <dt>{{ m.about.startupRuntime }}</dt>
        <dd>{{ ms(timings.runtimeMs) }}</dd>
        <dt class="sub">{{ m.about.compile }}</dt>
        <dd>{{ ms(timings.compileMs) }}</dd>
        <dt>{{ m.about.startupPackage }}</dt>
        <dd>{{ ms(timings.packageMs) }}</dd>
        <dt>{{ m.about.startupTotal }}</dt>
        <dd><strong>{{ ms(timings.totalMs) }}</strong></dd>
        <template v-if="info?.resources.length">
          <dt>{{ m.about.downloads }}</dt>
          <dd>
            <div v-for="r in info.resources" :key="r.name" class="small">
              {{ r.name }}: {{ ms(r.ms) }}<template v-if="r.bytes > 0">, {{ mb(r.bytes) }} MB</template>
            </div>
          </dd>
        </template>
      </dl>
      <span v-else-if="core.status !== 'failed'" class="skeleton" style="width: 40%" />
      <div v-if="timings?.snapshotError" class="alert warn">{{ format(m.about.snapshotError, { error: timings.snapshotError }) }}</div>
      <div v-if="core.snapshotSaved" class="alert" :class="core.snapshotSaved.saved ? 'ok' : 'warn'">
        {{
          core.snapshotSaved.saved
            ? format(m.about.snapshotSaved, { mb: mb(core.snapshotSaved.bytes), ms: Math.round(core.snapshotSaved.ms) })
            : m.about.snapshotSaveFailed
        }}
      </div>
      <p class="muted small">{{ m.about.measuredHere }}</p>
    </div>

    <div v-if="lexiconSource" class="card">
      <h2>{{ m.about.lexicon }}</h2>
      <p>{{ lexiconSource }}</p>
    </div>

    <div class="card">
      <h2>{{ m.about.device }}</h2>
      <dl v-if="device">
        <dt>{{ m.about.model }}</dt>
        <dd>{{ device.model ?? "—" }}</dd>
        <dt>{{ m.about.os }}</dt>
        <dd>{{ device.osVersion ?? "—" }}</dd>
        <dt>{{ m.about.cores }}</dt>
        <dd>{{ device.cores ?? "—" }}</dd>
        <dt>{{ m.about.memory }}</dt>
        <dd>{{ device.memoryGb !== undefined ? `${device.memoryGb} GB` : "—" }}</dd>
        <dt>{{ m.about.webview }}</dt>
        <dd>{{ device.browser ?? "—" }}</dd>
      </dl>
      <div class="actions">
        <button class="btn primary" type="button" @click="copyReport">{{ copied ? m.about.copied : m.about.copyReport }}</button>
        <button class="btn" type="button" :disabled="forgotten" @click="forgetSnapshot">{{ m.about.forgetSnapshot }}</button>
      </div>
      <p v-if="forgotten" class="muted small">{{ m.about.forgetSnapshotDone }}</p>
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
dt.sub {
  padding-left: 1rem;
  font-size: 0.9rem;
}
dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
@media (max-width: 520px) {
  dl {
    grid-template-columns: 1fr;
    gap: 0.1rem;
  }
  dd {
    margin-bottom: 0.6rem;
  }
  dt.sub {
    padding-left: 0;
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
