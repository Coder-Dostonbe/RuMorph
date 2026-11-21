import { invoke } from "@tauri-apps/api/core";
import { defineStore } from "pinia";
import { ref } from "vue";
import { inTauri } from "../app/platform";

export interface UpdateInfo {
  version: string;
  current: string;
  notes: string | null;
}

export type UpdateState =
  | "idle" // not checked yet
  | "checking"
  | "none" // up to date
  | "available"
  | "installing"
  | "permission" // Android: allow "install unknown apps" for Zabon, then tap again
  | "installer" // Android: the system installer is open
  | "off" // this build has no update key (or runs in a browser)
  | "failed";

const FIRST_CHECK_MS = 8_000;

/**
 * App updates from the GitHub "dev" release (src-tauri/src/update.rs). Checked once, a few
 * seconds after start, so that it does not slow the start; the user decides when to install.
 */
export const useUpdates = defineStore("updates", () => {
  const state = ref<UpdateState>(inTauri ? "idle" : "off");
  const info = ref<UpdateInfo | null>(null);
  const error = ref("");
  const dismissed = ref(false);
  const checkedAt = ref<Date | null>(null);

  async function check(): Promise<void> {
    if (!inTauri || state.value === "checking" || state.value === "installing") return;
    state.value = "checking";
    error.value = "";
    try {
      info.value = await invoke<UpdateInfo | null>("update_check");
      state.value = info.value ? "available" : "none";
    } catch (e) {
      error.value = String(e);
      state.value = error.value === "not_configured" ? "off" : "failed";
    } finally {
      checkedAt.value = new Date();
    }
  }

  async function install(): Promise<void> {
    if (!inTauri || state.value === "installing") return;
    state.value = "installing";
    error.value = "";
    try {
      // Windows does not return from here: the installer replaces and reopens the app.
      const outcome = await invoke<{ status: string }>("update_install");
      state.value = outcome.status === "permission" ? "permission" : "installer";
    } catch (e) {
      error.value = String(e);
      state.value = "failed";
    }
  }

  function startChecking(): void {
    if (inTauri) setTimeout(() => void check(), FIRST_CHECK_MS);
  }

  return { state, info, error, dismissed, checkedAt, check, install, startChecking };
});
