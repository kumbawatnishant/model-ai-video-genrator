## Dockerfile for deploying the Node/Express backend to Render (or any Docker-friendly host)
FROM node:18-bullseye-slim

# Install ffmpeg and other system deps
RUN apt-get update \
  && apt-get install -y --no-install-recommends ffmpeg ca-certificates build-essential \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# Copy package files and install deps
COPY scaffold/backend/package*.json ./
RUN npm ci --only=production

# Copy backend source
COPY scaffold/backend/ .

# Expose port (Render will use PORT env var)
ENV PORT=4000
EXPOSE 4000

# Default startup (Render will set NODE_ENV=production in its dashboard)
CMD ["node", "index.js"]
