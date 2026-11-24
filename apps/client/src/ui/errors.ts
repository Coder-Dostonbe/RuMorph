import { ApiError } from "../api/http";
import { format, type Messages } from "../i18n";
import { useAdmin } from "../stores/admin";

/**
 * A message the user can read, in the interface language, for any error from the API.
 * Codes the app has no text for are shown only in the admin mode.
 */
export function describeError(error: unknown, m: Messages): string {
  const admin = useAdmin().unlocked;
  if (error instanceof ApiError) {
    switch (error.code) {
      case "network":
        return m.errors.network;
      case "invalid_credentials":
        return m.errors.invalidCredentials;
      case "email_taken":
        return m.errors.emailTaken;
      case "weak_password":
        return m.errors.weakPassword;
      case "invalid_email":
        return m.errors.invalidEmail;
      case "too_many_attempts":
        return m.errors.tooManyAttempts;
      case "registration_closed":
        return m.errors.registrationClosed;
      case "session_expired":
      case "unauthorized":
        return m.errors.sessionExpired;
      case "internal":
        return m.errors.server;
    }
    return admin ? format(m.errors.unknown, { error: `${error.code} (${error.status})` }) : m.errors.unknownUser;
  }
  return admin ? format(m.errors.unknown, { error: error instanceof Error ? error.message : String(error) }) : m.errors.unknownUser;
}
