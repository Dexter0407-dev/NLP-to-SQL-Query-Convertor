# Multi-stage build for lean image
FROM python:3.11-slim as builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY ./app ./app

# Ensure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Render assigns PORT dynamically
ENV PORT=8000

# Expose port
EXPOSE $PORT

# Run with uvicorn
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
