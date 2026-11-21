// The admin password of this device. Only a salted PBKDF2-SHA-256 hash is kept, in the app's
// secret store (Windows Credential Manager, or a private file on Android: see src-tauri/src/secret.rs).
// The repository is public, so no password or hash is ever part of the build.
//
// This is a temporary lock for testing builds, not a security boundary: whoever controls the
// device can reset the app's data. It keeps the technical pages out of an ordinary user's way.

export const MIN_LENGTH = 6;
const ITERATIONS = 210_000;

export interface PasswordRecord {
  alg: "pbkdf2-sha256";
  iterations: number;
  salt: string; // base64
  hash: string; // base64
}

const toBase64 = (bytes: Uint8Array): string => btoa(String.fromCharCode(...bytes));
const fromBase64 = (text: string): Uint8Array => Uint8Array.from(atob(text), (c) => c.charCodeAt(0));

async function derive(password: string, salt: Uint8Array, iterations: number): Promise<Uint8Array> {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(password.normalize("NFC")), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt: salt as BufferSource, iterations }, key, 256);
  return new Uint8Array(bits);
}

export async function hashPassword(password: string, iterations = ITERATIONS): Promise<PasswordRecord> {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  return { alg: "pbkdf2-sha256", iterations, salt: toBase64(salt), hash: toBase64(await derive(password, salt, iterations)) };
}

export function parseRecord(text: string | null): PasswordRecord | null {
  if (!text) return null;
  try {
    const r = JSON.parse(text) as Partial<PasswordRecord>;
    if (r.alg === "pbkdf2-sha256" && typeof r.iterations === "number" && r.iterations > 0 && typeof r.salt === "string" && typeof r.hash === "string") {
      return r as PasswordRecord;
    }
  } catch {
    // An unreadable record counts as none.
  }
  return null;
}

export async function verifyPassword(password: string, record: PasswordRecord): Promise<boolean> {
  const actual = await derive(password, fromBase64(record.salt), record.iterations);
  const expected = fromBase64(record.hash);
  if (actual.length !== expected.length) return false;
  let diff = 0;
  for (let i = 0; i < actual.length; i++) diff |= actual[i]! ^ expected[i]!;
  return diff === 0;
}
