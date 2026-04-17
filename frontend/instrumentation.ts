export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { init } = await import("@sentry/nextjs");
    init({
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
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    const { init } = await import("@sentry/nextjs");
    init({
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
  }
}

// Capture errors thrown during RSC rendering (Next.js ≥ 15).
export const onRequestError = async (
  err: unknown,
  request: { path: string; method: string; headers: Record<string, string | string[] | undefined> },
  errorContext: { routerKind: string; routePath: string; routeType: string },
) => {
  const { captureRequestError } = await import("@sentry/nextjs");
  captureRequestError(err, request, errorContext);
};
