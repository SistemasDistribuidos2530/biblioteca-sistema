#!/usr/bin/env bash
# start_site2.sh - Arranca componentes de la Sede 2 (Secondary)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"
PID_DIR="$ROOT_DIR/.pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

export GA_ROLE=secondary
export GC_REP_BIND=${GC_REP_BIND:-tcp://0.0.0.0:5555}
export GC_PUB_BIND=${GC_PUB_BIND:-tcp://0.0.0.0:5556}
export GC_ACTOR_PRESTAMO=${GC_ACTOR_PRESTAMO:-tcp://localhost:5560}
export GA_PRIMARY_BIND=${GA_PRIMARY_BIND:-tcp://0.0.0.0:6000}
export GA_SECONDARY_BIND=${GA_SECONDARY_BIND:-tcp://0.0.0.0:6001}

echo "== Iniciando SEDE 2 (Secondary) =="

python3 ga/ga.py > "$LOG_DIR/ga_secondary.log" 2>&1 & echo $! > "$PID_DIR/ga_secondary.pid"
python3 gc/gc.py > "$LOG_DIR/gc_serial.log" 2>&1 & echo $! > "$PID_DIR/gc_serial.pid"
python3 gc/gc_multihilo.py > "$LOG_DIR/gc_multihilo.log" 2>&1 & echo $! > "$PID_DIR/gc_multihilo.pid"
python3 actores/actor_renovacion.py > "$LOG_DIR/actor_renovacion.log" 2>&1 & echo $! > "$PID_DIR/actor_renovacion.pid"
python3 actores/actor_devolucion.py > "$LOG_DIR/actor_devolucion.log" 2>&1 & echo $! > "$PID_DIR/actor_devolucion.pid"
python3 actores/actor_prestamo.py > "$LOG_DIR/actor_prestamo.log" 2>&1 & echo $! > "$PID_DIR/actor_prestamo.pid"
python3 gc/monitor_failover.py > "$LOG_DIR/monitor_failover.log" 2>&1 & echo $! > "$PID_DIR/monitor_failover.pid"

echo "Componentes iniciados. PIDs en $PID_DIR"
