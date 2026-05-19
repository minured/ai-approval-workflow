# Use Cases

These examples show what `ai-approval-workflow` is good at: quiet scheduled automation that only interrupts you when a decision is needed.

> Privacy note: every example below uses generic service names, placeholder paths, and public-safe wording. Put real hostnames, tokens, and commands in your private overlay.

## 1. Daily GitHub Trending brief

**Pain:** You want to track new libraries and tools, but checking trending pages manually becomes noise.

**Workflow shape:**

```text
09:00 every day
  -> fetch GitHub Trending
  -> AI summarizes notable repositories, languages, and ideas
  -> phone notification
```

**Why it helps:** You get a short daily signal instead of browsing a long page. No approval is needed because the task is read-only.

**Example file:** `examples/github-trending-daily.yaml`

## 2. Service upgrade review with approval

**Pain:** A service has new releases. You need someone to check release notes, known issues, and upgrade risk before running a fixed upgrade script.

**Workflow shape:**

```text
09:00 every day
  -> run service_version_check from allowlist
  -> AI summarizes current version, latest version, release notes, known issues, risk
  -> send approval link to phone
  -> if approved, enqueue service_bundle_upgrade
  -> root runner validates action name and runs fixed script
```

**Why it helps:** The AI does the reading and risk summary. A human still makes the final decision. The runtime never lets AI invent shell commands.

**Example file:** `examples/service-upgrade-watch.yaml`

## 3. Sanitized real-world upgrade case

This project was designed around a real operational need: checking whether a production business system and its related management component should be upgraded.

Public-safe version:

- The workflow checks two related service versions and one management component.
- The AI reads release notes and public issue reports.
- The phone approval has two buttons: **Upgrade** and **Skip**.
- If approved, a single allowlisted action upgrades the bundle together.

What stays private:

- real service names and domains;
- production hostnames and SSH details;
- webhook URLs and API tokens;
- exact upgrade commands and rollback scripts.

## 4. Certificate and domain expiry watcher

**Pain:** Expiring certificates or domains are easy to miss and painful when they break production.

**Workflow shape:**

```text
08:00 every day
  -> run readonly expiry check
  -> summarize anything expiring soon
  -> notify only when attention is needed
```

**Suggested behavior:** Use notification-only for normal reminders. Add approval only if you wire a fixed renewal or DNS action.

## 5. Backup health report

**Pain:** Backups often fail silently until you need them.

**Workflow shape:**

```text
Monday 08:00
  -> run readonly backup status check
  -> AI summarizes last successful backup, missing jobs, and risk
  -> notify phone
```

**Why it helps:** You get an operational digest, not raw logs.

## 6. CI failure triage

**Pain:** CI alerts are noisy. Many failures are transient, while some need quick human action.

**Workflow shape:**

```text
every 30 minutes during work hours
  -> fetch CI status or run readonly CLI check
  -> AI groups failures by likely cause
  -> notify with the top action items
```

**Optional approval:** Add a button for a fixed safe action such as rerunning a known workflow.

## 7. Billing and subscription drift

**Pain:** Cloud bills, SaaS renewals, and usage spikes are easy to overlook.

**Workflow shape:**

```text
every morning
  -> fetch or check billing summary
  -> AI highlights unusual spend, upcoming renewal, and reason
  -> notify phone
```

**Safety note:** Keep API credentials in private config. Do not put billing tokens in workflow YAML.

## 8. Personal convenience tasks

The same pattern works outside work:

- price drop summaries for products you care about;
- travel disruption summaries before a trip;
- policy or immigration update summaries from public sources;
- weekly reading digests from public feeds;
- home server disk and battery health checks.

The rule of thumb: if a task is repetitive, text-heavy, and occasionally needs a simple yes/no decision, it is a good fit.

## Picking the right pattern

| Need | Recommended pattern |
| --- | --- |
| Read public page and summarize | `http_fetch` + `ai_summary` + `notify` |
| Check private system state | `command_check` + `ai_summary` + `notify` |
| Ask before action | add `approval` |
| Execute after approval | add `queued_action` with a private allowlist |
| Needs arbitrary shell | do not do it; write a fixed private script and allowlist its name |
