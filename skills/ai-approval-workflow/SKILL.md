---
name: ai-approval-workflow
description: Use when creating, editing, deleting, validating, or deploying ai-approval-workflow YAML tasks, including scheduled AI notifications, mobile approvals, approved actions, or requests that may require upgrading the workflow DSL.
---

# ai-approval-workflow Skill

Manage scheduled AI workflows for `ai-approval-workflow`. The runtime executes scheduled tasks, sends notifications, and optionally creates simple mobile approval choices before allowlisted actions run.

## Guardrails

- Before creating, editing, deleting, restarting, deploying, or upgrading framework capability, show the intended changes and request operator confirmation unless the exact change has already been approved.
- Never print, commit, or write secrets into YAML. API keys, webhook URLs, bearer tokens, cookies, SSH credentials, and internal base URLs belong in `.env` or deployment-managed config.
- Prefer soft delete: move YAML into `.deleted/` instead of permanent removal.
- Admin web UI only views/deletes tasks; natural-language CRUD and capability planning are handled by this skill or another reviewed authoring process.
- If timezone is ambiguous and timing matters, ask one short clarification. Otherwise follow the existing workflow timezone; for Chinese “早上/晚上” reminders, default to `Asia/Shanghai` unless the deployment has another documented default.
- Respect the deployment message budget: `AAW_MESSAGE_MAX_CHARS` limits AI-generated notification/approval summaries. Default to 800 characters when unknown; `0` disables the limit.

## Path conventions

```text
Project root: current ai-approval-workflow checkout
Runtime env: $AAW_ENV_FILE or /etc/ai-approval-workflow/.env
Runtime workflows: $AAW_WORKFLOWS_DIR or /etc/ai-approval-workflow/workflows
Runtime DB: $AAW_DATABASE_PATH or /var/lib/ai-approval-workflow/ai-approval-workflow.db
Action allowlist: $AAW_ACTIONS_CONFIG_PATH or /etc/ai-approval-workflow/actions.yaml
```

Treat these as conventions. Inspect local files and environment before changing a deployment.

## Message length budget

- For any workflow that sends `ai_summary` through `notify` or `approval`, write prompts that produce a concise final message within `AAW_MESSAGE_MAX_CHARS`.
- Do not ask for long digests, raw excerpts, or multi-section reports unless the operator first raises the message budget.
- The runtime appends the hard output limit to AI requests and may clamp only as a last resort; do not rely on truncation as the primary behavior.

## First classify the request

| Classification | Action |
| --- | --- |
| Existing DSL supports it | Create/edit/delete workflow YAML only. |
| Existing steps can be combined | Compose YAML; do not change code. |
| Missing reusable primitive | Propose a small framework capability upgrade first. |
| Needs deployment-specific action | Keep core generic; add operator-managed allowlisted script/config. |
| Too bespoke or unsafe | Do not add to core; explain why and propose a safer adapter. |

If capability is missing, follow [Capability Upgrade Policy](references/capability-upgrade-policy.md). For common reusable recipes, see [Workflow Patterns](references/workflow-patterns.md).

## Supported workflow steps

- `http_fetch`: GET a public URL, storing response text for AI.
- `ai_summary`: summarize fetched/task text with an optional `prompt`.
- `notify`: send the latest AI summary or configured content to the notification webhook.
- `approval`: send a mobile approval page with Execute / Skip / Snooze or custom labels like 升级 / 不升级.
- `command_check`: run a root-allowlisted read-only command such as `service_version_check`.
- `queued_action`: enqueue an approved root-side action such as `service_bundle_upgrade`.
- `demo_summary`, `demo_action`: safe demo steps only.

## Workflow YAML shape

Use lowercase kebab-case ids. Keep workflow files root-level in the workflows directory.

```yaml
id: github-trending-daily
enabled: true
trigger:
  type: schedule
  cron: "0 9 * * *"
  timezone: Asia/Shanghai
steps:
  - id: fetch
    type: http_fetch
    url: "https://github.com/trending?since=daily"
  - id: summarize
    type: ai_summary
    prompt: "请用中文总结重点，控制在 8 条以内。"
  - id: notify
    type: notify
    title: "GitHub Trending Daily"
notify:
  channel: ops-default
```

## CRUD procedure

1. Inspect current workflows and runtime settings:

   ```bash
   pwd
   grep -E '^AAW_' .env 2>/dev/null || true
   .venv/bin/python scripts/validate_workflows.py "${AAW_WORKFLOWS_DIR:-./examples}"
   ls -la "${AAW_WORKFLOWS_DIR:-./examples}"
   ```

2. Convert the request into either:
   - a YAML-only change; or
   - a capability-upgrade proposal with generic core change + deployment-specific adapter split.

3. Show the diff or planned move and request confirmation.

4. After confirmation, write the change and validate:

   ```bash
   .venv/bin/python scripts/validate_workflows.py "${AAW_WORKFLOWS_DIR:-./examples}"
   ```

5. If this is a deployment checkout, reload the service using the deployment's documented command, then verify health:

   ```bash
   systemctl restart ai-approval-workflow.service
   systemctl is-active ai-approval-workflow.service
   curl -fsS https://approval.example.com/healthz
   ```

6. If a status notification is requested, use the deployment's notification helper or webhook without exposing secret paths or tokens.

## Production action notes

For privileged actions, do not put commands in workflow YAML. Use `command_check` and `queued_action` names allowlisted in `AAW_ACTIONS_CONFIG_PATH`. The root action runner validates action names again before executing fixed scripts.

## Natural-language mapping tips

- “每天早上 9 点” -> cron `0 9 * * *` plus selected timezone.
- “只通知 / 不需要审批” -> use `notify` and no `approval`.
- “确认后再执行” -> include `approval`; only use allowlisted actions.
- “升级/不升级按钮” -> approval choices with values `approve` / `reject` and labels `升级` / `不升级`.
- “简短发我 / 发消息给我” -> keep the AI summary within `AAW_MESSAGE_MAX_CHARS` (usually 800 characters).
- “删除任务” -> soft delete YAML and restart service if needed.
