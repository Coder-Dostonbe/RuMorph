import { defineStore } from "pinia";
import { ref, watch } from "vue";
import { normaliseBaseUrl } from "../api/http";
import { keyValue } from "../data/keyValue";
import { isLocale, locale, type Locale } from "../i18n";

export type Theme = "light" | "dark" | "system";
export const themes: Theme[] = ["light", "dark", "system"];
const isTheme = (v: unknown): v is Theme => typeof v === "string" && (themes as string[]).includes(v);

function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  if (theme === "system") delete root.dataset.theme;
  else root.dataset.theme = theme;
}

export const useSettings = defineStore("settings", () => {
  const theme = ref<Theme>("system");
  const apiUrl = ref<string>(import.meta.env.VITE_API_URL ?? "");
  const deviceId = ref<string>("");
  const loaded = ref(false);
  const storageKind = keyValue.kind;

  async function load(): Promise<void> {
    const [savedLocale, savedTheme, savedApi, savedDevice] = await Promise.all([
      keyValue.get("locale"),
      keyValue.get("theme"),
      keyValue.get("api_url"),
      keyValue.get("device_id"),
    ]);
    if (isLocale(savedLocale)) locale.value = savedLocale;
    if (isTheme(savedTheme)) theme.value = savedTheme;
    if (savedApi !== null) apiUrl.value = savedApi;
    if (savedDevice) {
      deviceId.value = savedDevice;
    } else {
      deviceId.value = crypto.randomUUID();
      await keyValue.set("device_id", deviceId.value);
    }
    applyTheme(theme.value);
    loaded.value = true;
  }

  async function setLocale(value: Locale): Promise<void> {
    locale.value = value;
    await keyValue.set("locale", value);
  }

  async function setTheme(value: Theme): Promise<void> {
    theme.value = value;
    await keyValue.set("theme", value);
  }

  async function setApiUrl(value: string): Promise<void> {
    apiUrl.value = normaliseBaseUrl(value);
    await keyValue.set("api_url", apiUrl.value);
  }

  watch(theme, applyTheme);
  watch(locale, (value) => (document.documentElement.lang = value), { immediate: true });

  return { theme, apiUrl, deviceId, loaded, storageKind, load, setLocale, setTheme, setApiUrl };
});
