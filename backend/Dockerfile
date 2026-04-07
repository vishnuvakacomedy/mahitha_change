# ── Stage 1: Build React frontend ───────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /frontend
COPY ../frontend/package*.json ./
RUN npm install
COPY ../frontend/ ./
RUN npm run build

# ── Stage 2: Python backend + static files ───────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy built React app into backend/static
COPY --from=frontend-builder /frontend/dist ./static

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
