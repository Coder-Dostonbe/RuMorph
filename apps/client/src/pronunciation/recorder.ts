// The learner's own pronunciation: a short recording from the microphone, kept in memory only.
// Nothing is saved or sent anywhere; it is gone when the word window closes.

export const MAX_SECONDS = 5;

export type RecordError = "unsupported" | "denied" | "no_mic" | "busy" | "empty" | "failed";

export class RecorderError extends Error {
  constructor(readonly reason: RecordError) {
    super(reason);
  }
}

const TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];

export function recordingSupported(): boolean {
  return typeof navigator !== "undefined"
    && typeof navigator.mediaDevices?.getUserMedia === "function"
    && typeof MediaRecorder !== "undefined";
}

function pickType(): string {
  return TYPES.find((t) => MediaRecorder.isTypeSupported(t)) ?? "";
}

/** Maps getUserMedia's DOMException names to what the learner can do about it. */
export function reasonOf(e: unknown): RecordError {
  if (e instanceof RecorderError) return e.reason;
  const name = typeof e === "object" && e !== null && "name" in e ? String((e as { name: unknown }).name) : "";
  if (name === "NotAllowedError" || name === "SecurityError") return "denied";
  if (name === "NotFoundError" || name === "OverconstrainedError") return "no_mic";
  if (name === "NotReadableError" || name === "AbortError") return "busy";
  return "failed";
}

export interface Recording {
  /** Resolves with the audio when the recording stops (by stop() or after MAX_SECONDS). */
  readonly done: Promise<Blob>;
  stop(): void;
}

export async function startRecording(maxSeconds: number = MAX_SECONDS): Promise<Recording> {
  if (!recordingSupported()) throw new RecorderError("unsupported");
  let stream: MediaStream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
  } catch (e) {
    throw new RecorderError(reasonOf(e));
  }
  const type = pickType();
  let recorder: MediaRecorder;
  try {
    recorder = type ? new MediaRecorder(stream, { mimeType: type }) : new MediaRecorder(stream);
  } catch {
    stream.getTracks().forEach((t) => t.stop());
    throw new RecorderError("failed");
  }
  const chunks: Blob[] = [];
  let timer: ReturnType<typeof setTimeout> | undefined;
  const done = new Promise<Blob>((resolve, reject) => {
    recorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) chunks.push(event.data);
    });
    recorder.addEventListener("stop", () => {
      clearTimeout(timer);
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(chunks, { type: recorder.mimeType || type || "audio/webm" });
      if (blob.size === 0) reject(new RecorderError("empty"));
      else resolve(blob);
    });
    recorder.addEventListener("error", () => {
      clearTimeout(timer);
      stream.getTracks().forEach((t) => t.stop());
      reject(new RecorderError("failed"));
    });
  });
  recorder.start();
  timer = setTimeout(() => stop(), maxSeconds * 1000);
  function stop(): void {
    if (recorder.state !== "inactive") recorder.stop();
  }
  return { done, stop };
}
