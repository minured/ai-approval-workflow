# Action Runner

`command_check` and `queued_action` keep AI away from arbitrary shell execution.

- `command_check` runs a named read-only command from a private allowlist.
- `queued_action` writes an approved JSON request into a queue.
- `scripts/aaw_action_runner.py` is intended to run as a root-managed process and validates the action name again before executing a fixed command.

## Allowlist shape

```yaml
# Queue where approved JSON requests are written by the app.
queue_dir: /var/lib/ai-approval-workflow/actions

# Optional command used by the root runner to notify action results.
notify_command:
  - /usr/local/bin/send-notification

# Read-only checks used by workflow command_check steps.
commands:
  service_version_check:
    command: ["/usr/local/bin/service-version-check"]
    timeout_seconds: 180

# Approved actions used by workflow queued_action steps.
actions:
  service_bundle_upgrade:
    command: ["/usr/local/bin/service-bundle-upgrade"]
    timeout_seconds: 1800
```

Keep this file root-owned and outside git, for example `/etc/ai-approval-workflow/actions.yaml`.

## Runner command

```bash
/opt/ai-approval-workflow/.venv/bin/python \
  /opt/ai-approval-workflow/scripts/aaw_action_runner.py \
  --config /etc/ai-approval-workflow/actions.yaml
```

A timer can run the command periodically, or a file watcher can trigger it when new pending JSON files arrive.

## Script contract

Action scripts can read the approved request path from:

```text
AAW_ACTION_REQUEST
```

The request JSON contains `request_id`, `action`, `run_id`, `approval_id`, `workflow_id`, `payload`, and `created_at`.

## Safety rules

- Never let AI generate shell command strings.
- Keep action names stable and allowlisted.
- Put credentials in the host environment or a root-owned config file, not workflow YAML.
- Make read-only checks separate from mutating actions.
- Write action scripts to be idempotent when possible.
