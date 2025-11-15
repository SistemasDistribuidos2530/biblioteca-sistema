#!/usr/bin/env bash
# stop_all.sh - Detiene todos los componentes de la sede (GA, GC, actores, monitor)
# Uso: bash scripts/stop_all.sh
# Opcional: --dry-run para solo mostrar qué se haría.

set -euo pipefail

DRY_RUN=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="$ROOT_DIR/.pids"
LOG_PREFIX="[stop_all]"

if [[ ! -d "$PID_DIR" ]]; then
  echo "$LOG_PREFIX No existe directorio de PIDs: $PID_DIR" >&2
  exit 0
fi

shopt -s nullglob
PID_FILES=("$PID_DIR"/*.pid)
shopt -u nullglob

if (( ${#PID_FILES[@]} == 0 )); then
  echo "$LOG_PREFIX No hay archivos .pid en $PID_DIR (nada que detener)"
  exit 0
fi

echo "== Deteniendo procesos (${#PID_FILES[@]} encontrados) =="

# Tiempo máximo de espera por proceso tras SIGTERM (segundos)
MAX_WAIT=3

for pidfile in "${PID_FILES[@]}"; do
  name="$(basename "$pidfile" .pid)"
  raw_pid="$(cat "$pidfile" 2>/dev/null || true)"
  # Validar que sea número
  if [[ ! "$raw_pid" =~ ^[0-9]+$ ]]; then
    echo "- $name: PID inválido ('$raw_pid'), eliminando pidfile" >&2
    $DRY_RUN || rm -f "$pidfile"
    continue
  fi
  pid="$raw_pid"

  if ! kill -0 "$pid" 2>/dev/null; then
    echo "- $name (PID $pid) ya no está ejecutándose"
    $DRY_RUN || rm -f "$pidfile"
    continue
  fi

  echo "- $name (PID $pid) -> SIGTERM"
  if ! $DRY_RUN; then
    kill "$pid" 2>/dev/null || true
    # Esperar hasta MAX_WAIT o que termine
    waited=0
    while kill -0 "$pid" 2>/dev/null && (( waited < MAX_WAIT )); do
      sleep 0.5
      waited=$(( waited + 1 ))
    done
    if kill -0 "$pid" 2>/dev/null; then
      echo "  * SIGKILL forzado (PID $pid persiste tras ${MAX_WAIT}s)"
      kill -9 "$pid" 2>/dev/null || true
    else
      echo "  * Terminó limpiamente (${waited}s)"
    fi
    rm -f "$pidfile" 2>/dev/null || true
  else
    echo "  * DRY-RUN: no se envían señales"
  fi

  echo "  * pidfile eliminado: $(basename "$pidfile")"
done

echo "Listo. Directorio $PID_DIR limpio."
exit 0
