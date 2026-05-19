# Publishing Checklist

Run this checklist before pushing the repository to a public remote.

## Tests

```bash
pytest -q
python scripts/validate_workflows.py examples
git diff --check
```

## Privacy scan

```bash
# Replace the placeholders below with deployment-specific domains, hostnames, and script names.
git grep -n -E 'internal-domain-example|internal-host-example|secret-script-example' || true
```

Optional if Gitleaks is installed:

```bash
gitleaks detect --source . --no-git
```

## Git hygiene

```bash
git status --short
git ls-files | grep -E '(^\.env$|^data/|\.db$|\.sqlite$|actions\.yaml$)' && echo 'unexpected private file'
```

Make sure `.env`, production workflows, action allowlists, databases, and local scripts are not tracked.
