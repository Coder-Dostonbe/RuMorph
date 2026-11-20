// Web Worker that owns Pyodide, so loading and running Python never blocks the UI.
/// <reference lib="webworker" />
import type { FromWorker, ResourceTiming, ToWorker } from "./protocol";
import { isCoreBundle, snapshotKey, startCore, type CoreRuntime } from "./runtime";
import { deleteSnapshot, loadSnapshot, saveSnapshot } from "./snapshotStore";

const scope = self as unknown as DedicatedWorkerGlobalScope;
let runtime: CoreRuntime | null = null;

function post(message: FromWorker): void {
  scope.postMessage(message);
}

/** How long the big runtime files took to arrive (Resource Timing API). */
function resourceTimings(): ResourceTiming[] {
  return performance
    .getEntriesByType("resource")
    .filter((e) => /pyodide\.asm\.wasm|python_stdlib\.zip|pyodide\.asm\.mjs|tilsim_core\.json/.test(e.name))
    .map((e) => {
      const r = e as PerformanceResourceTiming;
      return { name: r.name.split("/").pop() ?? r.name, ms: r.duration, bytes: r.decodedBodySize || r.encodedBodySize };
    });
}

async function start(useSnapshot: boolean): Promise<void> {
  try {
    const base = new URL("/", scope.location.href);
    const response = await fetch(new URL("py/tilsim_core.json", base));
    if (!response.ok) throw new Error(`tilsim_core.json: HTTP ${response.status}`);
    const bundle: unknown = await response.json();
    if (!isCoreBundle(bundle)) throw new Error("tilsim_core.json has an unexpected shape");

    const key = snapshotKey(bundle);
    const t = performance.now();
    const snapshot = useSnapshot ? await loadSnapshot(key) : null;
    const snapshotReadMs = performance.now() - t;

    runtime = await startCore(bundle, {
      indexURL: new URL("pyodide/", base).href,
      onStderr: (line) => post({ type: "stderr", line }),
      snapshot,
      makeSnapshot: useSnapshot && !snapshot,
    });
    if (runtime.timings.snapshotError) await deleteSnapshot();

    post({
      type: "ready",
      timings: runtime.timings,
      snapshotReadMs: snapshot ? snapshotReadMs : undefined,
      resources: resourceTimings(),
      bundleVersion: bundle.version,
      bundleHash: bundle.hash,
    });

    // Saved after "ready", so the first start is not made slower by the write.
    if (runtime.snapshot) {
      const t2 = performance.now();
      const saved = await saveSnapshot(key, runtime.snapshot);
      post({ type: "snapshot_saved", saved, ms: performance.now() - t2, bytes: runtime.snapshot.byteLength });
      runtime.snapshot = undefined;
    }
  } catch (error) {
    post({ type: "failed", message: error instanceof Error ? error.message : String(error) });
  }
}

scope.onmessage = (event: MessageEvent<ToWorker>) => {
  const message = event.data;
  if (message.type === "start") {
    void start(message.useSnapshot);
  } else if (message.type === "forget_snapshot") {
    void deleteSnapshot().then(() => post({ type: "snapshot_forgotten" }));
  } else if (message.type === "call") {
    // client.ts only sends calls after "ready"; answer anyway so a caller never hangs.
    const raw = runtime
      ? runtime.handle(message.raw)
      : JSON.stringify({ id: null, ok: false, error: { code: "not_ready", message: "core is not running" } });
    post({ type: "reply", seq: message.seq, raw });
  }
};
