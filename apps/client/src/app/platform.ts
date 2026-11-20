// Which platform the app runs on, and which layout to use.
import { isTauri } from "@tauri-apps/api/core";
import { ref } from "vue";

export type Platform = "windows" | "android" | "browser";

export const inTauri = isTauri();
const isAndroidUA = typeof navigator !== "undefined" && /Android/i.test(navigator.userAgent);

export const platform: Platform = inTauri ? (isAndroidUA ? "android" : "windows") : "browser";

/** Narrow screens (and Android) get the bottom navigation; wide screens the sidebar. */
const query = typeof window !== "undefined" ? window.matchMedia("(max-width: 760px)") : null;
export const compact = ref(platform === "android" || (query?.matches ?? false));
query?.addEventListener("change", (event) => {
  compact.value = platform === "android" || event.matches;
});
