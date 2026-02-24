FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

RUN apt-get update && apt-get install -y netcat-traditional gettext && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot


ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Create playwright directory with proper permissions
RUN mkdir -p /ms-playwright && chmod -R 777 /ms-playwright

WORKDIR /app

# Sync dependencies (without project code) — only re-runs when uv.lock/pyproject.toml change
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

ENV PATH="/app/.venv/bin:$PATH"

# Install Playwright browsers BEFORE copying source code
RUN --mount=type=cache,target=/root/.cache/ms-playwright \
    playwright install chromium --with-deps && \
    rm -rf /var/lib/apt/lists/*

# Copy code and ensure ownership belongs to nonroot
COPY --chown=nonroot:nonroot . /app

# Ensure nonroot owns the virtualenv from previous step
RUN chown -R nonroot:nonroot /app/.venv

# Create media directory with proper permissions
RUN mkdir -p /app/media && chown -R nonroot:nonroot /app/media

USER nonroot

# Mount the cache with the correct UID/GID for the nonroot user
RUN --mount=type=cache,target=/home/nonroot/.cache/uv,uid=999,gid=999 \
    uv sync --locked

ENTRYPOINT ["./docker-entrypoint.sh"]
