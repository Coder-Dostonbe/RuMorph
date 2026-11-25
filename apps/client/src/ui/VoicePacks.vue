<script setup lang="ts">
// Settings: choose, download and install a pronunciation voice pack (src/stores/voicePack.ts).
import { onBeforeUnmount, onMounted, ref } from "vue";
import { format, useI18n } from "../i18n";
import { useSettings } from "../stores/settings";
import { sampleUrl, useVoicePack, voicePacks, type VoicePackInfo } from "../stores/voicePack";

const m = useI18n();
const settings = useSettings();
const voice = useVoicePack();
onMounted(() => void voice.load());

const sampleNotice = ref<string | null>(null);
let player: HTMLAudioElement | null = null;
onBeforeUnmount(() => player?.pause());

function name(pack: VoicePackInfo): string {
  return m.value.settings.voice.names[pack.id] ?? pack.id;
}

function size(pack: VoicePackInfo): string {
  return format(m.value.settings.voice.size, { words: pack.words, mb: (pack.bytes / 1e6).toFixed(1) });
}

let objectUrl = "";
onBeforeUnmount(() => objectUrl && URL.revokeObjectURL(objectUrl));

// Fetched, then played from memory: the app's CSP lets audio play only from the app and blobs.
async function playSample(pack: VoicePackInfo): Promise<void> {
  sampleNotice.value = null;
  player?.pause();
  try {
    const response = await fetch(sampleUrl(settings.apiUrl, pack));
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = URL.createObjectURL(await response.blob());
    player = new Audio(objectUrl);
    await player.play();
  } catch {
    sampleNotice.value = pack.id;
  }
}

function failureText(code: string): string {
  const v = m.value.settings.voice;
  if (code === "offline") return v.offline;
  if (code === "unreachable") return v.unreachable;
  if (code === "checksum" || code === "size") return v.broken;
  if (code === "unsupported") return v.unsupported;
  return format(v.failed, { error: code });
}
</script>

<template>
  <div class="card voice">
    <h2>{{ m.settings.voice.title }}</h2>
    <p class="muted small">{{ m.settings.voice.intro }}</p>
    <p v-if="voice.loaded && !voice.installed" class="small">{{ m.settings.voice.none }}</p>

    <ul class="packs">
      <li v-for="pack in voicePacks" :key="pack.id" class="pack" :class="{ active: voice.installed === pack.id }">
        <div class="info">
          <strong>{{ name(pack) }}</strong>
          <span v-if="voice.installed === pack.id" class="badge">{{ m.settings.voice.installed }}</span>
          <span class="muted small">{{ size(pack) }}</span>
        </div>
        <div class="actions">
          <button type="button" class="btn" @click="playSample(pack)">{{ m.settings.voice.sample }}</button>
          <button v-if="voice.installed !== pack.id" type="button" class="btn primary" :disabled="voice.busy !== null"
            @click="voice.install(pack)">
            {{ voice.installed ? m.settings.voice.replace : m.settings.voice.install }}
          </button>
          <button v-else type="button" class="btn" :disabled="voice.busy !== null" @click="voice.remove()">
            {{ m.settings.voice.remove }}
          </button>
        </div>
        <div v-if="voice.busy === pack.id" class="progress" role="status">
          <div class="bar"><div class="fill" :style="{ width: `${Math.round(voice.progress * 100)}%` }" /></div>
          <span class="small">{{ format(m.settings.voice.downloading, { percent: Math.round(voice.progress * 100) }) }}</span>
        </div>
        <p v-if="voice.failure?.id === pack.id" class="small warn" role="status">{{ failureText(voice.failure.code) }}</p>
        <p v-if="sampleNotice === pack.id" class="small warn" role="status">{{ m.settings.voice.sampleFailed }}</p>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.voice h2 {
  margin: 0 0 0.3rem;
  font-size: 1.05rem;
}
.packs {
  list-style: none;
  margin: 0.6rem 0 0;
  padding: 0;
  display: grid;
  gap: 0.5rem;
}
.pack {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0.6rem 0.75rem;
  display: grid;
  gap: 0.45rem;
}
.pack.active {
  border-color: var(--accent);
}
.info {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.3rem 0.6rem;
}
.badge {
  font-size: 0.72rem;
  padding: 0.05rem 0.45rem;
  border-radius: 999px;
  background: var(--accent);
  color: var(--on-accent);
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.progress {
  display: grid;
  gap: 0.25rem;
}
.bar {
  height: 6px;
  border-radius: 999px;
  background: var(--border);
  overflow: hidden;
}
.fill {
  height: 100%;
  background: var(--accent);
  transition: width 0.2s;
}
.warn {
  margin: 0;
  color: var(--warn);
}
</style>
