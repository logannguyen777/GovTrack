// This file is loaded by @sentry/nextjs for the Node.js server runtime.
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENV ?? "development",
  tracesSampleRate: 0.1,
  beforeSend(event) {
    if (event.user?.email) {
      event.user.email = "[REDACTED]";
    }
    if (event.user?.ip_address) {
      event.user.ip_address = "[REDACTED]";
    }
    return event;
  },
});
