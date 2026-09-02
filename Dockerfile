# Образ для Django + Celery (web, celery-worker, celery-beat)
FROM python:3.12-slim

# Защита от питонских .pyc и буферизации вывода
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Устанавливаем системные зависимости:
# - libpq-dev — для psycopg2/psycopg (библиотека PostgreSQL)
# - build-essential, python3-dev, gcc — компилятор, т.к. psycopg2==2.9.10 и
#   ряд C-пакетов собираются из исходников на slim-образах
# - libffi-dev — для некоторых пакетов на slim-образах
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    python3-dev \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код проекта
COPY . .

# Собираем статику (для web-контейнера)
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["gunicorn", "WERP_system.wsgi:application", "--bind", "0.0.0.0:8000"]