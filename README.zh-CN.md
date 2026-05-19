# ai-approval-workflow

[English](README.md) | [简体中文](README.zh-CN.md)

开源的定时 AI 工作流运行时，重点支持手机端轻量审批。

它围绕两个核心交互设计：

1. **定时 AI 任务**：按 cron 触发，收集上下文，让 AI 总结，然后通知你；
2. **手机人工审批**：在执行白名单动作前，发送一个短审批链接，让你用 Execute / Skip / Snooze 或自定义按钮做简单选择。

这个项目刻意**不是**聊天机器人，也**不是**可视化工作流搭建器。自然语言创建、编辑、删除任务由内置 Codex skill 处理；skill 会生成可审查的 YAML 工作流文件。

## 包含什么

- FastAPI 运行时：健康检查、审批页、管理页和 API。
- APScheduler：从 YAML 工作流注册 cron 定时任务。
- 通用 webhook 通知：可接 WeChat、WeCom、Slack、Discord 或你自己的通知适配器。
- 手机审批页：稳定的决策值和可自定义按钮文案。
- 安全动作边界：工作流只引用命名 command/action，真正命令放在私有白名单配置里。
- Codex skill：支持自然语言工作流 CRUD，以及克制的通用框架能力升级。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
pytest -q
uvicorn ai_approval_workflow.main:app --host 127.0.0.1 --port 8787
```

打开：

- `http://127.0.0.1:8787/healthz`：健康检查；
- `http://127.0.0.1:8787/admin`：查看和软删除工作流。

## 工作流文件

工作流 YAML 文件位于 `AAW_WORKFLOWS_DIR`。重启服务前建议先校验：

```bash
.venv/bin/python scripts/validate_workflows.py ./examples
```

常见 MVP step 类型：

- `http_fetch`：GET 一个公开 URL，并把响应文本交给 AI；
- `ai_summary`：总结最近的任务结果或抓取结果；
- `notify`：通过配置的 webhook 发送通知；
- `approval`：创建一个手机审批页，提供简单选择；
- `command_check`：从私有白名单配置里运行一个命名的只读命令；
- `queued_action`：把审批通过后的命名动作写入队列，交给 root-side runner 执行；
- `demo_summary` / `demo_action`：安全的本地演示步骤。

示例：

- `examples/github-trending-daily.yaml`：只通知的 GitHub Trending 日报；
- `examples/service-upgrade-watch.yaml`：通用服务升级检查 + 审批 + 队列动作。

## 自然语言管理工作流

内置 Codex skill 位于：

```text
skills/ai-approval-workflow/SKILL.md
```

把它安装或复制到 `$CODEX_HOME/skills/ai-approval-workflow/` 后，可以使用类似提示：

- “每天早上 9 点给我发 GitHub Trending 总结，不需要审批”
- “每天检查某个服务版本，如果值得升级就发手机审批，按钮是升级/跳过”
- “删除某个定时任务”

skill 应该把私有主机名、token、脚本和生产工作流文件保留在公开仓库之外。

## 私有 overlay

把这个仓库作为通用框架发布是安全的。你的部署专属数据应该留在 git 外面：

- `.env` 和任何 `.env.*` 文件；
- 生产工作流文件，例如 `/etc/ai-approval-workflow/workflows` 或其他私有目录；
- action 白名单，例如 `/etc/ai-approval-workflow/actions.yaml`；
- `command_check` 或 `queued_action` 使用的 root-owned 脚本；
- SQLite 数据库和 action queue 文件。

发布前请阅读 [Private Overlay](docs/private-overlay.md) 和 [Publishing Checklist](docs/publishing-checklist.md)。

## 文档

- [Design](docs/design.md)
- [Security Model](docs/security.md)
- [Deployment](docs/deployment.md)
- [Action Runner](docs/action-runner.md)
- [Private Overlay](docs/private-overlay.md)
- [Publishing Checklist](docs/publishing-checklist.md)

## License

MIT.
