FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 10001 halite \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin halite

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=root:root . .
RUN mkdir -p /app/data && chown -R 10001:10001 /app/data && chmod 0750 /app/data

ARG GIT_SHA=unknown
ARG DEPLOYED_AT=
ENV GIT_SHA=$GIT_SHA \
    DEPLOYED_AT=$DEPLOYED_AT

USER 10001:10001

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header", "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1"]
