# ai-approval-workflow

Open-source scheduled AI workflow runtime with mobile-first approvals.

It is built for two core interactions:

1. **scheduled AI tasks**: run on cron, collect context, summarize with AI, and notify you;
2. **human approval from phone**: send a short approval link with simple choices such as Execute / Skip / Snooze before an allowlisted action runs.

The project is intentionally **not** a chat bot and **not** a visual workflow builder. Natural-language task creation/editing/deletion is handled by the bundled Codex skill, which writes reviewable YAML workflow files.

## What is included

- FastAPI runtime for health checks, approval pages, admin pages, and APIs.
- APScheduler cron registration from YAML workflow files.
- Generic webhook notifications for WeChat, WeCom, Slack, Discord, or any adapter service.
- Mobile approval pages with stable decision values and custom button labels.
- Safe action boundary: workflows reference named commands/actions, while fixed commands live in private allowlist config.
- Codex skill for natural-language workflow CRUD and conservative framework capability upgrades.

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
- `command_check`: run a named read-only command from private allowlist config;
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

Install or copy it into `$CODEX_HOME/skills/ai-approval-workflow/`, then use prompts such as:

- “每天早上 9 点给我发 GitHub Trending 总结，不需要审批”
- “每天检查某个服务版本，如果值得升级就发手机审批，按钮是升级/跳过”
- “删除某个定时任务”

The skill should keep private hostnames, tokens, scripts, and production workflow files outside this public repository.

## Private overlay

This repository is safe to publish when used as a framework. Your deployment-specific data should stay outside git:

- `.env` and any `.env.*` files;
- production workflow files under `/etc/ai-approval-workflow/workflows` or another private directory;
- action allowlists such as `/etc/ai-approval-workflow/actions.yaml`;
- root-owned scripts used by `command_check` or `queued_action`;
- SQLite databases and action queue files.

See [Private Overlay](docs/private-overlay.md) and [Publishing Checklist](docs/publishing-checklist.md) before publishing.

## Documentation

- [Design](docs/design.md)
- [Security Model](docs/security.md)
- [Deployment](docs/deployment.md)
- [Action Runner](docs/action-runner.md)
- [Private Overlay](docs/private-overlay.md)
- [Publishing Checklist](docs/publishing-checklist.md)

## License

MIT.
