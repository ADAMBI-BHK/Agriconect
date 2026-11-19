FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "psycopg[binary]"
COPY alembic.ini .
COPY migrations migrations
COPY app app
RUN mkdir -p uploads
EXPOSE 3000
CMD ["sh", "-c", "python -m app.cli init-db && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-3000}"]
