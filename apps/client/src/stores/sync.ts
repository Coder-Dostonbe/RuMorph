import { defineStore } from "pinia";
import { ref, watch } from "vue";
import { ApiError } from "../api/http";
import { keyValue } from "../data/keyValue";
import { onLocalChange, syncStore } from "../data/userData";
import { syncOnce, type Change, type PullResult, type PushResult, type SyncApi } from "../sync/engine";
import { useCards } from "./cards";
import { useSession } from "./session";
import { useVocabulary } from "./vocabulary";

export type SyncState =
  | "signed_out"      // no account on this device
  | "idle"            // signed in, not synced yet in this run of the app
  | "syncing"
  | "ok"              // the last sync finished
  | "offline"         // the last try could not reach the server
  | "failed"          // the server answered with an error
  | "other_account";  // the data on this device belongs to another account (the user decides)

const OWNER = "sync.owner";
const CURSOR = "sync.cursor";
const LAST_AT = "sync.last_at";

const EVERY_MS = 5 * 60_000;
const AFTER_CHANGE_MS = 20_000;

/**
 * Keeps the learner's data the same on every device of the account (src/sync/engine.ts).
 * Runs while the app is open: after sign-in, every few minutes, when the network comes back,
 * when the app comes to the front, and shortly after a change.
 */
export const useSync = defineStore("sync", () => {
  const session = useSession();
  const state = ref<SyncState>("signed_out");
  const lastSyncAt = ref<string | null>(null);
  const pending = ref(0);
  const rejected = ref(0);
  /** Technical detail of the last failure, for the admin panel only. */
  const detail = ref("");
  /** Raised whenever synced rows changed on this device; open screens reload on it. */
  const revision = ref(0);
  let running: Promise<void> | null = null;
  let again = false;
  let started = false;
  let changeTimer: ReturnType<typeof setTimeout> | null = null;

  const api: SyncApi = {
    push: (changes: Change[]) => session.authorized<PushResult>("/v1/sync/push", { body: { changes }, timeoutMs: 60_000 }),
    pull: (since: number) => session.authorized<PullResult>(`/v1/sync/pull?since=${since}`, { timeoutMs: 60_000 }),
  };

  async function refreshPending(): Promise<void> {
    pending.value = await syncStore.outboxCount();
  }

  /** Decides whose data is on this device. Returns false when the user has to choose. */
  async function prepare(userId: string): Promise<boolean> {
    const owner = await keyValue.get(OWNER);
    if (owner === userId) return true;
    if (owner) {
      state.value = "other_account";
      await refreshPending();
      return false;
    }
    // First account on this device: what was learnt here so far goes into the account.
    await syncStore.markAll();
    await keyValue.set(CURSOR, "0");
    await keyValue.set(OWNER, userId);
    return true;
  }

  async function run(): Promise<void> {
    const user = session.user;
    if (!user) {
      state.value = "signed_out";
      return;
    }
    if (!(await prepare(user.id))) return;
    state.value = "syncing";
    try {
      const cursor = Number((await keyValue.get(CURSOR)) ?? "0") || 0;
      const outcome = await syncOnce(api, cursor, (c) => keyValue.set(CURSOR, String(c)));
      rejected.value = outcome.rejected;
      detail.value = outcome.rejected ? `rejected: ${outcome.rejectedCodes.join(", ")}` : "";
      if (outcome.changed) await reload();
      lastSyncAt.value = new Date().toISOString();
      await keyValue.set(LAST_AT, lastSyncAt.value);
      state.value = "ok";
    } catch (e) {
      detail.value = e instanceof ApiError ? `${e.code}: ${e.message}` : String(e);
      if (!session.user) state.value = "signed_out";
      else state.value = e instanceof ApiError && e.code === "network" ? "offline" : "failed";
    } finally {
      await refreshPending();
    }
  }

  /** Syncs now; a call during a running sync makes it run once more afterwards. */
  async function syncNow(): Promise<void> {
    if (running) {
      again = true;
      return running;
    }
    running = (async () => {
      do {
        again = false;
        await run();
      } while (again && session.user && state.value === "ok");
    })().finally(() => {
      running = null;
    });
    return running;
  }

  async function reload(): Promise<void> {
    await Promise.all([useVocabulary().reload(), useCards().reload()]);
    revision.value++;
  }

  /** The device holds another account's data: remove it here and take this account's data. */
  async function replaceLocalData(): Promise<void> {
    const user = session.user;
    if (!user) return;
    await syncStore.wipe();
    await keyValue.set(CURSOR, "0");
    await keyValue.set(OWNER, user.id);
    await reload();
    await syncNow();
  }

  /** Before signing out: send what is still queued, if the server can be reached. */
  async function flush(): Promise<void> {
    if (session.user && state.value !== "other_account") await syncNow();
  }

  function start(): void {
    if (started) return;
    started = true;
    void keyValue.get(LAST_AT).then((v) => (lastSyncAt.value ??= v));
    void refreshPending();
    watch(
      () => session.user?.id ?? null,
      (id) => {
        if (id) void syncNow();
        else state.value = "signed_out";
      },
      { immediate: true },
    );
    setInterval(() => {
      if (session.user) void syncNow();
    }, EVERY_MS);
    window.addEventListener("online", () => {
      if (session.user) void syncNow();
    });
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState !== "visible" || !session.user) return;
      const last = lastSyncAt.value ? Date.parse(lastSyncAt.value) : 0;
      if (Date.now() - last > 60_000) void syncNow();
    });
    onLocalChange(() => {
      void refreshPending();
      if (!session.user) return;
      if (changeTimer) clearTimeout(changeTimer);
      changeTimer = setTimeout(() => void syncNow(), AFTER_CHANGE_MS);
    });
  }

  return { state, lastSyncAt, pending, rejected, detail, revision, start, syncNow, flush, replaceLocalData, refreshPending };
});
