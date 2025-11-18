#!/usr/bin/env bash
# reset_to_primary.sh - Resetea el sistema completamente al estado PRIMARY
# Corrige problemas comunes de configuración y estado

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              RESETEO COMPLETO A ESTADO PRIMARY                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# FASE 1: Detener todo
echo -e "${YELLOW}[1/6] Deteniendo todos los procesos...${NC}"
bash scripts/stop_all.sh 2>/dev/null || true
sleep 1

# Forzar kill de cualquier Python que haya quedado
pkill -f "ga/ga.py" 2>/dev/null || true
pkill -f "gc/gc" 2>/dev/null || true
pkill -f "actores/actor_" 2>/dev/null || true
pkill -f "monitor_failover" 2>/dev/null || true
sleep 1

echo -e "${GREEN}✓ Procesos detenidos${NC}"
echo

# FASE 2: Limpiar estado
echo -e "${YELLOW}[2/6] Limpiando estado anterior...${NC}"
rm -rf .pids/* 2>/dev/null || true
rm -f gc/ga_activo.txt 2>/dev/null || true
rm -f gc/ga_db_*.pkl.lock 2>/dev/null || true
echo -e "${GREEN}✓ Estado limpiado${NC}"
echo

# FASE 3: Verificar y corregir .env
echo -e "${YELLOW}[3/6] Verificando configuración .env...${NC}"

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}  .env no existe, creando desde .env.example...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        echo -e "${RED}  ✗ .env.example no existe${NC}"
        exit 1
    fi
fi

# Asegurar GA_ROLE=primary
if grep -q "^GA_ROLE=" .env; then
    # Cambiar a primary si está en otra cosa
    sed -i 's/^GA_ROLE=.*/GA_ROLE=primary/' .env
    echo -e "${GREEN}✓ GA_ROLE=primary configurado en .env${NC}"
else
    # Añadir si no existe
    echo "GA_ROLE=primary" >> .env
    echo -e "${GREEN}✓ GA_ROLE=primary añadido a .env${NC}"
fi

# Verificar otros valores críticos
if ! grep -q "^GA_PRIMARY_BIND=" .env; then
    echo "GA_PRIMARY_BIND=tcp://0.0.0.0:6000" >> .env
fi

if ! grep -q "^GA_SECONDARY_BIND=" .env; then
    echo "GA_SECONDARY_BIND=tcp://0.0.0.0:6001" >> .env
fi

# Mostrar configuración relevante
echo "  Configuración actual:"
grep -E "^(GA_ROLE|GA_PRIMARY_BIND|GA_SECONDARY_BIND)=" .env | sed 's/^/    /'
echo

# FASE 4: Arrancar el sistema
echo -e "${YELLOW}[4/6] Arrancando sistema en modo PRIMARY...${NC}"

# Forzar variables de entorno para este arranque
export GA_ROLE=primary
export GA_PRIMARY_BIND=tcp://0.0.0.0:6000
export GA_SECONDARY_BIND=tcp://0.0.0.0:6001
# Direcciones para monitor en M1 (primary local, secondary en M2)
export GA_PRIMARY_ADDR=tcp://localhost:6000
export GA_SECONDARY_ADDR=tcp://10.43.102.248:6001

bash scripts/start_site1.sh
echo -e "${GREEN}✓ Sistema iniciado${NC}"
echo

# FASE 5: Verificar que todo está arriba
echo -e "${YELLOW}[5/6] Verificando componentes...${NC}"
sleep 3

# Verificar GA
GA_PID=$(pgrep -f "ga/ga.py" | head -1 || echo "")
if [ -n "$GA_PID" ]; then
    echo -e "${GREEN}✓ GA corriendo (PID: $GA_PID)${NC}"

    # Verificar puerto
    if ss -tnlp 2>/dev/null | grep "$GA_PID" | grep -q ":6000"; then
        echo -e "${GREEN}✓ GA escuchando en puerto 6000 (PRIMARY)${NC}"
    else
        echo -e "${RED}✗ GA NO está en puerto 6000${NC}"
    fi
else
    echo -e "${RED}✗ GA no está corriendo${NC}"
fi

# Verificar GC
if pgrep -f "gc/gc" > /dev/null; then
    echo -e "${GREEN}✓ GC corriendo${NC}"
else
    echo -e "${RED}✗ GC no está corriendo${NC}"
fi

# Verificar actores
ACTORES_COUNT=$(pgrep -f "actores/actor_" | wc -l)
echo -e "${GREEN}✓ $ACTORES_COUNT actores corriendo${NC}"

# Verificar monitor
if pgrep -f "monitor_failover" > /dev/null; then
    echo -e "${GREEN}✓ Monitor de failover corriendo${NC}"
else
    echo -e "${YELLOW}⚠ Monitor no está corriendo${NC}"
fi

echo

# FASE 6: Esperar a que el monitor actualice el estado
echo -e "${YELLOW}[6/6] Esperando a que el monitor detecte el estado PRIMARY...${NC}"
echo "  (Esperando 15 segundos para heartbeats...)"

for i in {1..15}; do
    sleep 1
    echo -n "."

    # Verificar si ya cambió a primary
    if [ -f "gc/ga_activo.txt" ]; then
        ESTADO=$(cat gc/ga_activo.txt)
        if [ "$ESTADO" = "primary" ]; then
            echo
            echo -e "${GREEN}✓ Estado detectado: primary (después de ${i}s)${NC}"
            break
        fi
    fi
done
echo

# VERIFICACIÓN FINAL
echo
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                     VERIFICACIÓN FINAL                             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo

# Estado final
if [ -f "gc/ga_activo.txt" ]; then
    ESTADO_FINAL=$(cat gc/ga_activo.txt)
    if [ "$ESTADO_FINAL" = "primary" ]; then
        echo -e "${GREEN}✓✓✓ ESTADO: primary${NC}"
    else
        echo -e "${YELLOW}⚠ ESTADO: $ESTADO_FINAL (esperado: primary)${NC}"
        echo
        echo "El monitor puede tardar hasta 3 ciclos de ping (6s) en actualizar."
        echo "Espera otros 10 segundos y verifica:"
        echo "  cat gc/ga_activo.txt"
    fi
else
    echo -e "${YELLOW}⚠ gc/ga_activo.txt no existe aún${NC}"
    echo "El monitor lo creará en los próximos segundos."
fi

# Puertos
echo
echo "Puertos escuchando:"
ss -tnlp 2>/dev/null | grep -E ':(5555|5556|6000)' | awk '{print "  " $4}' || echo "  (ninguno detectado con ss)"

# Procesos
echo
echo "Procesos corriendo:"
echo "  GA: $(pgrep -f 'ga/ga.py' | wc -l)"
echo "  GC: $(pgrep -f 'gc/gc' | wc -l)"
echo "  Actores: $(pgrep -f 'actores/actor_' | wc -l)"
echo "  Monitor: $(pgrep -f 'monitor_failover' | wc -l)"

echo
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  RESETEO COMPLETADO                                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo
echo "Siguiente paso:"
echo "  1. Espera 5-10 segundos más"
echo "  2. Verifica el estado:"
echo -e "${BLUE}     cat gc/ga_activo.txt${NC}"
echo "  3. Debe decir: primary"
echo
echo "Si sigue en 'secondary', revisa los logs del monitor:"
echo -e "${BLUE}     tail -20 logs/monitor_failover.log${NC}"
echo
echo "Luego, ejecuta la demo de failover:"
echo -e "${BLUE}     bash scripts/failover_demo.sh${NC}"
echo

