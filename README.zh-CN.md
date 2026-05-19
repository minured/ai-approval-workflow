# ai-approval-workflow

[English](README.md) | [简体中文](README.zh-CN.md)

![ai-approval-workflow hero](docs/assets/hero.svg)

开源的定时 AI 工作流运行时，重点支持手机端轻量审批。

`ai-approval-workflow` 适合这类重复任务：

```text
某件事需要定期检查
  -> AI 可以阅读并总结结果
  -> 你只希望在需要决策时被打扰
  -> 真正执行动作必须是固定、可审查、白名单的
```

这个项目刻意**不是**聊天机器人，也**不是**可视化工作流搭建器。自然语言创建、编辑、删除任务由内置 Codex skill 处理；skill 会生成可审查的 YAML 工作流文件。

## 为什么需要它

很多自动化工具要么太沉默，要么太危险：

- cron 任务会执行，但上下文不足；
- 聊天机器人让简单决策也变成长对话；
- 如果 AI agent 能直接执行任意命令，风险很高；
- 人也不想每天盯着另一个 dashboard。

这个项目保留中间最实用的部分：**定时 AI 摘要 + 手机简单审批 + 固定白名单动作**。

## 它能做什么

- 从 YAML cron 定义运行定时 AI 任务。
- 抓取公开页面，或运行命名的只读检查。
- 把长输出总结成适合手机阅读的短消息。
- 用简单按钮发起手机审批，例如 Upgrade / Skip。
- 将审批通过的动作写入队列，由 root-side runner 再次校验 action 名称。
- 提供小型管理页，用于查看和软删除任务。
- 通过 Codex skill 把自然语言转换成可审查的 workflow YAML。

## 工作原理

![Architecture diagram](docs/assets/architecture.svg)

公开仓库只包含通用框架。你的私有部署把 secret、生产 workflow、action 白名单、脚本和数据库放在 git 外部。

![Workflow lifecycle](docs/assets/workflow-lifecycle.svg)

## 产品界面

手机审批：

![Mobile approval mockup](docs/assets/mobile-approval-mock.svg)

管理页：

![Admin dashboard mockup](docs/assets/admin-dashboard-mock.svg)

## 真实使用场景

- **GitHub Trending 摘要：** 每天早上总结值得关注的仓库。
- **服务升级检查：** 检查版本和已知问题，再问你是否升级。
- **证书/域名过期提醒：** 在重要资源过期前提醒。
- **备份健康报告：** 把原始备份日志变成每周风险摘要。
- **CI 失败归因：** 聚合失败原因并提示下一步动作。
- **账单/订阅变化：** 总结异常支出或即将续费项目。
- **生活便利任务：** 商品降价、旅行风险、政策更新、家庭服务器健康检查。

更多具体例子见 [使用场景](docs/use-cases.zh-CN.md)，其中包含一个脱敏的真实升级审批案例。

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

- [使用场景](docs/use-cases.zh-CN.md)
- [Design](docs/design.md)
- [Security Model](docs/security.md)
- [Deployment](docs/deployment.md)
- [Action Runner](docs/action-runner.md)
- [Private Overlay](docs/private-overlay.md)
- [Publishing Checklist](docs/publishing-checklist.md)

## License

MIT.
