# ---------- Build stage ----------
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies (cached layer)
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
ARG VITE_API_URL=
ENV VITE_API_URL=${VITE_API_URL}
# Optional: bake a bearer token into the bundle (only for browser-auth deployments).
# Leave unset to use unauthenticated requests (API_AUTH_REQUIRED=false) or proxy auth.
ARG VITE_API_AUTH_TOKEN=
ENV VITE_API_AUTH_TOKEN=${VITE_API_AUTH_TOKEN}
RUN npm run build

# ---------- Production stage ----------
FROM nginx:alpine AS production

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx config: serve SPA + proxy /api/* and /health /ready to FastAPI
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
