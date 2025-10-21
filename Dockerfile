# Multi-stage Dockerfile for RepoQ
# Stage 1: Builder - compile dependencies and build wheel
# Stage 2: Runtime - minimal image with only runtime dependencies

# ============================================================================
# STAGE 1: Builder
# ============================================================================
FROM python:3.11-alpine AS builder

# Install build dependencies
# - git: for git operations during build
# - gcc, musl-dev, libffi-dev: for compiling Python C extensions
# - graphviz: for graph generation dependencies
RUN apk add --no-cache \
    git \
    gcc \
    musl-dev \
    libffi-dev \
    graphviz \
    graphviz-dev

# Set working directory
WORKDIR /build

# Copy dependency files first (better layer caching)
COPY pyproject.toml README.md ./
COPY repoq/ ./repoq/

# Install build tools and create wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Create wheel for repoq and download all dependencies (including [full] extras)
RUN pip wheel --no-cache-dir --wheel-dir /wheels . && \
    pip wheel --no-cache-dir --wheel-dir /wheels ".[full]"

# Install repoq with full dependencies from wheels
RUN pip install --no-cache-dir \
    --find-links /wheels \
    --no-index \
    repoq[full]

# ============================================================================
# STAGE 2: Runtime
# ============================================================================
FROM python:3.11-alpine AS runtime

# Install runtime dependencies only
# - git: required for repository analysis
# - graphviz: required for graph generation
# - bash, curl: for health checks and debugging
RUN apk add --no-cache \
    git \
    graphviz \
    bash \
    curl

# Create non-root user for security
RUN addgroup -S repoq && adduser -S -G repoq repoq

# Set working directory
WORKDIR /app

# Copy wheels from builder
COPY --from=builder /wheels /wheels

# Install RepoQ with full dependencies
RUN pip install --no-cache-dir \
    --find-links /wheels \
    --no-index \
    repoq[full] && \
    rm -rf /wheels

# Copy ontologies and shapes (if not included in wheel)
COPY --chown=repoq:repoq repoq/ontologies/ /app/ontologies/
COPY --chown=repoq:repoq repoq/shapes/ /app/shapes/

# Switch to non-root user
USER repoq

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/repoq/.local/bin:$PATH"

# Health check (verify repoq CLI is available)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD repoq --help > /dev/null || exit 1

# Default command: show help
ENTRYPOINT ["repoq"]
CMD ["--help"]

# ============================================================================
# Usage:
# ============================================================================
# Build:
#   docker build -t repoq:latest .
#
# Run analysis on current directory:
#   docker run --rm -v $(pwd):/repo repoq:latest analyze /repo --format json
#
# Run with quality gate:
#   docker run --rm -v $(pwd):/repo repoq:latest gate --base main --head .
#
# Interactive shell:
#   docker run --rm -it --entrypoint bash repoq:latest
# ============================================================================
