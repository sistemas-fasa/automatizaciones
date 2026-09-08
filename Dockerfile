FROM python:3.12-slim

ARG SOURCE_COMMIT=not-set

LABEL org.opencontainers.image.source="https://github.com/sistemas-fasa/automatizaciones" \
      org.opencontainers.image.revision="${SOURCE_COMMIT}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=America/Argentina/Buenos_Aires

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash cron ca-certificates coreutils util-linux \
       libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/automatizaciones
COPY . /opt/automatizaciones

RUN if [ -f requirements-runtime.txt ]; then \
      pip install --no-cache-dir -r requirements-runtime.txt; \
    fi \
    && mkdir -p /data /backups /etc/automatizaciones \
    && touch /etc/automatizaciones/READY

COPY runner.sh /usr/local/bin/automatizaciones-runner
COPY scheduler-entrypoint.sh /usr/local/bin/automatizaciones-scheduler-entrypoint
COPY cron.disabled /etc/cron.d/automatizaciones

RUN chmod 0755 \
      /usr/local/bin/automatizaciones-runner \
      /usr/local/bin/automatizaciones-scheduler-entrypoint \
    && chmod 0644 /etc/cron.d/automatizaciones

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD test -f /etc/automatizaciones/READY

CMD ["sleep", "infinity"]
