# Imagem da API. NAO TESTADA LOCALMENTE (o ambiente de desenvolvimento nao tem Docker).
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
CMD ["python", "-m", "arbitrationlab"]
