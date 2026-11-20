// The refresh token is kept by the Rust shell: Windows Credential Manager on
// Windows, a file in the app's private data folder on Android. It is never put
// in the SQLite database or in browser storage. In a plain browser it is kept
// in memory only, so a reload signs the user out.
import { invoke } from "@tauri-apps/api/core";
import { inTauri } from "../app/platform";

const memory = new Map<string, string>();

export const secretsPersist = inTauri;

export async function getSecret(name: string): Promise<string | null> {
  if (!inTauri) return memory.get(name) ?? null;
  return (await invoke<string | null>("secret_get", { name })) ?? null;
}

export async function setSecret(name: string, value: string): Promise<void> {
  if (!inTauri) {
    memory.set(name, value);
    return;
  }
  await invoke("secret_set", { name, value });
}

export async function deleteSecret(name: string): Promise<void> {
  if (!inTauri) {
    memory.delete(name);
    return;
  }
  await invoke("secret_delete", { name });
}
