// The device's own voice for words without a recording. Windows (and browsers): the webview's
// speechSynthesis with an installed Russian voice. Android: its webview has none, so the
// phone's text-to-speech engine is used through the app shell (src-tauri/src/tts.rs).
import { invoke } from "@tauri-apps/api/core";
import { inTauri, platform } from "../app/platform";

export type VoiceState = "ready" | "no_russian" | "no_engine" | "unsupported";

function synth(): SpeechSynthesis | null {
  return typeof window !== "undefined" && "speechSynthesis" in window ? window.speechSynthesis : null;
}

function russianVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  return voices.find((v) => v.lang.toLowerCase().startsWith("ru")) ?? null;
}

/** Voices load asynchronously in Chromium; wait for them a little. */
async function voices(s: SpeechSynthesis): Promise<SpeechSynthesisVoice[]> {
  const now = s.getVoices();
  if (now.length) return now;
  return new Promise((resolve) => {
    const done = () => resolve(s.getVoices());
    s.addEventListener("voiceschanged", done, { once: true });
    setTimeout(done, 1500);
  });
}

const useShell = inTauri && platform === "android";

function asState(value: unknown): VoiceState {
  return value === "ready" || value === "no_russian" || value === "no_engine" ? value : "unsupported";
}

export async function voiceState(): Promise<VoiceState> {
  if (useShell) {
    try {
      return asState(await invoke<string>("tts_status"));
    } catch {
      return "no_engine";
    }
  }
  const s = synth();
  if (!s) return "unsupported";
  return russianVoice(await voices(s)) ? "ready" : "no_russian";
}

/** Normal device speed is a little slow already (0.85); `speed` slows it further. */
export const DEVICE_RATE = 0.85;

export async function speak(text: string, speed: number = 1): Promise<void> {
  const rate = Math.min(1, Math.max(0.25, DEVICE_RATE * speed));
  if (useShell) {
    await invoke("tts_speak", { text, rate });
    return;
  }
  const s = synth();
  const voice = s ? russianVoice(await voices(s)) : null;
  if (!s || !voice) throw new Error("no_russian");
  s.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.voice = voice;
  utterance.lang = voice.lang;
  utterance.rate = rate;
  s.speak(utterance);
}
