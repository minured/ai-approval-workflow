# Publishing Checklist

Run this before pushing the repository to a public remote.

## Tests

```bash
pytest -q
python scripts/validate_workflows.py examples
git diff --check
```

## Privacy scan

```bash
# Replace the placeholders below with private domains, hostnames, and script names from your own deployment.
git grep -n -E 'your-private-domain|your-private-host|your-secret-script' || true
```

Optional if you have Gitleaks installed:

```bash
gitleaks detect --source . --no-git
```

## Git hygiene

```bash
git status --short
git ls-files | grep -E '(^\.env$|^data/|\.db$|\.sqlite$|actions\.yaml$)' && echo 'unexpected private file'
```

Make sure `.env`, private workflows, action allowlists, databases, and local scripts are not tracked.
