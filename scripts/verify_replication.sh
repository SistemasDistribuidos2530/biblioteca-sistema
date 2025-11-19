#!/usr/bin/env bash
# verify_replication.sh - Verifica sincronización entre GA primario y secundario
set -euo pipefail

M1_DIR="${1:-~/ProyectoDistribuidos/biblioteca-sistema}"
M2_DIR="${2:-~/Desktop/DistribuidosProyecto/biblioteca-sistema}"
SAMPLE_SIZE=5

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║            VERIFICACIÓN DE REPLICACIÓN M1 ↔ M2                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# 1. Verificar existencia de archivos
echo "[1/6] Verificando archivos..."
for role in primary secondary; do
    dir="$([[ $role == primary ]] && echo "$M1_DIR" || echo "$M2_DIR")"
    db="$dir/gc/ga_db_$role.pkl"
    wal="$dir/gc/ga_wal_$role.log"

    if [ -f "$db" ]; then
        echo "  ✓ $role DB: $db"
    else
        echo "  ✗ $role DB: NO EXISTE"
    fi

    if [ -f "$wal" ]; then
        lines=$(wc -l < "$wal" 2>/dev/null || echo 0)
        echo "  ✓ $role WAL: $wal ($lines líneas)"
    else
        echo "  ✗ $role WAL: NO EXISTE"
    fi
done

echo ""

# 2. Comparar tamaños de BD
echo "[2/6] Comparando tamaños de BD..."
python3 - <<'PY'
import pickle, sys, os

m1_db = sys.argv[1] + "/gc/ga_db_primary.pkl"
m2_db = sys.argv[2] + "/gc/ga_db_secondary.pkl"

try:
    db1 = pickle.load(open(m1_db, "rb"))
    print(f"  M1 (primary)  : {len(db1)} libros")
except Exception as e:
    print(f"  M1 (primary)  : ERROR - {e}")
    sys.exit(1)

try:
    db2 = pickle.load(open(m2_db, "rb"))
    print(f"  M2 (secondary): {len(db2)} libros")
except Exception as e:
    print(f"  M2 (secondary): ERROR - {e}")
    sys.exit(1)

if len(db1) == len(db2):
    print("  ✓ Mismo número de libros")
else:
    print(f"  ✗ DIFERENCIA: {abs(len(db1) - len(db2))} libros")
PY "$M1_DIR" "$M2_DIR"

echo ""

# 3. Comparar muestra de libros
echo "[3/6] Comparando muestra de $SAMPLE_SIZE libros..."
python3 - <<PY
import pickle, sys

m1_db = sys.argv[1] + "/gc/ga_db_primary.pkl"
m2_db = sys.argv[2] + "/gc/ga_db_secondary.pkl"
sample_size = int(sys.argv[3])

db1 = pickle.load(open(m1_db, "rb"))
db2 = pickle.load(open(m2_db, "rb"))

sample_keys = list(db1.keys())[:sample_size]

print(f"\n  {'Libro':<12} {'M1 avail':<10} {'M1 loans':<10} {'M2 avail':<10} {'M2 loans':<10} {'Match':<6}")
print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*6}")

mismatches = 0
for key in sample_keys:
    b1 = db1.get(key, {})
    b2 = db2.get(key, {})

    a1 = b1.get('available', 0)
    l1 = len(b1.get('loans', {}))
    a2 = b2.get('available', 0)
    l2 = len(b2.get('loans', {}))

    match = '✓' if (a1 == a2 and l1 == l2) else '✗'
    if match == '✗':
        mismatches += 1

    print(f"  {key:<12} {a1:<10} {l1:<10} {a2:<10} {l2:<10} {match:<6}")

print(f"\n  Desajustes: {mismatches}/{sample_size}")
if mismatches == 0:
    print("  ✓ Muestra sincronizada")
else:
    print(f"  ⚠ {mismatches} libros con diferencias")
PY "$M1_DIR" "$M2_DIR" "$SAMPLE_SIZE"

echo ""

# 4. Comparar últimas entradas WAL
echo "[4/6] Comparando últimas 3 entradas WAL..."
echo "  M1 (primary):"
tail -n 3 "$M1_DIR/gc/ga_wal_primary.log" 2>/dev/null | while read line; do
    op=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('op',{}).get('operacion','?') + ' ' + d.get('op',{}).get('book_code','?'))" 2>/dev/null || echo "parse error")
    echo "    - $op"
done || echo "    (vacío)"

echo "  M2 (secondary):"
tail -n 3 "$M2_DIR/gc/ga_wal_secondary.log" 2>/dev/null | while read line; do
    op=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('op',{}).get('operacion','?') + ' ' + d.get('op',{}).get('book_code','?'))" 2>/dev/null || echo "parse error")
    echo "    - $op"
done || echo "    (vacío)"

echo ""

# 5. Verificar logs REPL en M1 y M2
echo "[5/6] Verificando logs de replicación..."
repl_send=$(grep -c 'REPL SEND' "$M1_DIR/logs/ga_primary.log" 2>/dev/null || echo 0)
repl_recv=$(grep -c 'REPL RECV' "$M2_DIR/logs/ga_secondary.log" 2>/dev/null || echo 0)
repl_apply=$(grep -c 'REPL APPLY' "$M2_DIR/logs/ga_secondary.log" 2>/dev/null || echo 0)

echo "  M1 REPL SEND  : $repl_send operaciones enviadas"
echo "  M2 REPL RECV  : $repl_recv operaciones recibidas"
echo "  M2 REPL APPLY : $repl_apply operaciones aplicadas"

if [ "$repl_send" -gt 0 ] && [ "$repl_recv" -gt 0 ]; then
    ratio=$((repl_recv * 100 / repl_send))
    echo "  Tasa recepción: $ratio%"
    if [ "$ratio" -ge 95 ]; then
        echo "  ✓ Replicación activa y saludable"
    else
        echo "  ⚠ Pérdida de paquetes o lag significativo"
    fi
else
    if [ "$repl_send" -eq 0 ]; then
        echo "  ⚠ M1 no ha enviado replicaciones (sin operaciones de escritura)"
    else
        echo "  ✗ M2 no está recibiendo replicaciones"
    fi
fi

echo ""

# 6. Resumen
echo "[6/6] Resumen de diagnóstico..."
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                         DIAGNÓSTICO                                ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

if [ "$repl_recv" -gt 0 ] && [ "$repl_apply" -gt 0 ]; then
    echo "✅ REPLICACIÓN FUNCIONANDO"
    echo ""
    echo "  La replicación M1 → M2 está activa."
    echo "  Si hay diferencias en la muestra, pueden deberse a:"
    echo "    - BD inicial diferente (regenerar con mismo seed)"
    echo "    - Lag de replicación (normal, < 1s)"
    echo ""
else
    echo "⚠️  REPLICACIÓN NO DETECTADA"
    echo ""
    echo "  Posibles causas:"
    echo "    1. No se han generado operaciones de escritura todavía"
    echo "    2. Puerto 7001 bloqueado o GA_REPL_PUSH_ADDR incorrecto en M1"
    echo "    3. GA secundario no está escuchando en puerto 7001"
    echo ""
    echo "  Verificar:"
    echo "    - nc -vz 10.43.102.248 7001  (desde M1)"
    echo "    - ss -tnlp | grep 7001       (en M2)"
    echo "    - grep GA_REPL_PUSH_ADDR ~/ProyectoDistribuidos/biblioteca-sistema/.env"
    echo ""
fi

echo "Ejecutado: $(date)"
echo ""

