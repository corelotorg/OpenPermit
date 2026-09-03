FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    ORI_BIND_HOST=0.0.0.0

WORKDIR /app

COPY reference-node/requirements.txt /app/reference-node/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/reference-node/requirements.txt

COPY . /app
RUN mkdir -p /app/reference-node/state

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()" || exit 1

CMD ["python", "reference-node/server.py"]
