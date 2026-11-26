<script setup lang="ts">
// The learner records the word and listens back to compare it with the sample. The recording
// stays in memory (nothing is saved or sent) and is dropped when the word changes.
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { platform } from "../app/platform";
import { format, useI18n } from "../i18n";
import { playBlob, stopAudio } from "../pronunciation/player";
import { MAX_SECONDS, reasonOf, recordingSupported, startRecording, type Recording } from "../pronunciation/recorder";

const props = defineProps<{ lemma: string }>();
const m = useI18n();

const supported = recordingSupported();
const mine = ref<Blob | null>(null);
const active = ref<Recording | null>(null);
const starting = ref(false);
const seconds = ref(0);
const notice = ref("");
let ticker: ReturnType<typeof setInterval> | undefined;

function stopTicker(): void {
  clearInterval(ticker);
  ticker = undefined;
}

watch(() => props.lemma, () => {
  active.value?.stop();
  mine.value = null;
  notice.value = "";
});
onBeforeUnmount(() => {
  active.value?.stop();
  stopTicker();
});

function problem(reason: string): string {
  const r = m.value.record;
  if (reason === "denied") return platform === "android" ? r.deniedAndroid : r.deniedWindows;
  if (reason === "no_mic") return r.noMic;
  if (reason === "busy") return r.busy;
  if (reason === "empty") return r.empty;
  if (reason === "unsupported") return r.unsupported;
  return r.failed;
}

async function record(): Promise<void> {
  if (active.value || starting.value) return;
  notice.value = "";
  starting.value = true;
  stopAudio();
  try {
    const recording = await startRecording(MAX_SECONDS);
    active.value = recording;
    seconds.value = 0;
    ticker = setInterval(() => (seconds.value = Math.min(MAX_SECONDS, seconds.value + 1)), 1000);
    const lemma = props.lemma;
    const blob = await recording.done;
    if (props.lemma === lemma) {
      mine.value = blob;
      await playBlob(blob);
    }
  } catch (e) {
    notice.value = problem(reasonOf(e));
  } finally {
    starting.value = false;
    active.value = null;
    stopTicker();
  }
}

function stop(): void {
  active.value?.stop();
}

async function listenMine(): Promise<void> {
  if (!mine.value) return;
  notice.value = "";
  try {
    await playBlob(mine.value);
  } catch {
    notice.value = m.value.record.playFailed;
  }
}

const recordLabel = computed(() => (mine.value ? m.value.record.again : m.value.record.start));
</script>

<template>
  <div class="record">
    <template v-if="supported">
      <button v-if="!active" type="button" class="btn small-btn" :disabled="starting"
        :aria-label="format(m.record.startFor, { word: lemma })" @click="record">
        <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8"
          stroke-linecap="round" stroke-linejoin="round">
          <rect x="9" y="3.5" width="6" height="11" rx="3" />
          <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v2.5" />
        </svg>
        <span>{{ starting ? m.record.waiting : recordLabel }}</span>
      </button>
      <button v-else type="button" class="btn small-btn recording" @click="stop">
        <span class="dot" aria-hidden="true"></span>
        <span>{{ format(m.record.stop, { seconds: seconds, max: MAX_SECONDS }) }}</span>
      </button>
      <button v-if="mine && !active" type="button" class="btn small-btn" @click="listenMine">
        <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8"
          stroke-linecap="round" stroke-linejoin="round">
          <path d="M8 5.5v13l10-6.5z" />
        </svg>
        <span>{{ m.record.listenMine }}</span>
      </button>
      <span v-if="mine && !active" class="muted small">{{ m.record.private }}</span>
    </template>
    <span v-else class="muted small">{{ m.record.unsupported }}</span>
    <p v-if="notice" class="small notice" role="status">{{ notice }}</p>
  </div>
</template>

<style scoped>
.record {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.3rem 0.6rem;
}
.small-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.7rem;
}
.small-btn svg {
  width: 1.1rem;
  height: 1.1rem;
}
.recording {
  border-color: var(--warn);
  color: var(--warn);
}
.dot {
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 50%;
  background: var(--warn);
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse {
  50% { opacity: 0.35; }
}
@media (prefers-reduced-motion: reduce) {
  .dot { animation: none; }
}
.notice {
  flex-basis: 100%;
  margin: 0;
  color: var(--warn);
}
</style>
