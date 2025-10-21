# Minimal production container for repoq
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends git graphviz && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Install in editable mode with full extras
RUN pip install --no-cache-dir -e ".[full]"

ENTRYPOINT ["repoq"]
