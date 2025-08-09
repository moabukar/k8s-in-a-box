#!/usr/bin/env bash

set -euo pipefail

KIND_CLUSTER_NAME=${KIND_CLUSTER_NAME:-kbox}
CMD=${1:-up}

if [[ "$CMD" == "up" ]]; then
  if kind get clusters | grep -q "^${KIND_CLUSTER_NAME}$"; then
    echo "kind cluster '${KIND_CLUSTER_NAME}' already exists."
  else
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
  fi

# Ensure local-path SC exists and is the ONLY default
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/master/deploy/local-path-storage.yaml >/dev/null
# remove default annotation from any existing SCs
for sc in $(kubectl get sc -o name | sed 's/storageclass.storage.k8s.io\///'); do
  kubectl annotate sc "$sc" storageclass.kubernetes.io/is-default-class- >/dev/null 2>&1 || true
done
# set local-path as default
kubectl annotate sc local-path storageclass.kubernetes.io/is-default-class=true --overwrite >/dev/null

fi

if [[ "$CMD" == "down" ]]; then
  kind delete cluster --name "${KIND_CLUSTER_NAME}" || true
  exit 0
fi
