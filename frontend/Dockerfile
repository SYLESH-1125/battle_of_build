FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --legacy-peer-deps
COPY frontend/ ./
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/ ./
ENV PORT 3000
EXPOSE 3000
CMD ["npm", "start"]
