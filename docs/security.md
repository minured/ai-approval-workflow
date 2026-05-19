# Security Model

## Secrets

Do not commit real secrets. Keep these values in `.env` or deployment-managed environment files:

- AI API keys;
- notification webhook secrets;
- bearer tokens and cookies;
- production public URLs with embedded secrets;
- SSH keys;
- host-specific action credentials.

Workflow YAML should contain public URLs, prompts, schedules, and channel names only.

## Approval tokens

Approval links include a random URL token. Only the SHA-256 hash is stored in SQLite.

## AI execution boundary

AI may summarize, classify risk, and recommend. AI must not generate arbitrary shell commands for direct execution.

## Actions

Actions must be allowlisted by root-owned code or configuration. The public repo ships only safe demos and generic runner code.

## HTTP fetches

`http_fetch` currently supports GET-only requests. Do not put credentials in workflow headers or URLs.

## Admin routes

Production should protect `/admin` and `/api/admin/*` with SSO, VPN, or another trusted access layer. Public approval routes remain token-based.

## Audit events

The runtime records approval creation, decisions, workflow completion, and failures in SQLite audit events.

## Privileged action runner

The app must not run arbitrary shell commands. Production actions are split into:

- named read-only commands, configured in a deployment-managed allowlist;
- queued action JSON files, consumed by a root-owned runner;
- fixed scripts such as `service-bundle-upgrade`.

The runner validates action names before execution and moves requests to `done/` or `failed/`. Secrets stay in host configuration and are never stored in workflow YAML.
