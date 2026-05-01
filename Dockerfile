# ToolCrate Production Container

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    ca-certificates \
    cron \
    make \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock* README.md ./

# Install production dependencies only
RUN uv sync --frozen --no-dev --no-install-project 2>/dev/null || uv sync --no-dev --no-install-project

# Copy source and scripts
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY Makefile configure_toolcrate.sh ./

# Install the project. The hatch frontend build hook (scripts/build_frontend.py)
# detects npm is missing and writes a stub index.html, so the wheel still builds
# without Node. Set TOOLCRATE_SKIP_FRONTEND_BUILD=1 to short-circuit explicitly.
ENV TOOLCRATE_SKIP_FRONTEND_BUILD=1
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Create necessary directories
RUN mkdir -p /app/data/downloads /app/data/library /app/logs /app/config

# Create non-root user
RUN useradd -m -u 1000 toolcrate && \
    chown -R toolcrate:toolcrate /app
USER root
RUN touch /var/log/cron.log
USER toolcrate

CMD ["uv", "run", "toolcrate", "--help"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run python3 -c "import toolcrate; print('ok')" || exit 1
