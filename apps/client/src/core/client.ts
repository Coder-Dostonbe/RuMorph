// The app's handle on tilsim_core: starts the Pyodide worker and sends typed calls.
import type { BridgeReply, FromWorker, ToWorker } from "./protocol";
import type { StartTimings } from "./runtime";

export class CoreError extends Error {
  constructor(
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export interface CoreReady {
  timings: StartTimings;
  bundleVersion: string;
  bundleHash: string;
}

const CALL_TIMEOUT_MS = 15_000;
const START_TIMEOUT_MS = 120_000;

interface Pending {
  resolve: (raw: string) => void;
  reject: (error: CoreError) => void;
  timer: ReturnType<typeof setTimeout>;
}

export class CoreClient {
  private worker: Worker | null = null;
  private seq = 0;
  private pending = new Map<number, Pending>();
  private ready: Promise<CoreReady> | null = null;
  readonly stderr: string[] = [];

  /** Starts the worker once; later calls return the same promise. */
  start(): Promise<CoreReady> {
    if (this.ready) return this.ready;
    this.ready = new Promise<CoreReady>((resolve, reject) => {
      const worker = new Worker(new URL("./worker.ts", import.meta.url), { type: "module" });
      this.worker = worker;
      const timer = setTimeout(() => reject(new CoreError("timeout", "core start-up timed out")), START_TIMEOUT_MS);
      worker.onmessage = (event: MessageEvent<FromWorker>) => {
        const message = event.data;
        switch (message.type) {
          case "ready":
            clearTimeout(timer);
            resolve({ timings: message.timings, bundleVersion: message.bundleVersion, bundleHash: message.bundleHash });
            break;
          case "failed":
            clearTimeout(timer);
            reject(new CoreError("start_failed", message.message));
            break;
          case "reply":
            this.settle(message.seq, message.raw);
            break;
          case "stderr":
            this.stderr.push(message.line);
            if (this.stderr.length > 200) this.stderr.shift();
            break;
        }
      };
      worker.onerror = (event) => {
        clearTimeout(timer);
        reject(new CoreError("start_failed", event.message || "core worker failed"));
      };
      worker.postMessage({ type: "start" } satisfies ToWorker);
    });
    return this.ready;
  }

  /** Runs one tilsim_core operation. Rejects with CoreError for bridge errors and timeouts. */
  async call<T>(op: string, args: Record<string, unknown> = {}): Promise<T> {
    await this.start();
    const seq = ++this.seq;
    const raw = await new Promise<string>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(seq);
        reject(new CoreError("timeout", `core operation "${op}" timed out`));
      }, CALL_TIMEOUT_MS);
      this.pending.set(seq, { resolve, reject, timer });
      this.worker!.postMessage({ type: "call", seq, raw: JSON.stringify({ id: seq, op, args }) } satisfies ToWorker);
    });
    const reply = JSON.parse(raw) as BridgeReply<T>;
    if (!reply.ok) throw new CoreError(reply.error.code, reply.error.message);
    return reply.result;
  }

  private settle(seq: number, raw: string): void {
    const entry = this.pending.get(seq);
    if (!entry) return;
    clearTimeout(entry.timer);
    this.pending.delete(seq);
    entry.resolve(raw);
  }
}

export const core = new CoreClient();
