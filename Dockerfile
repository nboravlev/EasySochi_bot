FROM postgres:15

# Устанавливаем необходимые расширения
RUN apt-get update && apt-get install -y \
    postgresql-15-cron \
    postgresql-15-postgis-3 \
    postgresql-15-postgis-3-scripts \
    && rm -rf /var/lib/apt/lists/*

# Копируем postgresql.conf (при необходимости ты можешь монтировать его через volume)
COPY postgresql.conf /etc/postgresql/postgresql.conf

# Копируем SQL-скрипт инициализации (выполняется при первом запуске контейнера)
COPY init-pg.sql /docker-entrypoint-initdb.d/
