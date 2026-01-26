FROM docker.io/python:3.12-slim

WORKDIR /app

# Install uv and AWS CLI for Hive cluster authentication
RUN pip install --no-cache-dir uv awscli

# Copy the MCP server code
COPY . /app/

# Install dependencies
RUN uv sync --no-cache

# Expose port for HTTP transport
EXPOSE 8000

# Set default environment variables
ENV HIVE_KUBECONFIG=/root/.kube/hive.yaml
ENV HIVE_CONTEXT=hive-cluster
ENV UVICORN_HOST=0.0.0.0
ENV UVICORN_PORT=8000

# Run the MCP server with HTTP transport via main.py
CMD ["sh", "-c", "UVICORN_HOST=0.0.0.0 UVICORN_PORT=8000 uv run python main.py --transport http --kubeconfig /root/.kube/hive.yaml --context hive-cluster"]

