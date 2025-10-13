# ------------------------------
# Etap budowy i uruchamiania
# ------------------------------
FROM python:3.10-slim

WORKDIR /app

COPY . .

ENV PYTHONPATH=/app

RUN pip install --no-cache-dir \
    numpy \
    matplotlib \
    pyyaml \
    scipy

CMD ["python", "src/uruchom_pipeline.py"]
