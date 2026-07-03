# =============================================================================
# AI Archive Platform - Frontend Dockerfile
# =============================================================================
# Multi-stage build for Next.js with minimal production image.

# ---------------------------------------------------------------------------
# Stage 1: Base image with system dependencies
# ---------------------------------------------------------------------------
FROM node:20-alpine AS base

# Enable standalone output mode for optimized production builds
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

WORKDIR /app

# ---------------------------------------------------------------------------
# Stage 2: Install dependencies (cached layer)
# ---------------------------------------------------------------------------
FROM base AS deps

COPY frontend/package.json frontend/package-lock.json* ./

RUN npm ci --ignore-scripts && \
    npm cache clean --force

# ---------------------------------------------------------------------------
# Stage 3: Build application
# ---------------------------------------------------------------------------
FROM base AS builder

COPY --from=deps /app/node_modules ./node_modules

COPY frontend/ .

ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}

RUN npm run build

# ---------------------------------------------------------------------------
# Stage 4: Production image (standalone mode)
# ---------------------------------------------------------------------------
FROM node:20-alpine AS production

RUN apk add --no-cache curl

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

# Copy only what's needed for standalone output
COPY --from=builder /app/public ./public
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static

USER node

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
    CMD curl -f http://localhost:3000/ || exit 1

CMD ["node", "server.js"]

# ---------------------------------------------------------------------------
# Stage 5: Development image (hot reload)
# ---------------------------------------------------------------------------
FROM base AS development

COPY frontend/package.json frontend/package-lock.json* ./

RUN npm ci --ignore-scripts

COPY frontend/ .

EXPOSE 3000 9229

CMD ["npm", "run", "dev"]
