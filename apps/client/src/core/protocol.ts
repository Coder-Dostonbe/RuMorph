// Messages between the app (client.ts) and the Pyodide Web Worker (worker.ts),
// and the shapes of the tilsim_core bridge replies (core/src/tilsim_core/bridge.py).
import type { StartTimings } from "./runtime";

export type ToWorker =
  | { type: "start" }
  | { type: "call"; seq: number; raw: string };

export type FromWorker =
  | { type: "ready"; timings: StartTimings; bundleVersion: string; bundleHash: string }
  | { type: "failed"; message: string }
  | { type: "reply"; seq: number; raw: string }
  | { type: "stderr"; line: string };

export interface BridgeOk<T> {
  id: number | string;
  ok: true;
  result: T;
}

export interface BridgeErr {
  id: number | string | null;
  ok: false;
  error: { code: string; message: string };
}

export type BridgeReply<T> = BridgeOk<T> | BridgeErr;

/** Result of the "version" operation. */
export interface CoreVersion {
  core: string;
  protocol: number;
  python: string;
  platform: string;
}

/** The bridge protocol this app understands (tilsim_core.PROTOCOL_VERSION). */
export const SUPPORTED_PROTOCOL = 1;
