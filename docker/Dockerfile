# Stage 1: Install production dependencies
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./
COPY src/ src/

# Install production dependencies only into /app/.venv
RUN uv sync --frozen --no-dev --no-editable

# Stage 2: Production image
FROM python:3.12-slim AS production

WORKDIR /app

# Non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1000 appuser

# Copy installed venv from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Copy resource files needed at runtime
COPY src/real_estate/resources/ /app/src/real_estate/resources/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/mcp')" || exit 1

CMD ["python", "-m", "real_estate.mcp_server.server", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
