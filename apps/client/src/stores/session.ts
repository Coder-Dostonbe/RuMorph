import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { ApiError, request } from "../api/http";
import type { AuthResponse, DeviceInfo, User } from "../api/types";
import { platform } from "../app/platform";
import { deleteSecret, getSecret, setSecret } from "../data/secrets";
import { useSettings } from "./settings";

const REFRESH_KEY = "refresh_token";

/** The signed-in user. The access token lives in memory only; the refresh token in secrets.ts. */
export const useSession = defineStore("session", () => {
  const settings = useSettings();
  const user = ref<User | null>(null);
  const accessToken = ref<string | null>(null);
  const restoring = ref(false);
  const signedIn = computed(() => user.value !== null);

  function device(name?: string): DeviceInfo {
    return { id: settings.deviceId, name: name?.trim() || defaultDeviceName(), platform };
  }

  async function accept(response: AuthResponse): Promise<void> {
    user.value = response.user;
    accessToken.value = response.access_token;
    await setSecret(REFRESH_KEY, response.refresh_token);
  }

  async function register(email: string, password: string, displayName: string, deviceName?: string): Promise<void> {
    await accept(
      await request<AuthResponse>(settings.apiUrl, "/v1/auth/register", {
        body: { email, password, display_name: displayName || null, device: device(deviceName) },
      }),
    );
  }

  async function login(email: string, password: string, deviceName?: string): Promise<void> {
    await accept(
      await request<AuthResponse>(settings.apiUrl, "/v1/auth/login", {
        body: { email, password, device: device(deviceName) },
      }),
    );
  }

  /** Trades the stored refresh token for a new pair. Returns false if there is no valid session. */
  async function refresh(): Promise<boolean> {
    const token = await getSecret(REFRESH_KEY);
    if (!token || !settings.apiUrl) return false;
    try {
      await accept(await request<AuthResponse>(settings.apiUrl, "/v1/auth/refresh", { body: { refresh_token: token } }));
      return true;
    } catch (error) {
      // A rejected token ends the session; a network error keeps it for the next try.
      if (error instanceof ApiError && error.status === 401) await clear();
      return false;
    }
  }

  /** On start-up: restore the session if a refresh token was saved. Offline is not an error. */
  async function restore(): Promise<void> {
    restoring.value = true;
    try {
      await refresh();
    } finally {
      restoring.value = false;
    }
  }

  async function logout(): Promise<void> {
    const token = await getSecret(REFRESH_KEY);
    if (token && settings.apiUrl) {
      try {
        await request(settings.apiUrl, "/v1/auth/logout", { body: { refresh_token: token } });
      } catch {
        // Signing out locally must work offline too; the server token then simply expires.
      }
    }
    await clear();
  }

  async function clear(): Promise<void> {
    user.value = null;
    accessToken.value = null;
    await deleteSecret(REFRESH_KEY);
  }

  /** An API call that needs the user; refreshes the access token once if it has expired. */
  async function authorized<T>(path: string, options: Parameters<typeof request>[2] = {}): Promise<T> {
    try {
      return await request<T>(settings.apiUrl, path, { ...options, token: accessToken.value });
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error;
      if (!(await refresh())) throw new ApiError(401, "session_expired", "session expired");
      return request<T>(settings.apiUrl, path, { ...options, token: accessToken.value });
    }
  }

  return { user, accessToken, restoring, signedIn, register, login, logout, restore, authorized };
});

function defaultDeviceName(): string {
  return platform === "android" ? "Android" : platform === "windows" ? "Windows" : "Browser";
}
