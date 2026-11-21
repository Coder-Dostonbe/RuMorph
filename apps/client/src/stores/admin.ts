import { defineStore } from "pinia";
import { ref } from "vue";
import { hashPassword, MIN_LENGTH, parseRecord, verifyPassword, type PasswordRecord } from "../admin/password";
import { getSecret, setSecret } from "../data/secrets";

const SECRET = "admin_password";
const MAX_FAILURES = 5;
const LOCKOUT_MS = 30_000;

export type AdminResult = "ok" | "wrong" | "too_short" | "mismatch" | "locked_out";

/**
 * The temporary admin mode: technical pages and translation editing. It stays unlocked until
 * the app is closed or "Log out" is pressed; nothing about it is saved except the password hash.
 */
export const useAdmin = defineStore("admin", () => {
  const unlocked = ref(false);
  const configured = ref<boolean | null>(null);
  const lockedUntil = ref(0);
  let failures = 0;
  let record: PasswordRecord | null = null;

  async function load(): Promise<void> {
    record = parseRecord(await getSecret(SECRET));
    configured.value = record !== null;
  }

  async function setPassword(password: string, repeat: string): Promise<AdminResult> {
    if (password.length < MIN_LENGTH) return "too_short";
    if (password !== repeat) return "mismatch";
    const next = await hashPassword(password);
    await setSecret(SECRET, JSON.stringify(next));
    record = next;
    configured.value = true;
    unlocked.value = true;
    return "ok";
  }

  /** First setup only: an existing password is changed from inside the admin panel. */
  async function create(password: string, repeat: string): Promise<AdminResult> {
    await load();
    if (configured.value) return "wrong";
    return setPassword(password, repeat);
  }

  async function unlock(password: string): Promise<AdminResult> {
    if (Date.now() < lockedUntil.value) return "locked_out";
    if (!record) await load();
    if (record && (await verifyPassword(password, record))) {
      failures = 0;
      unlocked.value = true;
      return "ok";
    }
    failures += 1;
    if (failures >= MAX_FAILURES) {
      failures = 0;
      lockedUntil.value = Date.now() + LOCKOUT_MS;
      return "locked_out";
    }
    return "wrong";
  }

  async function change(current: string, password: string, repeat: string): Promise<AdminResult> {
    if (!unlocked.value || !record || !(await verifyPassword(current, record))) return "wrong";
    return setPassword(password, repeat);
  }

  function lock(): void {
    unlocked.value = false;
  }

  return { unlocked, configured, lockedUntil, load, create, unlock, change, lock };
});
