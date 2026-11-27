# Imagem da API. Verificada com Docker em 2026-11-27.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data && chown appuser /app/data

USER appuser
EXPOSE 8000
ENV ARBITRATIONLAB_DATABASE_URL=sqlite:////app/data/arbitrationlab.db
# Dentro do container escuta em 0.0.0.0; o compose só publica em 127.0.0.1 no host.
CMD ["uvicorn", "arbitrationlab.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
