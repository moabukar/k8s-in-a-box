#!/usr/bin/env bash
set -euo pipefail
ns="${KUBECTL_NS:-kbox}"
echo "== kubectl (ns=${ns}) =="
kubectl -n "${ns}" "$@"
