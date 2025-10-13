# ------------------------------
# Etap budowy i uruchamiania
# ------------------------------
FROM python:3.10-slim

WORKDIR /app

# Skopiuj cały projekt
COPY . .

# Zainstaluj zależności (jeśli masz requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt || true

# 🔧 Kluczowe rozwiązanie — ustaw Python path
ENV PYTHONPATH=/app

# Domyślny punkt wejścia (można nadpisać w pipeline)
CMD ["python", "src/uruchom_pipeline.py"]
