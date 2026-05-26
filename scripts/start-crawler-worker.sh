#!/bin/sh
set -e

exec celery -A heuriva worker --loglevel=info --queues=crawler --concurrency=1
