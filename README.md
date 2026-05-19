# ai-approval-workflow

[English](README.md) | [简体中文](README.zh-CN.md)

![ai-approval-workflow hero](docs/assets/hero.svg)

Open-source scheduled AI workflow runtime with mobile-first approvals.

`ai-approval-workflow` is designed for repetitive operational or personal tasks with this shape:

```text
regular check
  -> AI-readable result
  -> concise notification or approval request
  -> optional fixed action after approval
```

The project is intentionally **not** a chat bot and **not** a visual workflow builder. Natural-language task creation/editing/deletion is provided by a bundled Codex skill that writes reviewable YAML workflow files.

## Why this exists

Many automation systems fall into one of two extremes:

- cron jobs run silently with limited context;
- chat bots and agents require long conversations for simple decisions;
- direct AI command execution can create unsafe operational boundaries;
- dashboards require continuous human attention.

This project focuses on a narrower pattern: **scheduled AI summaries + mobile approval + fixed allowlisted actions**.

## What it can do

- Run scheduled AI tasks from YAML cron definitions.
- Fetch public pages or run named read-only checks.
- Summarize long output into short mobile-friendly messages.
- Create approval pages with simple buttons such as Upgrade / Skip.
- Queue approved actions for a root-side runner that validates names again.
- Provide a small admin page for viewing and soft-deleting configured tasks.
- Convert natural-language task requests into reviewed workflow YAML through the bundled skill.

## How it works

![Architecture diagram](docs/assets/architecture.svg)

The public repository contains generic framework code. Deployment-specific secrets, production workflows, action allowlists, scripts, and databases stay outside git.

![Workflow lifecycle](docs/assets/workflow-lifecycle.svg)

## Product surfaces

Mobile approval:

![Mobile approval mockup](docs/assets/mobile-approval-mock.svg)

Admin page:

![Admin dashboard mockup](docs/assets/admin-dashboard-mock.svg)

## Use cases

- **GitHub Trending digest:** summarize notable repositories on a schedule.
- **Service upgrade review:** check versions and known issues before asking whether to upgrade.
- **Certificate/domain expiry watcher:** notify before important resources expire.
- **Backup health report:** turn raw backup logs into a weekly risk summary.
- **CI failure triage:** group failures and summarize likely causes.
- **Billing/subscription drift:** summarize unusual spend or upcoming renewals.
- **Personal convenience tasks:** price changes, travel disruption summaries, policy updates, and home server health.

See [Use Cases](docs/use-cases.md) for concrete examples, including a coordinated multi-component service upgrade pattern.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
pytest -q
uvicorn ai_approval_workflow.main:app --host 127.0.0.1 --port 8787
```

Open:

- `http://127.0.0.1:8787/healthz` for health checks;
- `http://127.0.0.1:8787/admin` for viewing and soft-deleting workflows.

## Workflow files

Workflow YAML files live in `AAW_WORKFLOWS_DIR`. Validate them before restart:

```bash
.venv/bin/python scripts/validate_workflows.py ./examples
```

Common MVP step types:

- `http_fetch`: GET a public URL and store response text for AI;
- `ai_summary`: summarize the latest task/fetch result;
- `notify`: send a notification through the configured webhook;
- `approval`: create a mobile approval page with simple choices;
- `command_check`: run a named read-only command from deployment-managed allowlist config;
- `queued_action`: enqueue an approved named action for a root-side runner;
- `demo_summary` / `demo_action`: safe local demo steps.

Examples:

- `examples/github-trending-daily.yaml`: notification-only GitHub Trending digest;
- `examples/service-upgrade-watch.yaml`: generic service upgrade check with approval and queued action.

## Natural-language workflow management

The bundled Codex skill lives in:

```text
skills/ai-approval-workflow/SKILL.md
```

Install or copy it into `$CODEX_HOME/skills/ai-approval-workflow/`. Example requests:

- `Send a GitHub Trending summary every morning at 9, no approval required.`
- `Check a service version daily; if an upgrade looks worthwhile, ask for mobile approval with Upgrade / Skip buttons.`
- `Soft-delete the weekly backup report workflow.`

The skill keeps hostnames, tokens, scripts, and production workflow files out of the public repository.

## Deployment-specific configuration

This repository is suitable for public release as a framework. Deployment-specific data should stay outside git:

- `.env` and any `.env.*` files;
- production workflow files under `/etc/ai-approval-workflow/workflows` or another operator-managed directory;
- action allowlists such as `/etc/ai-approval-workflow/actions.yaml`;
- root-owned scripts used by `command_check` or `queued_action`;
- SQLite databases and action queue files.

See [Deployment-Specific Configuration](docs/private-overlay.md) and [Publishing Checklist](docs/publishing-checklist.md) before publishing a fork or derivative.

## Documentation

- [Use Cases](docs/use-cases.md)
- [Design](docs/design.md)
- [Security Model](docs/security.md)
- [Deployment](docs/deployment.md)
- [Action Runner](docs/action-runner.md)
- [Deployment-Specific Configuration](docs/private-overlay.md)
- [Publishing Checklist](docs/publishing-checklist.md)

## License

MIT.
