# Use Cases

`ai-approval-workflow` is useful for scheduled automation that should produce concise AI summaries and only request human input when a simple decision is required.

> All examples use generic service names, placeholder paths, and public-safe wording. Real hostnames, credentials, and commands belong in deployment-specific configuration.

## 1. Daily GitHub Trending brief

**Problem:** Tracking new libraries and tools manually creates recurring browsing overhead.

**Workflow shape:**

```text
09:00 every day
  -> fetch GitHub Trending
  -> AI summarizes notable repositories, languages, and ideas
  -> send notification
```

**Result:** A short daily signal replaces manual browsing. Approval is not required because the task is read-only.

**Example file:** `examples/github-trending-daily.yaml`

## 2. Service upgrade review with approval

**Problem:** Service releases require review of release notes, known issues, and upgrade risk before running a fixed upgrade procedure.

**Workflow shape:**

```text
09:00 every day
  -> run service_version_check from allowlist
  -> AI summarizes current version, latest version, release notes, known issues, risk
  -> create mobile approval request
  -> if approved, enqueue service_bundle_upgrade
  -> root runner validates action name and runs fixed script
```

**Result:** AI performs the reading and risk summary, while a human decision gates execution. The runtime does not allow AI-generated shell commands.

**Example file:** `examples/service-upgrade-watch.yaml`

## 3. Coordinated multi-component upgrade

Some systems require multiple related components to be evaluated and upgraded together.

Generic pattern:

- A read-only check reports versions for two related services and one management component.
- AI summarizes release notes, public issue reports, compatibility risk, and recommendation.
- The approval page offers two stable choices: **Upgrade** and **Skip**.
- If approved, one allowlisted action upgrades the component bundle as a unit.

Deployment-specific values remain outside the public repository:

- service names and internal domains;
- production hostnames and SSH details;
- webhook URLs and API tokens;
- exact upgrade commands and rollback scripts.

## 4. Certificate and domain expiry watcher

**Problem:** Expiring certificates or domains can cause avoidable outages.

**Workflow shape:**

```text
08:00 every day
  -> run readonly expiry check
  -> summarize resources expiring soon
  -> notify only when attention is needed
```

**Variant:** Add approval only when a fixed renewal or DNS action is wired through an allowlisted action.

## 5. Backup health report

**Problem:** Backup jobs often fail silently until a restore is needed.

**Workflow shape:**

```text
Monday 08:00
  -> run readonly backup status check
  -> AI summarizes last successful backup, missing jobs, and risk
  -> send notification
```

**Result:** Operators receive an operational digest instead of raw logs.

## 6. CI failure triage

**Problem:** CI alerts are noisy. Some failures are transient, while others require fast action.

**Workflow shape:**

```text
every 30 minutes during work hours
  -> fetch CI status or run readonly CLI check
  -> AI groups failures by likely cause
  -> send the top action items
```

**Variant:** Add an approval button for a fixed safe action such as rerunning a known workflow.

## 7. Billing and subscription drift

**Problem:** Cloud bills, SaaS renewals, and usage spikes are easy to overlook.

**Workflow shape:**

```text
every morning
  -> fetch or check billing summary
  -> AI highlights unusual spend, upcoming renewal, and likely reason
  -> send notification
```

**Safety note:** API credentials should be stored in deployment-specific configuration, not workflow YAML.

## 8. Personal convenience tasks

The same pattern also applies outside operations:

- price change summaries for tracked products;
- travel disruption summaries before a trip;
- policy or immigration update summaries from public sources;
- weekly reading digests from public feeds;
- home server disk and battery health checks.

A good fit is a repetitive, text-heavy task that occasionally needs a simple yes/no decision.

## Picking the right pattern

| Need | Recommended pattern |
| --- | --- |
| Read public page and summarize | `http_fetch` + `ai_summary` + `notify` |
| Check internal system state | `command_check` + `ai_summary` + `notify` |
| Ask before action | add `approval` |
| Execute after approval | add `queued_action` with deployment-managed allowlist |
| Needs arbitrary shell | write a fixed script and allowlist its action name |
