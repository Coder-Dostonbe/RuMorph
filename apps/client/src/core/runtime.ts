// Starts Pyodide and loads tilsim_core into it. Used inside the app's Web Worker
// (worker.ts) and directly by the Node tests, so it must not touch the DOM.
//
// Start-up is dominated by Python initialising itself, not by compiling the
// WebAssembly. So after the first start the whole initialised interpreter, with
// tilsim_core already imported, is saved as a memory snapshot; later starts
// restore it instead of initialising again (snapshotStore.ts keeps it).
import { loadPyodide, version as pyodideVersion } from "pyodide";

/** public/py/tilsim_core.json, written by scripts/pack-core.mjs. */
export interface CoreBundle {
  version: string;
  hash: string;
  files: Record<string, string>;
}

/** How start-up went, in milliseconds. Shown on the About page. */
export interface StartTimings {
  /** "snapshot": restored from a saved snapshot; "fresh": initialised from scratch. */
  mode: "snapshot" | "fresh";
  /** loadPyodide(): fetch + compile WebAssembly, then initialise or restore Python. */
  runtimeMs: number;
  /** Time spent inside WebAssembly.instantiate / instantiateStreaming (compiling). */
  compileMs: number;
  /** Write tilsim_core into the virtual file system and import it. */
  packageMs: number;
  totalMs: number;
  /** Size of the snapshot that was restored or made, if any. */
  snapshotBytes?: number;
  /** Set when a saved snapshot could not be used and start-up fell back to "fresh". */
  snapshotError?: string;
}

export interface CoreRuntime {
  /** Send one JSON request string to tilsim_core.bridge.handle and get the JSON reply string. */
  handle(raw: string): string;
  timings: StartTimings;
  /** A new snapshot, when this was a fresh start and one was requested. */
  snapshot?: Uint8Array;
}

const PACKAGE_DIR = "/tilsim";

/** Snapshots only fit the exact Pyodide build and tilsim_core bundle they were made with. */
export function snapshotKey(bundle: CoreBundle): string {
  return `pyodide-${pyodideVersion}:core-${bundle.hash}`;
}

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

function installFiles(pyodide: Awaited<ReturnType<typeof loadPyodide>>, bundle: CoreBundle): void {
  for (const [path, source] of Object.entries(bundle.files)) {
    if (path.includes("..") || path.startsWith("/")) throw new Error(`invalid path in core bundle: ${path}`);
    const full = `${PACKAGE_DIR}/${path}`;
    pyodide.FS.mkdirTree(full.slice(0, full.lastIndexOf("/")));
    pyodide.FS.writeFile(full, source, { encoding: "utf8" });
  }
}

/** Measures time spent compiling WebAssembly while `run` is in progress. */
async function measuringCompile<T>(run: () => Promise<T>): Promise<{ value: T; compileMs: number }> {
  const wasm = WebAssembly as unknown as Record<string, (...args: unknown[]) => Promise<unknown>>;
  const names = ["instantiate", "instantiateStreaming", "compile", "compileStreaming"];
  const originals = new Map(names.map((n) => [n, wasm[n]]));
  let compileMs = 0;
  for (const name of names) {
    const original = originals.get(name);
    if (!original) continue;
    wasm[name] = async (...args: unknown[]) => {
      const t = performance.now();
      try {
        return await original.apply(WebAssembly, args);
      } finally {
        compileMs += performance.now() - t;
      }
    };
  }
  try {
    return { value: await run(), compileMs };
  } finally {
    for (const [name, original] of originals) if (original) wasm[name] = original;
  }
}

type ModuleFactory = (settings: object) => Promise<{ growMemory?: (bytes: number) => unknown }>;

/** Pyodide restores a snapshot by copying it into the WebAssembly memory, but the memory starts
 *  at the size compiled into pyodide.asm.wasm (30 MiB) and is not grown first, so a snapshot of a
 *  larger heap fails with "offset is out of bounds". This wraps Pyodide's own module factory and
 *  grows the memory to the snapshot's size (Module.growMemory, which also refreshes the heap
 *  views) after the module is created and before the snapshot is copied in. */
async function snapshotModuleFactory(indexURL: string | undefined, bytes: number): Promise<ModuleFactory> {
  const url = indexURL ? `${indexURL}pyodide.asm.mjs` : "pyodide/pyodide.asm.mjs";
  const factory = ((await import(/* @vite-ignore */ url)) as { default: ModuleFactory }).default;
  return async (settings) => {
    const module = await factory(settings);
    if (typeof module.growMemory !== "function") throw new Error("this Pyodide build has no growMemory");
    module.growMemory(bytes);
    return module;
  };
}

export async function startCore(
  bundle: CoreBundle,
  options: {
    indexURL?: string;
    onStderr?: (line: string) => void;
    /** A snapshot saved earlier under snapshotKey(bundle). */
    snapshot?: Uint8Array | null;
    /** Make a snapshot after a fresh start (returned as CoreRuntime.snapshot). */
    makeSnapshot?: boolean;
  } = {},
): Promise<CoreRuntime> {
  const common = {
    indexURL: options.indexURL,
    // Python's print() is not part of the protocol; keep it out of the way.
    stdout: () => {},
    stderr: (line: string) => options.onStderr?.(line),
  };
  const t0 = performance.now();
  let snapshotError: string | undefined;

  if (options.snapshot) {
    try {
      const { value: pyodide, compileMs } = await measuringCompile(() =>
        (async () =>
          loadPyodide({
            ...common,
            _loadSnapshot: options.snapshot!,
            createPyodideModule: await snapshotModuleFactory(options.indexURL, options.snapshot!.byteLength),
          } as unknown as Parameters<typeof loadPyodide>[0]))(),
      );
      const t1 = performance.now();
      // The snapshot already holds tilsim_core imported; the files are written again so
      // that tracebacks and any later imports find them.
      installFiles(pyodide, bundle);
      const bridge = pyodide.pyimport("tilsim_core.bridge");
      const handle = bridge.handle as (raw: string) => string;
      const t2 = performance.now();
      return {
        handle: (raw) => handle(raw),
        timings: {
          mode: "snapshot",
          runtimeMs: t1 - t0,
          compileMs,
          packageMs: t2 - t1,
          totalMs: t2 - t0,
          snapshotBytes: options.snapshot.byteLength,
        },
      };
    } catch (error) {
      // A damaged or incompatible snapshot must never stop the app: start fresh instead.
      snapshotError = error instanceof Error ? error.message : String(error);
    }
  }

  const t0Fresh = performance.now();
  const { value: pyodide, compileMs } = await measuringCompile(() =>
    loadPyodide({ ...common, _makeSnapshot: options.makeSnapshot === true }),
  );
  const t1 = performance.now();
  installFiles(pyodide, bundle);
  // Imported with runPython (not pyimport) so no JavaScript proxy exists when the snapshot is taken.
  // "warmup" loads the lexicon and builds its index, so a start from the snapshot has it in memory.
  pyodide.runPython(
    `import sys\nif "${PACKAGE_DIR}" not in sys.path: sys.path.insert(0, "${PACKAGE_DIR}")\n` +
      `import tilsim_core.bridge\ntilsim_core.bridge.dispatch("warmup")`,
  );
  const snapshot = options.makeSnapshot ? pyodide.makeMemorySnapshot() : undefined;
  const handle = pyodide.pyimport("tilsim_core.bridge").handle as (raw: string) => string;
  const t2 = performance.now();

  return {
    handle: (raw) => handle(raw),
    snapshot,
    timings: {
      mode: "fresh",
      runtimeMs: t1 - t0Fresh,
      compileMs,
      packageMs: t2 - t1,
      totalMs: t2 - t0,
      snapshotBytes: snapshot?.byteLength,
      snapshotError,
    },
  };
}
