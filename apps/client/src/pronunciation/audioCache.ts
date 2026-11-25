// Recordings already played are kept on the device, so they play again without internet.
// Cache Storage keeps them across restarts; where it is missing, they are kept until the app
// closes.

const NAME = "zabon-pronunciations-v1";
const memory = new Map<string, Blob>();

async function store(): Promise<Cache | null> {
  try {
    return typeof caches !== "undefined" ? await caches.open(NAME) : null;
  } catch {
    return null;
  }
}

export async function cached(url: string): Promise<Blob | null> {
  const hit = memory.get(url);
  if (hit) return hit;
  const cache = await store();
  const response = cache ? await cache.match(url).catch(() => undefined) : undefined;
  if (!response) return null;
  const blob = await response.blob();
  memory.set(url, blob);
  return blob;
}

export async function keep(url: string, blob: Blob): Promise<void> {
  memory.set(url, blob);
  const cache = await store();
  if (!cache) return;
  try {
    await cache.put(url, new Response(blob, { headers: { "content-type": blob.type || "audio/mpeg" } }));
  } catch {
    // Storage full or unavailable: the copy in memory still serves this session.
  }
}
