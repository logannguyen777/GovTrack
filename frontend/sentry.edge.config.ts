// This file is loaded by @sentry/nextjs for the Edge runtime (middleware).
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENV ?? "development",
  tracesSampleRate: 0.05,
  beforeSend(event) {
    if (event.user?.email) {
      event.user.email = "[REDACTED]";
    }
    return event;
  },
});
