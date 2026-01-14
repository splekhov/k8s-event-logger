#!/usr/bin/env bash

set -euo pipefail

# Default parameters
KUBECONFIG_PATH="${1:-$HOME/.kube/config}"
NAMESPACE="${2:-ecare-ta}"

echo "Using kubeconfig: $KUBECONFIG_PATH"
echo "Using namespace:  $NAMESPACE"

# Ensure kubeconfig exists
if [ ! -f "$KUBECONFIG_PATH" ]; then
  echo "ERROR: kubeconfig not found at $KUBECONFIG_PATH"
  exit 1
fi

# Directory for backups
BACKUP_DIR="k8s-backup-${NAMESPACE}-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Backup directory: $BACKUP_DIR"

# List of resource types to back up
RESOURCE_TYPES=(
  pods
  deployments
  statefulsets
  daemonsets
  replicasets
  services
  ingresses
  configmaps
  secrets
  serviceaccounts
  roles
  rolebindings
  persistentvolumeclaims
  jobs
  cronjobs
  endpoints
  networkpolicies
)

# Loop through each resource type
for TYPE in "${RESOURCE_TYPES[@]}"; do
  echo "Processing resource type: $TYPE"

  # Get all object names of this type
  NAMES=$(kubectl --kubeconfig "$KUBECONFIG_PATH" -n "$NAMESPACE" get "$TYPE" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || true)

  # Skip if none exist
  if [ -z "$NAMES" ]; then
    continue
  fi

  # Backup each object
  for NAME in $NAMES; do
    FILE="${BACKUP_DIR}/${TYPE}-${NAME}-${NAMESPACE}.yaml"
    echo "  Backing up: $TYPE/$NAME → $FILE"

    kubectl --kubeconfig "$KUBECONFIG_PATH" -n "$NAMESPACE" \
      get "$TYPE" "$NAME" -o yaml > "$FILE"
  done
done

echo "Backup completed successfully."
echo "Files stored in: $BACKUP_DIR"

