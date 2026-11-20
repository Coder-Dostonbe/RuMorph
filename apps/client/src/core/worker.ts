// Web Worker that owns Pyodide, so loading and running Python never blocks the UI.
/// <reference lib="webworker" />
import type { FromWorker, ToWorker } from "./protocol";
import { isCoreBundle, startCore, type CoreRuntime } from "./runtime";

const scope = self as unknown as DedicatedWorkerGlobalScope;
let runtime: CoreRuntime | null = null;

function post(message: FromWorker): void {
  scope.postMessage(message);
}

async function start(): Promise<void> {
  try {
    const base = new URL("/", scope.location.href);
    const response = await fetch(new URL("py/tilsim_core.json", base));
    if (!response.ok) throw new Error(`tilsim_core.json: HTTP ${response.status}`);
    const bundle: unknown = await response.json();
    if (!isCoreBundle(bundle)) throw new Error("tilsim_core.json has an unexpected shape");
    runtime = await startCore(bundle, {
      indexURL: new URL("pyodide/", base).href,
      onStderr: (line) => post({ type: "stderr", line }),
    });
    post({ type: "ready", timings: runtime.timings, bundleVersion: bundle.version, bundleHash: bundle.hash });
  } catch (error) {
    post({ type: "failed", message: error instanceof Error ? error.message : String(error) });
  }
}

scope.onmessage = (event: MessageEvent<ToWorker>) => {
  const message = event.data;
  if (message.type === "start") {
    void start();
  } else if (message.type === "call") {
    // client.ts only sends calls after "ready"; answer anyway so a caller never hangs.
    const raw = runtime
      ? runtime.handle(message.raw)
      : JSON.stringify({ id: null, ok: false, error: { code: "not_ready", message: "core is not running" } });
    post({ type: "reply", seq: message.seq, raw });
  }
};
