// Shapes of the API's JSON. They mirror apps/api/src/tilsim_api (auth.py, app.py);
// the API tests check the server side of every field listed here.

export interface Health {
  status: "ok";
  service: string;
  version: string;
  database: "ok" | "unavailable";
}

export interface User {
  id: string;
  email: string;
  display_name: string | null;
  role: "user" | "admin";
  created_at: string;
}

export interface DeviceInfo {
  id: string;
  name: string;
  platform: "windows" | "android" | "browser";
}

export interface TokenPair {
  access_token: string;
  access_expires_in: number;
  refresh_token: string;
  refresh_expires_in: number;
  token_type: "Bearer";
}

export interface AuthResponse extends TokenPair {
  user: User;
}

export interface AccountDevice {
  id: string;
  name: string;
  platform: DeviceInfo["platform"];
  created_at: string;
  last_seen_at: string;
  last_sync_at: string | null;
  signed_in: boolean;
  current: boolean;
}

/** GET /v1/account (sync.py, account). Counts are of live rows on the server. */
export interface AccountOverview {
  user: User;
  progress: {
    words: number;
    known_words: number;
    cards: number;
    reviews: number;
    texts: number;
    readings: number;
    tests: number;
    last_change_at: string | null;
  };
  devices: AccountDevice[];
}
