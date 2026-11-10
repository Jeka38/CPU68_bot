FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DB_PATH=/data/users.db

# DejaVu fonts are used by Pillow to render rank cards on Linux.
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py ranks.py i18n.py ./
COPY locales ./locales

# The database lives on a bind mount (see docker-compose.yml), not in the image.
RUN mkdir -p /data
VOLUME ["/data"]

CMD ["python", "bot.py", "bot"]
