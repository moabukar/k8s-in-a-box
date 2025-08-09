#!/usr/bin/env bash

set -euo pipefail

NS=kbox
SVC=app
DEPLOY=app

echo "[1/5] Namespace exists?"
kubectl get ns ${NS} >/dev/null

echo "[2/5] PVC Bound?"
kubectl -n ${NS} get pvc app-pvc -o jsonpath='{.status.phase}' | grep -q '^Bound$' || { echo "FAIL: PVC not Bound"; exit 1; }

echo "[3/5] Pods Ready?"
kubectl -n ${NS} wait --for=condition=ready pod -l app=${DEPLOY} --timeout=180s

echo "[4/5] Service has endpoints?"
EP_COUNT=$(kubectl -n ${NS} get endpoints ${SVC} -o jsonpath='{.subsets[0].addresses[*].ip}' 2>/dev/null | wc -w | tr -d ' ')
if [[ -z "${EP_COUNT}" || "${EP_COUNT}" -lt 1 ]]; then
  echo "FAIL: Service has no endpoints"
  exit 1
fi

echo "[5/5] In-cluster connectivity works?"
POD=$(kubectl -n ${NS} get pod -l run=net-debug -o jsonpath='{.items[0].metadata.name}')
kubectl -n ${NS} exec "${POD}" -- sh -c "wget -qO- ${SVC}.${NS}.svc.cluster.local:80/health || wget -qO- ${SVC}.${NS}.svc.cluster.local:80/"

echo "Verification passed."
