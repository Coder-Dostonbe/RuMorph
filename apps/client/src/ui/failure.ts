// Error texts. Technical details (Python errors, codes) are shown only in the admin mode;
// an ordinary user gets a plain sentence in the interface language.
import { CoreError } from "../core/client";
import { format, type Messages } from "../i18n";
import { useAdmin } from "../stores/admin";

export function errorDetail(e: unknown): string {
  return e instanceof CoreError ? `${e.code}: ${e.message}` : e instanceof Error ? e.message : String(e);
}

/** A failed call to the grammar module. */
export function callFailed(m: Messages, e: unknown): string {
  return useAdmin().unlocked ? format(m.analyze.callFailed, { error: errorDetail(e) }) : m.analyze.callFailedUser;
}

/** The grammar module did not start (detail: useCore().error). */
export function coreFailed(m: Messages, detail: string): string {
  return useAdmin().unlocked ? format(m.analyze.coreFailed, { error: detail }) : m.analyze.coreFailedUser;
}
