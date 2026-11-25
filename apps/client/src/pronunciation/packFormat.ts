// The voice pack file (tools/pronunciation/pack.py): b"ZVP1" | header length (uint32 BE) |
// header JSON | audio. Each word's audio is a complete Ogg Opus file inside the audio part.

export interface PackHeader {
  format: "zabon-voice-pack";
  version: 1;
  mime: string;
  voice: { id: string; engine?: string; model?: string; license?: string };
  /** word -> [offset, length, author, license]; offsets count from the start of the audio. */
  words: Record<string, [number, number, string, string]>;
}

export interface ParsedPack {
  header: PackHeader;
  audio: Uint8Array;
}

export class PackError extends Error {}

const MAGIC = [0x5a, 0x56, 0x50, 0x31]; // "ZVP1"

export function parsePack(bytes: Uint8Array): ParsedPack {
  if (bytes.length < 8 || MAGIC.some((b, i) => bytes[i] !== b)) throw new PackError("not a voice pack");
  const size = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength).getUint32(4, false);
  if (8 + size > bytes.length) throw new PackError("truncated header");
  let header: PackHeader;
  try {
    header = JSON.parse(new TextDecoder().decode(bytes.subarray(8, 8 + size))) as PackHeader;
  } catch {
    throw new PackError("bad header");
  }
  if (header.format !== "zabon-voice-pack" || header.version !== 1 || typeof header.words !== "object") {
    throw new PackError("unknown pack version");
  }
  const audio = bytes.subarray(8 + size);
  for (const [word, entry] of Object.entries(header.words)) {
    const [offset, length] = entry;
    if (!Number.isInteger(offset) || !Number.isInteger(length) || offset < 0 || length <= 0 || offset + length > audio.length) {
      throw new PackError(`bad range for ${word}`);
    }
  }
  return { header, audio };
}

export async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", bytes as BufferSource);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}
