import { defineStore } from "pinia";
import { ref } from "vue";
import { core, CoreError, type CoreReady } from "../core/client";
import type { CoreVersion } from "../core/protocol";

export type CoreStatus = "idle" | "loading" | "ready" | "failed";

/** State of the offline Python module (tilsim_core under Pyodide). */
export const useCore = defineStore("core", () => {
  const status = ref<CoreStatus>("idle");
  const info = ref<CoreReady | null>(null);
  const version = ref<CoreVersion | null>(null);
  const error = ref<string>("");

  async function start(): Promise<void> {
    if (status.value === "loading" || status.value === "ready") return;
    status.value = "loading";
    error.value = "";
    try {
      info.value = await core.start();
      version.value = await core.call<CoreVersion>("version");
      status.value = "ready";
    } catch (e) {
      error.value = e instanceof CoreError ? `${e.code}: ${e.message}` : String(e);
      status.value = "failed";
    }
  }

  return { status, info, version, error, start, stderr: core.stderr };
});
