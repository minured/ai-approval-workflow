# Private Overlay

Use this repository as the public framework. Keep deployment-specific behavior in a private overlay.

## Keep private

- `.env` and any `.env.*` files.
- Production workflow YAML files if they contain private URLs, schedules, channel names, or business details.
- `/etc/ai-approval-workflow/actions.yaml` or equivalent action allowlists.
- Root-owned scripts invoked by `command_check` or `queued_action`.
- Databases, action queues, logs, cookies, API keys, SSH keys, and webhooks.

## Keep public

- Generic runtime code.
- Generic workflow step types.
- Example workflows with placeholder domains and disabled schedules.
- Documentation that explains extension points without naming private infrastructure.
- Tests that use fake services and temporary files.

## Suggested directory split

```text
public repo:
  ai-approval-workflow/
    src/
    scripts/
    skills/
    docs/
    examples/

private host:
  /etc/ai-approval-workflow/.env
  /etc/ai-approval-workflow/workflows/*.yaml
  /etc/ai-approval-workflow/actions.yaml
  /usr/local/bin/service-version-check
  /usr/local/bin/service-bundle-upgrade
  /var/lib/ai-approval-workflow/
```

## Development loop

1. Add generic capability to the public repo only when it is reusable.
2. Add business-specific checks/actions as private allowlisted scripts.
3. Validate examples and tests locally.
4. Run the publishing checklist before pushing to a public remote.
