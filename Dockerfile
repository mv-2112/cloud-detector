# Pulls the official upstream Python 3.12 environment pre-packaged with uv from GHCR
FROM ghcr.io/astral-sh/uv:0.13.6-python3.12-alpine

# Install uv installer safely
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy the build manifests
COPY pyproject.toml uv.lock README.md ./

# Copy the updated source directory layout
COPY src/ ./src/

# Sync dependencies using uv frozen tool paths
RUN uv sync --frozen --no-cache

# Place internal tool virtualenv binaries explicitly into operational scope
ENV PATH="/app/.venv/bin:$PATH"

# Set non-root security contexts
USER 65534:65534

ENTRYPOINT ["cloud-detect"]
CMD ["--include-runtime", "-o", "json"]

