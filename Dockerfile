FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements-app.txt .
RUN pip install --no-cache-dir -r requirements-app.txt \
    && useradd --create-home --uid 10001 appuser

COPY --chown=appuser:appuser api/ ./api/
COPY --chown=appuser:appuser dashboard/ ./dashboard/

USER appuser

EXPOSE 8001 8501

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]