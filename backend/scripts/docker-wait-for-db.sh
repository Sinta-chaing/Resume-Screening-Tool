#!/bin/sh
# Wait for PostgreSQL to accept connections before starting Django.
# Usage: wait-for-db [host] [port] [timeout_secs]
set -e

HOST="${DB_HOST:-db}"
PORT="${DB_PORT:-5432}"
TIMEOUT="${1:-60}"

i=0
until nc -z "$HOST" "$PORT" 2>/dev/null || [ "$i" -ge "$TIMEOUT" ]; do
    i=$((i + 1))
    echo "waiting for db $HOST:$PORT ($i/${TIMEOUT}s)..."
    sleep 1
done

if [ "$i" -ge "$TIMEOUT" ]; then
    echo "ERROR: database $HOST:$PORT not reachable after ${TIMEOUT}s" >&2
    exit 1
fi