# Deployment

This document describes a generic production deployment. Replace domains and paths with your own private values, and keep all secrets outside git.

## Recommended paths

```text
/opt/ai-approval-workflow                    # application checkout
/etc/ai-approval-workflow/.env               # private environment file
/etc/ai-approval-workflow/workflows          # private workflow YAML directory
/etc/ai-approval-workflow/actions.yaml       # private command/action allowlist
/var/lib/ai-approval-workflow                # SQLite database and action queues
```

These are conventional examples, not requirements.

## Environment file

```dotenv
# Runtime mode and bind address. Keep the app bound to localhost behind a reverse proxy.
AAW_APP_ENV=production
AAW_BIND_HOST=127.0.0.1
AAW_BIND_PORT=8787

# Public base URL used when generating mobile approval links.
AAW_PUBLIC_BASE_URL=https://approval.example.com

# Private runtime data locations.
AAW_DATABASE_PATH=/var/lib/ai-approval-workflow/ai-approval-workflow.db
AAW_WORKFLOWS_DIR=/etc/ai-approval-workflow/workflows
AAW_SCHEDULER_ENABLED=true

# Optional OpenAI-compatible AI endpoint. Keep API keys private.
AAW_AI_BASE_URL=https://api.openai.com/v1
AAW_AI_API_KEY=<set-in-secret-manager>
AAW_AI_MODEL=gpt-4.1-mini

# Notification adapter. Keep webhook URLs and bearer tokens private.
AAW_NOTIFICATION_WEBHOOK_URL=https://notify.example.com/webhook
AAW_NOTIFICATION_BEARER_TOKEN=<set-in-secret-manager>
AAW_NOTIFICATION_CHANNEL=ops-default
AAW_NOTIFICATION_SOURCE=ai-approval-workflow

# Optional action runner integration.
AAW_ACTIONS_CONFIG_PATH=/etc/ai-approval-workflow/actions.yaml
AAW_ACTION_QUEUE_DIR=/var/lib/ai-approval-workflow/actions
```

Do not copy the example secrets above into git; use deployment-managed secrets instead.

## Systemd service

```ini
[Unit]
Description=ai-approval-workflow
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/ai-approval-workflow
EnvironmentFile=/etc/ai-approval-workflow/.env
ExecStart=/opt/ai-approval-workflow/.venv/bin/uvicorn ai_approval_workflow.main:app --host ${AAW_BIND_HOST} --port ${AAW_BIND_PORT} --no-access-log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Reverse proxy

Protect admin routes with your SSO or VPN. Tokenized approval links may remain public if your token TTL and HTTPS setup are acceptable.

```nginx
location /admin {
    # auth_request /oauth2/auth; # deployment-specific SSO snippet
    proxy_pass http://127.0.0.1:8787;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /api/admin/ {
    # auth_request /oauth2/auth; # deployment-specific SSO snippet
    proxy_pass http://127.0.0.1:8787;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location / {
    proxy_pass http://127.0.0.1:8787;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Notification adapter contract

The app sends JSON to `AAW_NOTIFICATION_WEBHOOK_URL`:

```json
{
  "title": "Message title",
  "content": "Message body",
  "message": "Message body",
  "source": "ai-approval-workflow",
  "channel": "ops-default",
  "severity": "info"
}
```

If `AAW_NOTIFICATION_BEARER_TOKEN` is set, the app sends `Authorization: Bearer <token>`.

## Deploy checklist

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
python scripts/validate_workflows.py /etc/ai-approval-workflow/workflows
systemctl restart ai-approval-workflow.service
systemctl is-active ai-approval-workflow.service
curl -fsS https://approval.example.com/healthz
```
