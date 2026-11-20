// Runs tilsim_core inside real Pyodide (under Node), the same runtime the app uses,
// and records how long start-up takes on this machine.
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { BridgeReply, CoreVersion } from "../src/core/protocol";
import { isCoreBundle, startCore, type CoreRuntime } from "../src/core/runtime";

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
});
