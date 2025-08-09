#!/usr/bin/env bash
set -euo pipefail

declare -a HINTS=(
  "Check labels & selectors between Deployment and Service."
  "Compare Service 'targetPort' with the container's actual listening port."
  "Readiness/liveness probes: path, port, initialDelaySeconds, scheme."
  "Describe the Pod and inspect Events for failing probes or mounts."
  "PVC pending? Verify storageClassName and capacity; check 'describe pvc'."
  "NetworkPolicy may be denying traffic. Is there a default-deny?"
  "Exec into busybox and curl the service DNS name. What error do you get?"
  "Service endpoints: 'kubectl get ep' — do they exist and match Pod labels?"
)

R=$(( RANDOM % ${#HINTS[@]} ))
echo "Hint: ${HINTS[$R]}"
