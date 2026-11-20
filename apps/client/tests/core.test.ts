// Runs tilsim_core inside real Pyodide (under Node), the same runtime the app uses,
// and records how long start-up takes on this machine.
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { BridgeReply, CoreVersion } from "../src/core/protocol";
import { isCoreBundle, snapshotKey, startCore, type CoreBundle, type CoreRuntime } from "../src/core/runtime";

const bundle: unknown = JSON.parse(readFileSync(new URL("../public/py/tilsim_core.json", import.meta.url), "utf8"));

function call<T>(runtime: CoreRuntime, op: string, args: object = {}): BridgeReply<T> {
  return JSON.parse(runtime.handle(JSON.stringify({ id: 1, op, args }))) as BridgeReply<T>;
}

describe("tilsim_core under Pyodide", () => {
  let runtime: CoreRuntime;

  it("starts", async () => {
    expect(isCoreBundle(bundle)).toBe(true);
    runtime = await startCore(bundle as Parameters<typeof startCore>[0]);
    const t = runtime.timings;
    console.log(
      `Pyodide start-up: runtime ${t.runtimeMs.toFixed(0)} ms, package ${t.packageMs.toFixed(0)} ms, total ${t.totalMs.toFixed(0)} ms`,
    );
    expect(t.totalMs).toBeGreaterThan(0);
  });

  it("reports its version from inside WebAssembly", () => {
    const reply = call<CoreVersion>(runtime, "version");
    expect(reply.ok).toBe(true);
    if (reply.ok) {
      expect(reply.result.platform).toBe("emscripten");
      expect(reply.result.protocol).toBe(1);
    }
  });

  it("round-trips Cyrillic and Uzbek text", () => {
    const text = "Здравствуйте, o'zbekcha ғ қ ў ҳ";
    const reply = call<{ text: string }>(runtime, "echo", { text });
    expect(reply).toEqual({ id: 1, ok: true, result: { text } });
  });

  it("returns bridge errors as data", () => {
    const reply = call(runtime, "nope");
    expect(reply.ok).toBe(false);
    if (!reply.ok) expect(reply.error.code).toBe("unknown_op");
  });

  it("analyses a Russian word with the bundled lexicon", () => {
    const reply = call<{ status: string; lemmas: string[]; readings: { description: string }[] }>(
      runtime, "analyze", { word: "книги" },
    );
    expect(reply.ok).toBe(true);
    if (reply.ok) {
      expect(reply.result.status).toBe("ambiguous");
      expect(reply.result.lemmas).toEqual(["книга"]);
      expect(reply.result.readings).toHaveLength(3);
    }
  });

  it("measures a warm analysis", () => {
    const t0 = performance.now();
    for (let i = 0; i < 100; i++) call(runtime, "analyze", { word: "столом" });
    const perCall = (performance.now() - t0) / 100;
    console.log(`warm analyze: ${perCall.toFixed(3)} ms`);
    expect(perCall).toBeLessThan(50);
  });

  it("measures a warm call", () => {
    const t0 = performance.now();
    for (let i = 0; i < 100; i++) call(runtime, "echo", { text: "привет" });
    const perCall = (performance.now() - t0) / 100;
    console.log(`warm call: ${perCall.toFixed(3)} ms`);
    expect(perCall).toBeLessThan(50);
  });

  it("refuses bundle paths that escape the package directory", async () => {
    await expect(
      startCore({ version: "x", hash: "x", files: { "../evil.py": "" } }),
    ).rejects.toThrow(/invalid path/);
  });

  it("refuses a bundle that is not a core bundle", () => {
    expect(isCoreBundle({ version: "1", hash: "x", files: { "a.py": 5 } })).toBe(false);
  });
});

describe("start-up from a memory snapshot", () => {
  const b = bundle as CoreBundle;
  let snapshot: Uint8Array;

  it("a fresh start can make a snapshot with tilsim_core imported", async () => {
    const fresh = await startCore(b, { makeSnapshot: true });
    expect(fresh.timings.mode).toBe("fresh");
    expect(fresh.snapshot?.byteLength).toBeGreaterThan(1_000_000);
    snapshot = fresh.snapshot!;
    console.log(`fresh ${fresh.timings.totalMs.toFixed(0)} ms, snapshot ${(snapshot.byteLength / 1e6).toFixed(1)} MB`);
  });

  it("a start from the snapshot works and is much faster", async () => {
    const fresh = await startCore(b);
    const restored = await startCore(b, { snapshot });
    expect(restored.timings.mode).toBe("snapshot");
    console.log(`from snapshot ${restored.timings.totalMs.toFixed(0)} ms (fresh ${fresh.timings.totalMs.toFixed(0)} ms)`);
    expect(restored.timings.totalMs).toBeLessThan(fresh.timings.totalMs / 2);
    const reply = JSON.parse(restored.handle(JSON.stringify({ id: 1, op: "echo", args: { text: "Привет" } })));
    expect(reply).toEqual({ id: 1, ok: true, result: { text: "Привет" } });
    // The lexicon was loaded before the snapshot, so the first analysis needs no loading.
    const t = performance.now();
    const analysed = JSON.parse(restored.handle(JSON.stringify({ id: 2, op: "analyze", args: { word: "столом" } })));
    console.log(`first analyze after restore: ${(performance.now() - t).toFixed(1)} ms`);
    expect(analysed.result.status).toBe("ok");
  });

  it("a damaged snapshot falls back to a fresh start instead of failing", async () => {
    const broken = await startCore(b, { snapshot: new Uint8Array([1, 2, 3, 4]) });
    expect(broken.timings.mode).toBe("fresh");
    expect(broken.timings.snapshotError).toBeTruthy();
    expect(JSON.parse(broken.handle(JSON.stringify({ id: 1, op: "version" }))).ok).toBe(true);
  });

  it("the snapshot key changes with the core bundle", () => {
    expect(snapshotKey(b)).not.toBe(snapshotKey({ ...b, hash: "other" }));
  });
});
