import { ApiError } from "../api/http";
import { format, type Messages } from "../i18n";

/** A message the user can read, in the interface language, for any error from the API. */
export function describeError(error: unknown, m: Messages): string {
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
    return format(m.errors.unknown, { error: `${error.code} (${error.status})` });
  }
  return format(m.errors.unknown, { error: error instanceof Error ? error.message : String(error) });
}
