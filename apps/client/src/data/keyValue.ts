// Small key-value storage for settings: the SQLite `settings` table in the app,
// localStorage in a plain browser (development only).
import { database } from "./db";

export interface KeyValueStore {
  readonly kind: "sqlite" | "browser";
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<void>;
}

class SqliteStore implements KeyValueStore {
  readonly kind = "sqlite" as const;
  constructor(private db: NonNullable<ReturnType<typeof database>>) {}

  async get(key: string): Promise<string | null> {
    const rows = await (await this.db).select<{ value: string }[]>("SELECT value FROM settings WHERE key = $1", [key]);
    return rows[0]?.value ?? null;
  }

  async set(key: string, value: string): Promise<void> {
    await (await this.db).execute(
      `INSERT INTO settings (key, value, updated_at) VALUES ($1, $2, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
       ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at`,
      [key, value],
    );
  }
}

class BrowserStore implements KeyValueStore {
  readonly kind = "browser" as const;
  private prefix = "tilsim.";

  async get(key: string): Promise<string | null> {
    try {
      return localStorage.getItem(this.prefix + key);
    } catch {
      return null;
    }
  }

  async set(key: string, value: string): Promise<void> {
    try {
      localStorage.setItem(this.prefix + key, value);
    } catch {
      // Storage can be unavailable (private mode); settings then last for this session only.
    }
  }
}

const db = database();
export const keyValue: KeyValueStore = db ? new SqliteStore(db) : new BrowserStore();
