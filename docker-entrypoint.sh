#!/bin/sh
set -e

echo "Waiting for database to be ready..."
while ! nc -z $SQL_HOST $SQL_PORT; do
  sleep 0.1
done
echo "Database is ready!"

python manage.py migrate --noinput
python manage.py compilemessages --ignore=.venv

if [ "$ENVIRONMENT" = "production" ]; then
    python manage.py collectstatic --noinput
fi

exec "$@"
