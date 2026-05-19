#!/bin/sh
# Example mutating action for queued_action.
# Copy to a deployment-managed root-owned path and replace placeholders with deployment commands.
set -eu

REQUEST_PATH="${AAW_ACTION_REQUEST:-}"
if [ -z "${REQUEST_PATH}" ] || [ ! -f "${REQUEST_PATH}" ]; then
  echo "AAW_ACTION_REQUEST must point to an approved request JSON" >&2
  exit 1
fi

echo "Would upgrade example-service using approved request: ${REQUEST_PATH}"
echo "Replace this script with backup, upgrade, health check, and rollback logic."
