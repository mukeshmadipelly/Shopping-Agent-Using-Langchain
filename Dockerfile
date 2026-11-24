# Dockerfile for AWS App Runner deployment
FROM python:3.13-slim

WORKDIR /app

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (for cache efficiency)
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/
COPY resources/ ./resources/

# Seed the SQLite database (store.db is gitignored, so it must be built into the image)
RUN uv run python -m src.shopping_agent.setup_db

# Expose Streamlit port
EXPOSE 8501

# Run the app
CMD ["uv", "run", "streamlit", "run", "src/shopping_agent/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]