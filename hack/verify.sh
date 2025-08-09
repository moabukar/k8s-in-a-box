#!/usr/bin/env bash
set -euo pipefail

NS=kbox
SVC=app
DEPLOY=app

fail(){ echo "FAIL: $*"; exit 1; }

echo "[1/5] Namespace exists?"
kubectl get ns ${NS} >/dev/null || fail "namespace ${NS} missing"

echo "[2/5] PVC Bound?"
kubectl -n ${NS} get pvc app-pvc -o jsonpath='{.status.phase}' | grep -q '^Bound$' || fail "PVC not Bound"

echo "[3/5] Pods Ready?"
kubectl -n ${NS} wait --for=condition=ready pod -l app=${DEPLOY} --timeout=180s >/dev/null || fail "pods not Ready"

echo "[4/5] Service has endpoints?"
EP_JSON=$(kubectl -n ${NS} get endpoints ${SVC} -o json 2>/dev/null || true)
[[ -n "$EP_JSON" ]] || fail "no endpoints object"
EP_COUNT=$(echo "$EP_JSON" | jq -r '[.subsets[]?.addresses[]?] | length' 2>/dev/null || echo 0)
[[ "$EP_COUNT" -ge 1 ]] || fail "Service has no endpoints"

echo "[5/5] In-cluster connectivity works?"
POD=$(kubectl -n ${NS} get pod -l run=net-debug -o jsonpath='{.items[0].metadata.name}')
# Try /health then / as fallback, with explicit scheme
set +e
kubectl -n ${NS} exec "${POD}" -- sh -c "wget -qO- http://${SVC}.${NS}.svc.cluster.local:80/health || wget -qO- http://${SVC}.${NS}.svc.cluster.local:80/" >/dev/null
RC=$?
set -e
[[ $RC -eq 0 ]] || fail "HTTP fetch failed (check Service targetPort, probes, or NetworkPolicy)"

echo "Verification passed."
