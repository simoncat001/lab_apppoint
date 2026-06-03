# Single-stage SPA build. The staff (security-server) frontend was merged
# into ui/src/security/ in Phase 6, so one `vite build` now produces a
# single dist serving both the nemo SPA (at /) and the staff SPA (at
# /security/) — routing is handled by vue-router on the client side.
ARG NODE_BASE_IMAGE=node:20-alpine
ARG NGINX_BASE_IMAGE=nginx:1.27-alpine

FROM ${NODE_BASE_IMAGE} AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM ${NGINX_BASE_IMAGE}
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
