#!/bin/sh
# Example read-only version check for command_check.
# Copy to a private path, replace the placeholder logic, and allowlist it in actions.yaml.
set -eu

SERVICE_NAME="${SERVICE_NAME:-example-service}"
CURRENT_VERSION="${CURRENT_VERSION:-1.0.0}"
LATEST_VERSION="${LATEST_VERSION:-1.1.0}"

cat <<REPORT
service: ${SERVICE_NAME}
current_version: ${CURRENT_VERSION}
latest_version: ${LATEST_VERSION}
release_notes: Placeholder release notes. Replace with real package or API lookup.
known_issues: No known critical issues in this example.
recommendation: Review the changelog before approving the upgrade.
REPORT
