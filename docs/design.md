# Design

`ai-approval-workflow` is a lightweight runtime for scheduled AI workflows that need notifications and, when requested, mobile approval before executing allowlisted actions.

## Core flows

Notification-only task:

```text
schedule trigger
  -> collect context, for example http_fetch
  -> AI summary
  -> notification webhook
  -> audit event
```

Approval-gated task:

```text
schedule trigger
  -> read-only check or public fetch
  -> AI summary / recommendation
  -> pending approval
  -> mobile approval page
  -> allowlisted action or skip
  -> audit event and notification
```

## Modules

- `config`: environment settings and YAML workflow loading.
- `storage`: SQLite persistence for runs, approvals, and audit events.
- `workflow`: step execution and decision continuation.
- `approvals`: secure approval IDs, token hashes, and decisions.
- `notify`: generic outbound webhook notification.
- `admin`: workflow inventory and soft-delete helpers.
- `main`: FastAPI approval page, admin page, and APIs.
- `scheduler`: APScheduler cron registration.
- `actions`: allowlisted read-only commands and queued action requests.

## Workflow steps

The MVP supports generic composition without hard-coding a specific business task:

- `http_fetch`: fetch public HTTP content for AI processing.
- `ai_summary`: summarize task or fetch output with an optional prompt.
- `notify`: send the latest summary/content to the configured notification webhook.
- `approval`: ask for simple mobile choices such as Execute / Skip / Snooze.
- `command_check`: run a named read-only command from deployment-managed allowlist config.
- `queued_action`: enqueue an approved named action for a root-side runner.
- `demo_summary` and `demo_action`: safe sample steps.

## Admin UI

`/admin` is intentionally limited to viewing and deleting workflows. Deletion is a soft delete that moves YAML files into `.deleted/` and reloads the scheduler.

The admin page does not parse natural language and does not create or edit workflows. Those operations are handled outside the web UI by the bundled skill or another operator-reviewed workflow authoring process.

## Approval UI

The MVP uses a mobile web approval page instead of relying on provider-specific native card buttons. This keeps the approval flow compatible with WeChat, WeCom, and generic notification adapters.

## Privileged actions

Production actions use a two-part model:

- `command_check` runs a named read-only command from a deployment-managed allowlist.
- `queued_action` writes an approved JSON request into an action queue.

A root-side runner validates queued action names against deployment-managed config before executing fixed scripts. AI summarizes and recommends, but it never creates shell commands.
