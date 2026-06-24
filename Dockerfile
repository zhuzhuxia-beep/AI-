# ====== Stage 1: Build frontend ======
FROM node:20-slim AS frontend-builder

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npx vite build --outDir /static --emptyOutDir

# ====== Stage 2: Python runtime with FFmpeg ======
FROM python:3.11-slim

# Install FFmpeg (full version from Debian repos) and system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy built frontend static files
COPY --from=frontend-builder /static ./static/

# Create directories
RUN mkdir -p outputs uploads

# Expose port
EXPOSE 8000

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
