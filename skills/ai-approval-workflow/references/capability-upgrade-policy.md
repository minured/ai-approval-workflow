# Capability Upgrade Policy

Use this when a natural-language request cannot be expressed with the current workflow DSL.

## Upgrade only if all gates pass

1. **Reusable:** the new primitive can support at least three categories of tasks.
2. **Generic name:** the core feature name has no business/service-specific nouns.
3. **Deployment split:** hostnames, tokens, SSH details, and business procedures stay in runtime config or deployment-managed scripts.
4. **Testable:** unit tests can prove the primitive without touching production.
5. **Safe boundary:** AI may summarize/choose config, but cannot generate arbitrary shell for execution.
6. **Confirmed:** the operator has approved the gap, abstraction, files, and deployment plan.

## Required proposal before implementation

Show these bullets and wait for confirmation:

```text
Capability gap:
Generic abstraction:
Why this is reusable:
Deployment adapter/config:
Security boundary:
Files to add/change:
Tests/verification:
Deployment impact:
```

## Layering rule

- **Core framework:** reusable primitives such as `http_fetch`, `command_check`, `approval`, `queued_action`.
- **Deployment adapter:** root-owned scripts, allowlist entries, host-specific config.
- **Workflow YAML:** schedule and composition only.

Do not put a deployment-specific adapter into core just because one task needs it.

## Good vs bad abstractions

Good:

- `command_check`: run a named read-only allowlisted command.
- `queued_action`: enqueue a named approved action for a root runner.
- `approval.choices`: labels for simple mobile decisions.

Bad:

- `upgrade_named_service`: business-specific core step.
- `ssh_exec`: too broad; lets AI create unsafe commands.
- `wechat_chatbot_mode`: outside product scope.
