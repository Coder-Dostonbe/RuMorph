<script setup lang="ts">
// "Listen" next to a word. The installed voice pack (Settings) reads it when it has the word,
// offline. Otherwise a recorded pronunciation (Wikimedia Commons) plays when the word has one;
// the first time it needs the internet, then it is kept on the device. Other words are read by
// the device's own voice, marked as synthetic. A stress homograph (замок) gets no button:
// neither a recording nor a synthetic voice can know which word is meant.
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { platform } from "../app/platform";
import { format, useI18n } from "../i18n";
import { cached, keep } from "../pronunciation/audioCache";
import { speak, voiceState } from "../pronunciation/deviceVoice";
import { audioUrl, loadManifest, lookup, type Lookup } from "../pronunciation/source";
import { useSettings } from "../stores/settings";
import { useVoicePack } from "../stores/voicePack";

const props = defineProps<{ lemma: string }>();
const m = useI18n();
const settings = useSettings();
const voice = useVoicePack();
void voice.load();

const found = ref<Lookup | null>(null);
const busy = ref(false);
const notice = ref("");
let player: HTMLAudioElement | null = null;
let objectUrl = "";

watch(() => props.lemma, async (lemma) => {
  found.value = null;
  notice.value = "";
  try {
    const data = await loadManifest();
    if (props.lemma === lemma) found.value = lookup(data, lemma);
  } catch {
    found.value = { kind: "none" };
  }
}, { immediate: true });

const fromPack = computed(() => voice.has(props.lemma));
const packName = computed(() => (voice.current ? m.value.settings.voice.names[voice.current.id] ?? voice.current.id : ""));
const recording = computed(() => (found.value?.kind === "recording" ? found.value.recording : null));
const visible = computed(() => found.value !== null && found.value.kind !== "homograph");

function release(): void {
  player?.pause();
  player = null;
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = "";
}
onBeforeUnmount(release);

async function fetchRecording(url: string): Promise<Blob> {
  const hit = await cached(url);
  if (hit) return hit;
  if (typeof navigator !== "undefined" && navigator.onLine === false) throw new Error("offline");
  let response: Response;
  try {
    response = await fetch(url);
  } catch {
    throw new Error(navigator.onLine === false ? "offline" : "unreachable");
  }
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const blob = await response.blob();
  await keep(url, blob);
  return blob;
}

function play(blob: Blob): Promise<void> {
  release();
  objectUrl = URL.createObjectURL(blob);
  player = new Audio(objectUrl);
  return player.play();
}

async function playRecording(): Promise<void> {
  await play(await fetchRecording(audioUrl(settings.apiUrl, recording.value!.path)));
}

async function playPack(): Promise<boolean> {
  const blob = await voice.audio(props.lemma);
  if (!blob) return false;
  await play(blob);
  return true;
}

async function playDevice(): Promise<void> {
  const state = await voiceState();
  if (state !== "ready") {
    notice.value = state === "no_russian"
      ? (platform === "android" ? m.value.pronounce.noRussianAndroid : m.value.pronounce.noRussianWindows)
      : m.value.pronounce.noVoice;
    return;
  }
  await speak(props.lemma);
}

async function listen(): Promise<void> {
  if (busy.value) return;
  busy.value = true;
  notice.value = "";
  try {
    if (fromPack.value && (await playPack())) return;
    if (recording.value) await playRecording();
    else await playDevice();
  } catch (e) {
    const detail = e instanceof Error ? e.message : String(e);
    notice.value = detail === "offline" ? m.value.pronounce.offline
      : detail === "unreachable" ? m.value.pronounce.unreachable
        : format(m.value.pronounce.failed, { error: detail });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div v-if="visible" class="pronounce">
    <button type="button" class="btn listen" :disabled="busy" :aria-label="format(m.pronounce.listenTo, { word: lemma })"
      @click="listen">
      <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z" />
        <path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11" />
      </svg>
      <span>{{ busy ? m.pronounce.loading : m.pronounce.listen }}</span>
    </button>
    <span v-if="fromPack" class="muted small credit">{{ format(m.pronounce.packCredit, { voice: packName }) }}</span>
    <span v-else-if="recording" class="muted small credit">
      {{ format(m.pronounce.credit, { author: recording.author, license: recording.license }) }}
    </span>
    <span v-else class="muted small credit">{{ m.pronounce.synthetic }}</span>
    <p v-if="notice" class="small notice" role="status">{{ notice }}</p>
  </div>
</template>

<style scoped>
.pronounce {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.3rem 0.6rem;
  margin: 0.35rem 0;
}
.listen {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.7rem;
}
.listen svg {
  width: 1.1rem;
  height: 1.1rem;
}
.credit {
  min-width: 0;
}
.notice {
  flex-basis: 100%;
  margin: 0;
  color: var(--warn);
}
</style>
