# Test image: Python for the adapter, Node for the ctx reference implementation.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @promptowl/contextnest-cli@2.6.0 \
    && pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml README.md ./
COPY contextnest_adapter ./contextnest_adapter
COPY tests ./tests
COPY examples ./examples
RUN uv venv && uv pip install -e ".[dev]"
ENV PATH="/app/.venv/bin:$PATH"
CMD ["pytest", "-q"]
