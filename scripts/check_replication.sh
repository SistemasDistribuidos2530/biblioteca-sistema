#!/usr/bin/env bash
set -euo pipefail
PRIMARY_DIR="$1"
SECONDARY_DIR="$2"
echo "[*] Últimas 3 líneas WAL primario:"
tail -n3 "$PRIMARY_DIR/gc/ga_wal_primary.log" || true
echo "[*] Últimas 3 líneas WAL secundario:"
tail -n3 "$SECONDARY_DIR/gc/ga_wal_secondary.log" || true
