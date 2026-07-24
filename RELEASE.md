# PyPI Release Guide

## Prerequisites

1. Create a PyPI account at https://pypi.org/account/register/
2. Generate an API token at https://pypi.org/manage/account/token/
3. (Recommended) Enable trusted publishing for GitHub Actions

## Manual Release

### Option A: Using API Token (Interactive)

```bash
cd /Users/marco/projects/dataveil
source venv/bin/activate

# Build
python -m build

# Upload (will prompt for token)
twine upload dist/*
```

When prompted:
- Username: `__token__`
- Password: Your PyPI API token (starts with `pypi-`)

### Option B: Using .pypirc (Non-interactive)

Create `~/.pypirc`:

```ini
[distutils]
index-servers = pypi

[pypi]
username = __token__
password = pypi-your-api-token-here
```

Then:

```bash
twine upload dist/*
```

### Option C: GitHub Actions (Recommended for CI/CD)

1. Add `PYPI_API_TOKEN` to your GitHub repository secrets
2. Push a tag: `git tag v0.1.0 && git push origin v0.1.0`
3. GitHub Actions will automatically build and publish

## Test on TestPyPI First (Recommended)

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ dataveil
```

## Post-Release Checklist

- [ ] `pip install dataveil` works
- [ ] `dv --help` works after pip install
- [ ] Update GitHub release notes
- [ ] Announce on social media / forums

## Current Build Status

✅ Package built successfully:
- `dist/dataveil-0.1.0-py3-none-any.whl` (41 KB)
- `dist/dataveil-0.1.0.tar.gz` (40 KB)

✅ Twine check passed

⚠️ Upload requires PyPI API token (not available in this environment)
