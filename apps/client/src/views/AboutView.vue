<script setup lang="ts">
// About the app, for every user: what it is, its version and the dictionary's source (the
// CC BY-SA licence asks for the attribution). Technical details are in the admin panel, whose
// hidden entry is here: tapping the version seven times opens it.
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { format, useI18n } from "../i18n";
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
      <p>{{ m.about.pronunciationSource }}</p>
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
</style>
