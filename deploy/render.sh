#!/usr/bin/env bash
set -euo pipefail

NS=pid-sim-dev
IMAGE="${IMAGE:-registry.example.com/pid-sim:dev}"
CM_ENV="deploy/configmap.env"

# 1) Namespace
kubectl apply -f deploy/namespace.yaml

# 2) Zbuduj ConfigMap z pliku ENV (klucze=wartosci)
#    Tworzymy tymczasowy manifest configmap z data:<klucz: "wartosc">
echo "apiVersion: v1
kind: ConfigMap
metadata:
  name: pid-sim-config
  namespace: ${NS}
data:" > deploy/configmap.yaml

while IFS='=' read -r k v; do
  [[ -z "$k" || "$k" =~ ^# ]] && continue
  # escapowanie cudzyslowow
  v_esc=$(printf '%s' "$v" | sed 's/"/\\"/g')
  echo "  ${k}: \"${v_esc}\"" >> deploy/configmap.yaml
done < "$CM_ENV"

kubectl apply -f deploy/configmap.yaml

# 3) Render job.yaml z podstawieniem obrazu
export IMAGE
envsubst < deploy/job.yaml.tpl > deploy/job.yaml
kubectl apply -f deploy/job.yaml

# 4) Czekaj na zakonczenie Job
kubectl -n "${NS}" wait --for=condition=complete job/pid-sim-validate --timeout=10m || {
  echo "Job failed or timed out"; kubectl -n "${NS}" logs job/pid-sim-validate || true; exit 1; }

# 5) Pobierz nazwe poda i skopiuj artefakty
POD=$(kubectl -n "${NS}" get pods -l job-name=pid-sim-validate -o jsonpath='{.items[0].metadata.name}')
mkdir -p .out
kubectl -n "${NS}" cp "${POD}:/out" ".out"
echo "Artefakty w .out/"
