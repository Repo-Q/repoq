# Installation

RepoQ offers multiple installation methods to suit different use cases.

## Requirements

- **Python**: 3.9+ (3.11+ recommended)
- **Operating System**: Linux, macOS, Windows
- **Memory**: 512MB+ available RAM
- **Optional**: Graphviz for dependency diagrams

## Installation Methods

### Standard Installation

=== "pip (Recommended)"
    ```bash
    pip install repoq[full]
    ```
    
    This installs RepoQ with all optional dependencies for complete functionality:
    
    - `rdflib` - Semantic web and ontological reasoning
    - `pydriller` - Git repository analysis
    - `lizard` - Complexity analysis
    - `graphviz` - Dependency visualization
    - `pyshacl` - RDF validation

=== "Basic Installation"
    ```bash
    pip install repoq
    ```
    
    Minimal installation with core functionality only. You can add optional dependencies later:
    
    ```bash
    pip install repoq[full]  # Upgrade to full
    ```

=== "Development Installation"
    ```bash
    git clone https://github.com/kirill-0440/repoq.git
    cd repoq
    pip install -e ".[full,dev,docs]"
    ```
    
    Includes development and documentation dependencies for contributors.

### System Dependencies

#### Graphviz (Optional)

For dependency diagrams and visualization:

=== "Ubuntu/Debian"
    ```bash
    sudo apt-get install graphviz
    ```

=== "macOS"
    ```bash
    brew install graphviz
    ```

=== "Windows"
    ```bash
    choco install graphviz
    # or download from https://graphviz.org/download/
    ```

#### Git

RepoQ requires Git for repository analysis:

=== "Ubuntu/Debian"
    ```bash
    sudo apt-get install git
    ```

=== "macOS"
    ```bash
    # Git is included with Xcode Command Line Tools
    xcode-select --install
    ```

=== "Windows"
    ```bash
    choco install git
    # or download from https://git-scm.com/
    ```

## Verification

Verify your installation:

```bash
# Check RepoQ version
repoq --help

# Run basic analysis
repoq structure . --output test.json

# Check ontological capabilities
python -c "from repoq.ontologies import ontology_manager; print('✅ Ontologies available')"
```

## Virtual Environment (Recommended)

Use a virtual environment to avoid dependency conflicts:

=== "venv"
    ```bash
    python -m venv repoq-env
    source repoq-env/bin/activate  # Linux/macOS
    # or repoq-env\Scripts\activate  # Windows
    pip install repoq[full]
    ```

=== "conda"
    ```bash
    conda create -n repoq python=3.11
    conda activate repoq
    pip install repoq[full]
    ```

## Docker Installation

For containerized deployment:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Install RepoQ
RUN pip install repoq[full]

# Set working directory
WORKDIR /workspace

# Entry point
ENTRYPOINT ["repoq"]
```

Build and run:

```bash
docker build -t repoq .
docker run -v $(pwd):/workspace repoq structure /workspace
```

## Troubleshooting

### Common Issues

#### ImportError: No module named 'rdflib'

Install full dependencies:
```bash
pip install repoq[full]
```

#### Graphviz not found

Install system Graphviz package (see System Dependencies above).

#### Permission errors on Windows

Run PowerShell as Administrator or use:
```bash
pip install --user repoq[full]
```

#### Memory issues with large repositories

Increase memory limits or use filtering:
```bash
repoq structure /large/repo --max-files 1000 --exclude-globs "*.min.js,node_modules"
```

### Getting Help

- **Documentation**: Check this documentation
- **Issues**: [GitHub Issues](https://github.com/kirill-0440/repoq/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kirill-0440/repoq/discussions)

## Next Steps

- [Quick Start Guide](quickstart.md) - Your first analysis
- [Configuration](configuration.md) - Customizing RepoQ
- [CLI Commands](../user-guide/commands.md) - Complete command reference