# Multi-stage for smaller final image
FROM python:3.12-slim AS base

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
ENV PYTHONUNBUFFERED=1
ENV OUT_DIR=/out

# Default entrypoint runs the scenario
ENTRYPOINT ["python", "-m", "src.run_scenario"]
