<script setup lang="ts">
// "Listen" next to a word. The installed voice pack (Settings) reads it when it has the word,
// offline. Otherwise a recorded pronunciation (Wikimedia Commons) plays when the word has one;
// the first time it needs the internet, then it is kept on the device. Other words are read by
// the device's own voice, marked as synthetic. A stress homograph (замок) gets no button:
// neither a recording nor a synthetic voice can know which word is meant.
// Pressing again within 5 seconds slows the word down: 1x, 0.75x, 0.5x, then 1x again; a
// longer pause starts at 1x. The button itself shows no speed. Who made the voices is credited
// on the About page, not here.
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { platform } from "../app/platform";
import { format, useI18n } from "../i18n";
import { cached, keep } from "../pronunciation/audioCache";
import { speak, voiceState } from "../pronunciation/deviceVoice";
import { nextSpeed, playBlob, stopAudio, type LastPress, type Speed } from "../pronunciation/player";
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
const last = ref<LastPress | null>(null);
const speed = computed<Speed>(() => last.value?.speed ?? 1);

watch(() => props.lemma, async (lemma) => {
  found.value = null;
  notice.value = "";
  last.value = null;
  try {
    const data = await loadManifest();
    if (props.lemma === lemma) found.value = lookup(data, lemma);
  } catch {
    found.value = { kind: "none" };
  }
}, { immediate: true });

const fromPack = computed(() => voice.has(props.lemma));
const recording = computed(() => (found.value?.kind === "recording" ? found.value.recording : null));
const visible = computed(() => found.value !== null && found.value.kind !== "homograph");

onBeforeUnmount(stopAudio);

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
  return playBlob(blob, speed.value);
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
  await speak(props.lemma, speed.value);
}

async function listen(): Promise<void> {
  if (busy.value) return;
  busy.value = true;
  notice.value = "";
  last.value = { speed: nextSpeed(last.value, Date.now()), at: Date.now() };
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
.notice {
  flex-basis: 100%;
  margin: 0;
  color: var(--warn);
}
</style>
