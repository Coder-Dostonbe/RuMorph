// Starts Pyodide and loads tilsim_core into it. Used inside the app's Web Worker
// (worker.ts) and directly by the Node tests, so it must not touch the DOM.
import { loadPyodide } from "pyodide";

/** public/py/tilsim_core.json, written by scripts/pack-core.mjs. */
export interface CoreBundle {
  version: string;
  hash: string;
  files: Record<string, string>;
}

/** How long start-up took, in milliseconds. Shown on the About page. */
export interface StartTimings {
  /** Download + compile the WebAssembly runtime and the standard library. */
  runtimeMs: number;
  /** Write tilsim_core into the virtual file system and import it. */
  packageMs: number;
  totalMs: number;
}

export interface CoreRuntime {
  /** Send one JSON request string to tilsim_core.bridge.handle and get the JSON reply string. */
  handle(raw: string): string;
  timings: StartTimings;
}

const PACKAGE_DIR = "/tilsim";

export function isCoreBundle(value: unknown): value is CoreBundle {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.version === "string" &&
    typeof v.hash === "string" &&
    typeof v.files === "object" &&
    v.files !== null &&
    Object.values(v.files).every((f) => typeof f === "string")
  );
}

export async function startCore(
  bundle: CoreBundle,
  options: { indexURL?: string; onStderr?: (line: string) => void } = {},
): Promise<CoreRuntime> {
  const t0 = performance.now();
  const pyodide = await loadPyodide({
    indexURL: options.indexURL,
    // Python's print() is not part of the protocol; keep it out of the way.
    stdout: () => {},
    stderr: (line: string) => options.onStderr?.(line),
  });
  const t1 = performance.now();

  for (const [path, source] of Object.entries(bundle.files)) {
    if (path.includes("..") || path.startsWith("/")) throw new Error(`invalid path in core bundle: ${path}`);
    const full = `${PACKAGE_DIR}/${path}`;
    pyodide.FS.mkdirTree(full.slice(0, full.lastIndexOf("/")));
    pyodide.FS.writeFile(full, source, { encoding: "utf8" });
  }
  pyodide.runPython(`import sys\nif "${PACKAGE_DIR}" not in sys.path: sys.path.insert(0, "${PACKAGE_DIR}")`);
  const bridge = pyodide.pyimport("tilsim_core.bridge");
  const handle = bridge.handle as (raw: string) => string;
  const t2 = performance.now();

  return {
    handle: (raw) => handle(raw),
    timings: { runtimeMs: t1 - t0, packageMs: t2 - t1, totalMs: t2 - t0 },
  };
}
