# RepoQ Documentation Deployment

This directory contains the GitHub Actions workflow for automatically building and deploying RepoQ documentation to GitHub Pages.

## How it Works

1. **Trigger**: On push to `main` branch (when docs/ or mkdocs.yml changes)
2. **Build**: MkDocs builds the documentation
3. **Version**: Mike manages versioning (stable, latest)
4. **Deploy**: Automatically deploys to `gh-pages` branch
5. **Live**: Available at https://repo-q.github.io/repoq

## Workflow Details

- **File**: `.github/workflows/docs.yml`
- **Jobs**:
  - `build`: Builds and deploys documentation
  - `link-check`: Validates links in pull requests

## Local Development

Build documentation locally:

```bash
# Build static site
uv run mkdocs build

# Serve with hot reload
uv run mkdocs serve

# Open browser to http://localhost:8000
```

## Versioning with Mike

Mike provides documentation versioning:

```bash
# Deploy new version
uv run mike deploy --push --update-aliases 2.1 latest

# Set default version
uv run mike set-default --push stable

# List versions
uv run mike list

# Delete version
uv run mike delete 2.0
```

## Manual Deployment

If needed, deploy manually:

```bash
# Deploy latest as stable
uv run mike deploy --push --update-aliases latest stable

# Set stable as default
uv run mike set-default --push stable
```

## Activation Steps

After pushing this workflow:

1. Go to repository **Settings** → **Pages**
2. Set **Source** to: `Deploy from a branch`
3. Select branch: `gh-pages`
4. Select folder: `/ (root)`
5. Click **Save**
6. Wait 2-3 minutes for first deployment
7. Visit: https://repo-q.github.io/repoq

## Structure

Documentation follows this structure:

```
docs/
├── getting-started/    # Installation, quickstart
├── user-guide/         # Usage, configuration, commands, workflows
├── tutorials/          # 6 step-by-step tutorials
├── architecture/       # Deep technical documentation
├── api/                # Auto-generated API reference
├── development/        # Contributing, testing, proofs
├── vdad/               # Value-Driven Architecture Design
└── about/              # Limitations, license
```

## Troubleshooting

### Build Fails

Check the workflow run:
- Go to **Actions** tab
- Click on failed workflow
- Review error logs

Common issues:
- Broken links: Fix in markdown files
- Missing dependencies: Update pyproject.toml
- Syntax errors: Check mkdocs.yml

### Pages Not Updating

1. Check Actions workflow succeeded
2. Verify gh-pages branch exists
3. Check GitHub Pages settings
4. Clear browser cache
5. Wait 2-3 minutes for CDN

### Links Break After Deployment

Use relative links in markdown:

```markdown
<!-- Good -->
[Config Guide](../user-guide/configuration.md)

<!-- Bad -->
[Config Guide](/user-guide/configuration.md)
```

## Resources

- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [Mike Versioning](https://github.com/jimporter/mike)
- [GitHub Pages](https://docs.github.com/en/pages)
