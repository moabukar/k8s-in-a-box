#!/usr/bin/env bash

set -euo pipefail

KIND_CLUSTER_NAME=${KIND_CLUSTER_NAME:-kbox}
CMD=${1:-up}

if [[ "$CMD" == "up" ]]; then
  if kind get clusters | grep -q "^${KIND_CLUSTER_NAME}$"; then
    echo "kind cluster '${KIND_CLUSTER_NAME}' already exists."
    exit 0
  fi

  cat <<EOF | kind create cluster --name "${KIND_CLUSTER_NAME}" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
- role: worker
- role: worker
EOF

  kubectl wait --for=condition=Ready node --all --timeout=90s
  echo "Cluster '${KIND_CLUSTER_NAME}' is ready."
  exit 0
fi

if [[ "$CMD" == "down" ]]; then
  kind delete cluster --name "${KIND_CLUSTER_NAME}" || true
  exit 0
fi
