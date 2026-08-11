FROM python:3.11-slim

WORKDIR /opt/sof-runtime
COPY . .
RUN python -m pip install --no-cache-dir ".[service,mcp]"

ENV SOF_RUNTIME_WORKSPACE=/data
VOLUME ["/data"]
EXPOSE 8080

CMD ["sof", "serve", "--workspace-root", "/data/service", "--host", "0.0.0.0", "--port", "8080"]
