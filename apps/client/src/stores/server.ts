import { defineStore } from "pinia";
import { ref } from "vue";
import { ApiError, request } from "../api/http";
import type { Health } from "../api/types";
import { useSettings } from "./settings";

export type ServerState = "unknown" | "checking" | "ok" | "unreachable" | "not_configured";

/** Result of the last real call to GET /health. Nothing here is assumed. */
export const useServer = defineStore("server", () => {
  const settings = useSettings();
  const state = ref<ServerState>("unknown");
  const health = ref<Health | null>(null);
  const latencyMs = ref<number | null>(null);
  const error = ref("");

  async function check(): Promise<void> {
    if (!settings.apiUrl) {
      state.value = "not_configured";
      return;
    }
    state.value = "checking";
    const t0 = performance.now();
    try {
      health.value = await request<Health>(settings.apiUrl, "/health", { timeoutMs: 10_000 });
      latencyMs.value = Math.round(performance.now() - t0);
      state.value = "ok";
    } catch (e) {
      health.value = null;
      error.value = e instanceof ApiError ? `${e.code}: ${e.message}` : String(e);
      state.value = "unreachable";
    }
  }

  return { state, health, latencyMs, error, check };
});
