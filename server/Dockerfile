FROM node:22-slim AS client
WORKDIR /app/client
COPY client/package*.json ./
RUN npm ci
COPY client/ ./
RUN npm run build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /usr/local/bin/uv
WORKDIR /app/server
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY server/ ./
RUN uv sync --frozen --no-dev
COPY --from=client /app/client/dist /app/client/dist

RUN useradd --system --no-create-home lms && mkdir -p /app/data && chown lms /app/data
USER lms

ENV LMS_DB_URL=sqlite+aiosqlite:////app/data/lms.sqlite3
ENV LMS_CLIENT_DIST=/app/client/dist
VOLUME ["/app/data"]
EXPOSE 8000
CMD ["/app/server/.venv/bin/uvicorn", "--factory", "lms.app:app_from_env", "--host", "0.0.0.0", "--port", "8000"]
