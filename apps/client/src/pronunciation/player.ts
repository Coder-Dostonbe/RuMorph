// One audio player for the whole app, so a word's sample and the learner's own recording never
// play over each other. The audio is a blob (the CSP allows media from blob: only).

export const speeds = [1, 0.75, 0.5] as const;
export type Speed = (typeof speeds)[number];
export const isSpeed = (v: unknown): v is Speed => typeof v === "number" && (speeds as readonly number[]).includes(v);

let player: HTMLAudioElement | null = null;
let objectUrl = "";

export function stopAudio(): void {
  player?.pause();
  player = null;
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = "";
}

/** Plays the blob; slower speeds keep the pitch, so the word only gets longer. */
export function playBlob(blob: Blob, speed: number = 1): Promise<void> {
  stopAudio();
  objectUrl = URL.createObjectURL(blob);
  const audio = new Audio(objectUrl);
  audio.preservesPitch = true;
  audio.playbackRate = speed;
  // playbackRate resets to defaultPlaybackRate on load in some engines.
  audio.defaultPlaybackRate = speed;
  player = audio;
  return audio.play();
}
