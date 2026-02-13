FROM python:3.12-slim

WORKDIR /app

# psycopg2-binary bundles its own libpq, so libpq-dev is not needed.
# gcc is kept for any source-built optional packages (e.g. libpff).
# See README §PST Conversion for a recipe to build libpff from source.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["celery", "-A", "app.celery_app:celery_app", "worker", "--loglevel=info", "-c", "2"]
