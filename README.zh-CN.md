# ai-approval-workflow

[English](README.md) | [简体中文](README.zh-CN.md)

![ai-approval-workflow hero](docs/assets/hero.svg)

开源的定时 AI 工作流运行时，重点支持手机端轻量审批。

`ai-approval-workflow` 面向这类重复的运维或个人任务：

```text
定期检查
  -> 结果可由 AI 阅读
  -> 生成简短通知或审批请求
  -> 审批后可选执行固定动作
```

该项目刻意**不是**聊天机器人，也**不是**可视化工作流搭建器。自然语言创建、编辑、删除任务由内置 Codex skill 提供；skill 会生成可审查的 YAML 工作流文件。

## 为什么需要它

很多自动化系统容易落入两个极端：

- cron 任务会静默执行，但上下文有限；
- 聊天机器人和 agent 会让简单决策变成冗长交互；
- 直接让 AI 执行命令会带来不安全的运维边界；
- dashboard 需要持续的人类注意力。

该项目聚焦更窄、更可控的模式：**定时 AI 摘要 + 手机审批 + 固定白名单动作**。

## 它能做什么

- 从 YAML cron 定义运行定时 AI 任务。
- 抓取公开页面，或运行命名的只读检查。
- 把长输出总结成适合手机阅读的短消息。
- 创建带有简单按钮的审批页，例如 Upgrade / Skip。
- 将审批通过的动作写入队列，由 root-side runner 再次校验 action 名称。
- 提供小型管理页，用于查看和软删除已配置任务。
- 通过内置 skill 将自然语言任务请求转换成可审查的 workflow YAML。

## 工作原理

![Architecture diagram](docs/assets/architecture.svg)

公开仓库只包含通用框架代码。部署专属 secret、生产 workflow、action 白名单、脚本和数据库保留在 git 之外。

![Workflow lifecycle](docs/assets/workflow-lifecycle.svg)

## 产品界面

手机审批：

![Mobile approval mockup](docs/assets/mobile-approval-mock.svg)

管理页：

![Admin dashboard mockup](docs/assets/admin-dashboard-mock.svg)

## 使用场景

- **GitHub Trending 摘要：** 按计划总结值得关注的仓库。
- **服务升级检查：** 检查版本和已知问题，再发起升级审批。
- **证书/域名过期提醒：** 在重要资源过期前提醒。
- **备份健康报告：** 把原始备份日志变成每周风险摘要。
- **CI 失败归因：** 聚合失败并总结可能原因。
- **账单/订阅变化：** 总结异常支出或即将续费项目。
- **生活便利任务：** 价格变化、旅行风险、政策更新、家庭服务器健康检查。

更多具体例子见 [使用场景](docs/use-cases.zh-CN.md)，其中包含一个多组件服务升级审批模式。

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
- `command_check`：从部署方维护的白名单配置里运行一个命名的只读命令；
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

安装或复制到 `$CODEX_HOME/skills/ai-approval-workflow/` 后，可使用类似请求：

- `每天早上 9 点发送 GitHub Trending 摘要，不需要审批。`
- `每天检查服务版本，如果值得升级就发手机审批，按钮是 Upgrade / Skip。`
- `软删除每周备份报告工作流。`

skill 会避免把主机名、token、脚本和生产 workflow 文件写入公开仓库。

## 部署专属配置

该仓库适合作为通用框架公开发布。部署专属数据应保留在 git 之外：

- `.env` 和任何 `.env.*` 文件；
- 生产工作流文件，例如 `/etc/ai-approval-workflow/workflows` 或其他运维方管理的目录；
- action 白名单，例如 `/etc/ai-approval-workflow/actions.yaml`；
- `command_check` 或 `queued_action` 使用的 root-owned 脚本；
- SQLite 数据库和 action queue 文件。

发布 fork 或衍生项目之前，请阅读 [部署专属配置](docs/private-overlay.md) 和 [Publishing Checklist](docs/publishing-checklist.md)。

## 文档

- [使用场景](docs/use-cases.zh-CN.md)
- [Design](docs/design.md)
- [Security Model](docs/security.md)
- [Deployment](docs/deployment.md)
- [Action Runner](docs/action-runner.md)
- [部署专属配置](docs/private-overlay.md)
- [Publishing Checklist](docs/publishing-checklist.md)

## License

MIT.
