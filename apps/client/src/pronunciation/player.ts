// One audio player for the whole app, so two words never play over each other. The audio is a blob (the CSP allows media from blob: only).

export const speeds = [1, 0.75, 0.5] as const;
export type Speed = (typeof speeds)[number];

/** Presses closer together than this slow the word down; a longer pause starts again at 1x. */
export const SLOWER_WITHIN_MS = 5000;

export interface LastPress {
  speed: Speed;
  at: number;
}

/** Listen pressed again soon: 1x, then 0.75x, then 0.5x, then 1x again. */
export function nextSpeed(last: LastPress | null, now: number): Speed {
  if (!last || now - last.at > SLOWER_WITHIN_MS || now < last.at) return 1;
  if (last.speed === 1) return 0.75;
  if (last.speed === 0.75) return 0.5;
  return 1;
}

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
