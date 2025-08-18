#!/bin/bash
#!/bin/bash
set -euo pipefail

# Функция для чтения секретов и проверки их существования
read_secret() {
  local secret_path="$1"
  if [ ! -f "$secret_path" ]; then
    echo "[entrypoint] ERROR: Secret file $secret_path not found!" >&2
    exit 1
  fi
  cat "$secret_path"
}

export BOT_TOKEN=$(cat /run/secrets/bot_token)
export POSTGRES_USER=$(cat /run/secrets/postgres_user)
export POSTGRES_PASSWORD=$(cat /run/secrets/postgres_password)
export POSTGRES_DB=$(cat /run/secrets/postgres_db)
export MAPBOX_TOKEN=$(cat /run/secrets/mapbox_token)

export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"





# Ждём доступности Postgres
echo "[entrypoint] Waiting for postgres..."
until pg_isready -h db -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB"; do
  >&2 echo "[entrypoint] Postgres is unavailable - sleeping"
  sleep 1
done
echo "[entrypoint] Postgres is ready"

# Логика запуска
case "${1:-}" in
  bot)
    exec python /bot/main.py
    ;;
  alembic)
    shift
    exec alembic "$@"
    ;;
  *)
    exec "$@"
    ;;
esac