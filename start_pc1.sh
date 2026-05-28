#!/usr/bin/env bash

for PORT in 5556; do
  PIDS=$(lsof -ti tcp:$PORT || true)
  if [ -n "$PIDS" ]; then
    kill $PIDS 2>/dev/null || true
    sleep 1
    PIDS=$(lsof -ti tcp:$PORT || true)
    [ -z "$PIDS" ] || kill -9 $PIDS 2>/dev/null || true
  fi
done

echo "Puertos de PC1 limpios"