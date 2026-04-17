# ── Stage 1: deps ────────────────────────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --frozen-lockfile

# ── Stage 2: builder ─────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

ARG NEXT_PUBLIC_API_URL=http://localhost:8100
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8100

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}
# Disable Next.js telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm run build

# ── Stage 3: runtime ─────────────────────────────────────────────────────────
FROM node:20-alpine AS runtime

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3100

# Non-root user
RUN addgroup --gid 1001 nextjs && \
    adduser --uid 1001 --ingroup nextjs --disabled-password nextjs

WORKDIR /app

# Standalone output contains its own node_modules subset
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
# Static assets must be copied separately (Next.js docs requirement)
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static
# Public assets
COPY --from=builder --chown=nextjs:nextjs /app/public ./public

USER nextjs

EXPOSE 3100

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -qO- http://localhost:3100/api/health 2>/dev/null || \
        wget -qO- http://localhost:3100/ 2>/dev/null | grep -q "GovFlow" || exit 1

CMD ["node", "server.js"]
