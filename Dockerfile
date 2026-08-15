FROM node:22-bookworm-slim AS web-build

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile
COPY apps/web apps/web
COPY scripts/build-static.mjs scripts/prepare-static-export.mjs scripts/
RUN pnpm build:static

FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PERSONAL_AI_OS_DATA_DIR=/data
ENV PERSONAL_AI_OS_WEB_DIR=/app/web
WORKDIR /app

COPY requirements-runtime.txt ./
COPY packages packages
COPY apps/api apps/api
RUN python -m pip install --no-cache-dir -r requirements-runtime.txt

COPY --from=web-build /app/apps/web/out /app/web

RUN addgroup --system personalai && adduser --system --ingroup personalai personalai \
    && mkdir -p /data && chown -R personalai:personalai /app /data
USER personalai

EXPOSE 8080
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"

CMD ["python", "-m", "uvicorn", "personal_ai_os.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips=*"]
