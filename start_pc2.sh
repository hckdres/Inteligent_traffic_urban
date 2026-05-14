#!/usr/bin/env bash

for PORT in 5557 5560 5562 5565; do
  PIDS=$(lsof -ti tcp:$PORT || true)
  if [ -n "$PIDS" ]; then
    kill $PIDS 2>/dev/null || true
    sleep 1
    PIDS=$(lsof -ti tcp:$PORT || true)
    [ -z "$PIDS" ] || kill -9 $PIDS 2>/dev/null || true
  fi
done

echo "Puertos de PC2 limpios"