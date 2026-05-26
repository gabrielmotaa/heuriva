#!/bin/sh
set -e

exec celery -A heuriva worker --loglevel=info --queues=celery
