#!/usr/bin/env bash
# stop_all.sh - Detiene todos los componentes en la sede
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="$ROOT_DIR/.pids"

if [ ! -d "$PID_DIR" ]; then
  echo "No existe directorio de PIDs: $PID_DIR" >&2
  exit 1
fi

echo "== Deteniendo procesos =="
for pidfile in "$PID_DIR"/*.pid; do
  [ -e "$pidfile" ] || continue
  pid=$(cat "$pidfile" || true)
  name=$(basename "$pidfile" .pid)
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    echo "- $name (PID $pid) -> SIGTERM"
    kill "$pid" 2>/dev/null || true
    sleep 0.5
    if kill -0 "$pid" 2>/dev/null; then
      echo "  * SIGKILL forzado"
      kill -9 "$pid" 2>/dev/null || true
    fi
  else
    echo "- $name ya no está ejecutándose"
  fi
  rm -f "$pidfile"
fi

echo "Listo. Directorio $PID_DIR limpiado."
