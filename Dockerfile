# ToolCrate Production Container
# Lightweight container for running ToolCrate in production

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_CACHE_DIR=/tmp/poetry_cache
ENV POETRY_VENV_IN_PROJECT=1
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Basic build tools
    build-essential \
    curl \
    git \
    # Docker dependencies (if needed)
    ca-certificates \
    gnupg \
    lsb-release \
    # Cron for scheduling
    cron \
    # Additional tools
    make \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && chmod +x $POETRY_HOME/bin/poetry

# Create working directory
WORKDIR /app

# Copy dependency files first for better Docker layer caching
COPY pyproject.toml poetry.lock* README.md ./

# Install only production dependencies
RUN poetry install --only=main --no-root && rm -rf $POETRY_CACHE_DIR

# Copy the entire project source code
COPY src/ ./src/
COPY bin/ ./bin/
COPY Makefile ./
COPY install.sh ./
COPY configure_toolcrate.sh ./
COPY setup.py ./

# Make scripts executable
RUN chmod +x ./bin/* ./install.sh ./configure_toolcrate.sh

# Install the project
RUN poetry install --only=main

# Install the package globally so 'toolcrate' command is available
RUN pip install -e .

# Create necessary directories (including empty config directory)
RUN mkdir -p /app/data/downloads /app/data/library /app/logs /app/config

# Create a non-root user for security
RUN useradd -m -u 1000 toolcrate && \
    chown -R toolcrate:toolcrate /app
USER toolcrate

# Set up cron service (run as root for cron setup, then switch back)
USER root
RUN service cron start
USER toolcrate

# Set the default command
CMD ["toolcrate", "--help"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import toolcrate; print('ToolCrate is healthy')" || exit 1
