// Runs tilsim_api.passwords inside Pyodide with the Web Crypto derive (as in the
// Worker) and checks it against hashlib-compatible known values.
// Run from the repository root: node --test apps/api/tests/js/
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { loadPyodide } from "pyodide";

const src = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "src", "tilsim_api");
const py = await loadPyodide();
py.FS.mkdirTree("/api/tilsim_api");
for (const name of readdirSync(src).filter((f) => f.endsWith(".py"))) {
  py.FS.writeFile(`/api/tilsim_api/${name}`, readFileSync(join(src, name), "utf8"));
}
py.runPython("import sys; sys.path.insert(0, '/api')");

test("hashlib has no pbkdf2_hmac under Pyodide (why webcrypto.py exists)", () => {
  assert.equal(py.runPython("import hashlib; hasattr(hashlib, 'pbkdf2_hmac')"), false);
});

test("Web Crypto derive matches the PBKDF2 test vector", async () => {
  const hex = await py.runPythonAsync(`
from tilsim_api import webcrypto
(await webcrypto.derive(b"password", b"salt", 1)).hex()`);
  assert.equal(hex, "120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b");
});

test("hash and verify round-trip at the production iteration count", async () => {
  const result = await py.runPythonAsync(`
from tilsim_api import passwords, webcrypto
import time
t = time.perf_counter()
stored = await passwords.hash_password("juda-maxfiy-parol", passwords.DEFAULT_ITERATIONS, webcrypto.derive)
ms = (time.perf_counter() - t) * 1000
ok = await passwords.verify_password("juda-maxfiy-parol", stored, webcrypto.derive)
bad = await passwords.verify_password("noto'g'ri", stored, webcrypto.derive)
[stored.split("$")[1], ok, bad, round(ms)]`);
  const [iterations, ok, bad, ms] = result.toJs();
  console.log(`Web Crypto PBKDF2 ${iterations} iterations: ${ms} ms`);
  assert.equal(iterations, "100000");
  assert.equal(ok, true);
  assert.equal(bad, false);
});

test("a hash made with hashlib verifies with Web Crypto", async () => {
  // pbkdf2_sha256$1000$ of "parol-parol" with salt b"0123456789abcdef", computed by CPython hashlib.
  const stored = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "hashlib_vector.txt"), "utf8").trim();
  const ok = await py.runPythonAsync(`
from tilsim_api import passwords, webcrypto
await passwords.verify_password("parol-parol", ${JSON.stringify(stored)}, webcrypto.derive)`);
  assert.equal(ok, true);
});
