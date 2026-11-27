<script setup lang="ts">
// About the app, for every user: what it is, its version and the sources of the dictionary and
// of the pronunciation voices (CC BY, CC BY-SA and Apache 2.0 ask for the attribution; every
// Commons recording is credited here, with its author, licence and file). Technical details are in the admin panel, whose
// hidden entry is here: tapping the version seven times opens it.
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { format, useI18n } from "../i18n";
import { authorCredits, licenseUrl, licensesUsed } from "../pronunciation/credits";
import { loadManifest, type Manifest } from "../pronunciation/source";
import { useGrammar } from "../stores/grammar";

const m = useI18n();
const g = useGrammar();
const router = useRouter();
const appVersion = __APP_VERSION__;

const lexiconSource = computed(() => {
  const src = g.lexicon?.packages[0]?.source;
  if (!src) return "";
  return format(m.value.about.lexiconSource, {
    name: src.name, url: src.url, license: src.license, version: `${src.version ?? "?"} (rev. ${src.revision ?? "?"})`,
  });
});

const VOSK_MODEL = "vosk-model-tts-ru-0.9-multi, https://alphacephei.com/vosk/models";
const APACHE = "https://www.apache.org/licenses/LICENSE-2.0";

const manifest = ref<Manifest | null>(null);
onMounted(async () => {
  try {
    manifest.value = await loadManifest();
  } catch {
    manifest.value = null;
  }
});
const credits = computed(() => (manifest.value ? authorCredits(manifest.value) : []));
const recordings = computed(() => Object.keys(manifest.value?.words ?? {}).length);
const licenses = computed(() => licensesUsed(credits.value));
const words = computed(() => Object.entries(manifest.value?.words ?? {}).sort(([a], [b]) => a.localeCompare(b, "ru")));
const showWords = ref(false);

const TAPS = 7;
const WINDOW_MS = 4000;
const taps = ref<number[]>([]);
function tapVersion(): void {
  const now = Date.now();
  taps.value = [...taps.value.filter((t) => now - t < WINDOW_MS), now];
  if (taps.value.length >= TAPS) {
    taps.value = [];
    void router.push("/admin");
  }
}
</script>

<template>
  <section class="page">
    <h1>{{ m.about.title }}</h1>
    <div class="card">
      <div class="brand">
        <img src="/brand/tilsim-b.svg" alt="" class="logo" />
        <div>
          <div class="name">{{ m.app.name }}</div>
          <div class="muted small">{{ m.app.tagline }}</div>
        </div>
      </div>
      <p>{{ m.about.description }}</p>
      <dl>
        <dt>{{ m.about.version }}</dt>
        <dd class="version" @click="tapVersion">{{ appVersion }}</dd>
      </dl>
      <div class="alert warn">{{ m.common.testMode }}</div>
    </div>

    <div v-if="lexiconSource" class="card">
      <h2>{{ m.about.lexicon }}</h2>
      <p>{{ lexiconSource }}</p>
    </div>

    <div class="card">
      <h2>{{ m.about.voices }}</h2>
      <p>{{ format(m.about.packsSource, { model: VOSK_MODEL, url: APACHE }) }}</p>
      <template v-if="manifest">
        <p>{{ format(m.about.recordingsSource, { url: "https://commons.wikimedia.org", count: recordings }) }}</p>
        <h3>{{ m.about.authors }}</h3>
        <table class="credits">
          <thead>
            <tr><th>{{ m.about.author }}</th><th>{{ m.about.license }}</th><th class="num">{{ m.about.words }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in credits" :key="c.author + c.license">
              <td>{{ c.author }}</td><td>{{ c.license }}</td><td class="num">{{ c.words }}</td>
            </tr>
          </tbody>
        </table>
        <h3>{{ m.about.licenses }}</h3>
        <ul class="licenses small">
          <li v-for="l in licenses" :key="l">{{ l }}: {{ licenseUrl(l) || m.about.publicDomain }}</li>
        </ul>
        <details class="all" @toggle="showWords = ($event.target as HTMLDetailsElement).open">
          <summary>{{ format(m.about.allWords, { count: recordings }) }}</summary>
          <table v-if="showWords" class="credits small">
            <thead>
              <tr><th>{{ m.about.word }}</th><th>{{ m.about.author }}</th><th>{{ m.about.license }}</th><th>{{ m.about.file }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="[word, r] in words" :key="word">
                <td lang="ru">{{ word }}</td><td>{{ r.author }}</td><td>{{ r.license }}</td><td class="file">{{ r.file }}</td>
              </tr>
            </tbody>
          </table>
        </details>
      </template>
      <p>{{ m.about.deviceSource }}</p>
    </div>
  </section>
</template>

<style scoped>
.page {
  max-width: 640px;
  display: grid;
  gap: 1rem;
  align-content: start;
}
.brand {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.logo {
  width: 3rem;
  height: 3rem;
}
.name {
  font-size: 1.25rem;
  font-weight: 700;
}
dl {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.45rem 1.25rem;
  margin: 0 0 0.75rem;
}
dt {
  color: var(--muted);
}
dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
}
.version {
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}
h2 {
  font-size: 1rem;
  margin: 0 0 0.4rem;
}
p {
  margin: 0.75rem 0;
}
h3 {
  font-size: 0.95rem;
  margin: 1rem 0 0.4rem;
}
.credits {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.credits th {
  text-align: left;
  color: var(--muted);
  font-weight: 600;
}
.credits th,
.credits td {
  padding: 0.3rem 0.5rem 0.3rem 0;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
.credits .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.credits .file {
  color: var(--muted);
  word-break: break-all;
}
.licenses {
  margin: 0;
  padding-left: 1.1rem;
  overflow-wrap: anywhere;
}
.all {
  margin-top: 1rem;
}
.all summary {
  cursor: pointer;
  font-weight: 600;
}
</style>
