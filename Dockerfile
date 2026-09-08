FROM node:24 AS web
WORKDIR /build/apps/web
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt && useradd --create-home --uid 10001 farmtact
COPY packages/ packages/
COPY services/ services/
COPY runtime/ runtime/
COPY config/ config/
COPY research/ research/
COPY scripts/serve.py scripts/serve.py
COPY data/fixtures/ data/fixtures/
COPY reports/deepseek/latest.json reports/deepseek/latest.json
COPY --from=web /build/apps/web/dist apps/web/dist
RUN mkdir -p data/runtime data/raw data/normalized data/manifests data/reports && chown -R farmtact:farmtact /app
USER farmtact
EXPOSE 8080
CMD ["python", "scripts/serve.py"]
