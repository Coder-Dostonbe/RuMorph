// Keeps one Pyodide memory snapshot in IndexedDB (the webview's own storage, kept
// across app starts on Windows and Android). Only the newest is kept: a new app
// version or tilsim_core bundle gets a new key and replaces the old one.
// Every function swallows storage errors and reports them as "no snapshot":
// the snapshot only speeds start-up up, it is never required.

const DB_NAME = "tilsim-core";
const STORE = "snapshots";
const ENTRY = "current";

interface Entry {
  key: string;
  bytes: Uint8Array;
  savedAt: string;
}

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function run<T>(mode: IDBTransactionMode, body: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return open().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const tx = db.transaction(STORE, mode);
        const request = body(tx.objectStore(STORE));
        tx.oncomplete = () => {
          db.close();
          resolve(request.result);
        };
        tx.onerror = tx.onabort = () => {
          db.close();
          reject(tx.error ?? request.error);
        };
      }),
  );
}

export async function loadSnapshot(key: string): Promise<Uint8Array | null> {
  if (typeof indexedDB === "undefined") return null;
  try {
    const entry = await run<Entry | undefined>("readonly", (s) => s.get(ENTRY) as IDBRequest<Entry | undefined>);
    return entry && entry.key === key && entry.bytes instanceof Uint8Array ? entry.bytes : null;
  } catch {
    return null;
  }
}

export async function saveSnapshot(key: string, bytes: Uint8Array): Promise<boolean> {
  if (typeof indexedDB === "undefined") return false;
  try {
    const entry: Entry = { key, bytes, savedAt: new Date().toISOString() };
    await run("readwrite", (s) => s.put(entry, ENTRY));
    return true;
  } catch {
    return false;
  }
}

export async function deleteSnapshot(): Promise<void> {
  if (typeof indexedDB === "undefined") return;
  try {
    await run("readwrite", (s) => s.delete(ENTRY));
  } catch {
    // Nothing to do: the next start simply makes a new one.
  }
}
