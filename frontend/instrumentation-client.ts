import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENV ?? "development",
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0.01,
  replaysOnErrorSampleRate: 0.5,
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

// Required by @sentry/nextjs ≥ 9 to instrument client-side navigations.
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
