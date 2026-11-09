FROM node:22-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package*.json ./
RUN npm install
COPY . .
# Rewrites are built with this URL. Use the same backend service name at runtime.
ENV API_INTERNAL_URL=http://api:8000
RUN npm run build
FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 API_INTERNAL_URL=http://api:8000
COPY --from=build --chown=node:node /app ./
USER node
EXPOSE 3000
CMD ["node","node_modules/next/dist/bin/next","start","--hostname","0.0.0.0","--port","3000"]
