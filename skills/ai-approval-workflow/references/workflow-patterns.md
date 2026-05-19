# Workflow Patterns

Use these as reusable shapes when translating natural language into workflow YAML.

## Scheduled digest

For “每天总结 X 发我”:

```yaml
steps:
  - {id: fetch, type: http_fetch, url: "https://example.com"}
  - {id: summarize, type: ai_summary, prompt: "简短中文总结"}
  - {id: notify, type: notify, title: "Daily Digest"}
```

## Monitor and approve action

For “检查 X，值得就问我是否执行 Y”:

```yaml
steps:
  - {id: check, type: command_check, name: named_readonly_check}
  - {id: summarize, type: ai_summary, prompt: "判断是否值得执行"}
  - id: approval
    type: approval
    title: "执行审批"
    choices:
      - {value: approve, label: 执行, style: approve}
      - {value: reject, label: 不执行, style: reject}
  - {id: action, type: queued_action, action: named_allowlisted_action}
```

## Version watch

For “检查版本更新和有没有问题”:

- Use `command_check` if current version is private/local.
- Use `http_fetch` if all sources are public.
- AI prompt should ask for: current version, latest version, release notes, recent issues, risk, recommendation.

## Approval labels

Keep stored decision values stable:

- approve -> label can be `升级`, `执行`, `通过`
- reject -> label can be `不升级`, `跳过`, `拒绝`
- snooze -> label can be `稍后`
