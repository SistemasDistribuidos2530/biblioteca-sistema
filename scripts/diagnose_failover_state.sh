#!/usr/bin/env bash
# diagnose_failover_state.sh - Diagnostica por qué el sistema está en "secondary"
# cuando el GA primario está corriendo

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          DIAGNÓSTICO DE ESTADO DE FAILOVER                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo

# 1. Verificar GA
echo -e "${YELLOW}[1/7] Verificando GA Primario...${NC}"
GA_PID=$(pgrep -f "ga/ga.py" | head -1 || echo "")
if [ -n "$GA_PID" ]; then
    echo -e "${GREEN}✓ GA corriendo (PID: $GA_PID)${NC}"

    # Ver si es primary o secondary
    GA_ROLE=$(ps aux | grep "$GA_PID" | grep -o "GA_ROLE=[a-z]*" || echo "GA_ROLE=desconocido")
    echo "  Rol detectado en proceso: $GA_ROLE"

    # Ver puerto
    GA_PORT=$(ss -tnlp 2>/dev/null | grep "$GA_PID" | grep -o ":[0-9]*" | head -1 || echo ":????")
    echo "  Puerto escuchando: $GA_PORT"

    if [[ "$GA_PORT" == ":6000" ]]; then
        echo -e "${GREEN}  ✓ Puerto 6000 (primary) correcto${NC}"
    elif [[ "$GA_PORT" == ":6001" ]]; then
        echo -e "${RED}  ✗ Puerto 6001 (secondary) - ¡Este es el problema!${NC}"
        echo -e "${YELLOW}    El GA está corriendo como SECONDARY, no PRIMARY${NC}"
    fi
else
    echo -e "${RED}✗ GA NO está corriendo${NC}"
fi
echo

# 2. Verificar archivo ga_activo.txt
echo -e "${YELLOW}[2/7] Verificando gc/ga_activo.txt...${NC}"
if [ -f "gc/ga_activo.txt" ]; then
    ESTADO=$(cat gc/ga_activo.txt)
    echo "  Contenido: '$ESTADO'"

    if [ "$ESTADO" = "primary" ]; then
        echo -e "${GREEN}  ✓ Estado correcto (primary)${NC}"
    else
        echo -e "${RED}  ✗ Estado incorrecto (debería ser 'primary')${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠ Archivo no existe${NC}"
fi
echo

# 3. Verificar Monitor de Failover
echo -e "${YELLOW}[3/7] Verificando Monitor de Failover...${NC}"
MONITOR_PID=$(pgrep -f "monitor_failover.py" || echo "")
if [ -n "$MONITOR_PID" ]; then
    echo -e "${GREEN}✓ Monitor corriendo (PID: $MONITOR_PID)${NC}"

    # Ver últimas líneas del log
    if [ -f "logs/monitor_failover.log" ]; then
        echo "  Últimas 5 líneas del log:"
        tail -5 logs/monitor_failover.log | sed 's/^/    /'
    fi
else
    echo -e "${RED}✗ Monitor NO está corriendo${NC}"
    echo -e "${YELLOW}  Sin monitor, el estado no se actualiza automáticamente${NC}"
fi
echo

# 4. Verificar conectividad al GA primario
echo -e "${YELLOW}[4/7] Verificando conectividad al GA en puerto 6000...${NC}"
if nc -z localhost 6000 2>/dev/null; then
    echo -e "${GREEN}✓ Puerto 6000 accesible${NC}"

    # Intentar ping/pong manual
    echo "  Intentando ping/pong..."
    PONG=$(echo "ping" | timeout 2 nc localhost 6000 2>/dev/null || echo "")
    if [[ "$PONG" == *"pong"* ]]; then
        echo -e "${GREEN}  ✓ GA responde correctamente a ping${NC}"
    else
        echo -e "${RED}  ✗ GA no responde 'pong' (respuesta: '$PONG')${NC}"
    fi
else
    echo -e "${RED}✗ Puerto 6000 NO accesible${NC}"
    echo -e "${YELLOW}  El GA no está escuchando en 6000 (puerto del primary)${NC}"
fi
echo

# 5. Ver variables de entorno del GA
echo -e "${YELLOW}[5/7] Variables de entorno del GA (si está corriendo)...${NC}"
if [ -n "$GA_PID" ]; then
    echo "  Buscando GA_ROLE en /proc/$GA_PID/environ..."
    GA_ENV_ROLE=$(tr '\0' '\n' < /proc/$GA_PID/environ 2>/dev/null | grep "^GA_ROLE=" || echo "GA_ROLE=no_definido")
    echo "  $GA_ENV_ROLE"

    if [[ "$GA_ENV_ROLE" == *"secondary"* ]]; then
        echo -e "${RED}  ✗ ¡PROBLEMA ENCONTRADO! El GA se lanzó con GA_ROLE=secondary${NC}"
        echo -e "${YELLOW}    Causa: start_site1.sh no estableció GA_ROLE=primary correctamente${NC}"
    fi
fi
echo

# 6. Verificar .env
echo -e "${YELLOW}[6/7] Verificando archivo .env...${NC}"
if [ -f ".env" ]; then
    GA_ROLE_ENV=$(grep "^GA_ROLE=" .env 2>/dev/null || echo "GA_ROLE=no_definido")
    echo "  $GA_ROLE_ENV"

    if [[ "$GA_ROLE_ENV" == *"secondary"* ]]; then
        echo -e "${RED}  ✗ ¡PROBLEMA! .env tiene GA_ROLE=secondary${NC}"
        echo -e "${YELLOW}    Solución: Cambiar a GA_ROLE=primary en .env${NC}"
    elif [[ "$GA_ROLE_ENV" == *"primary"* ]]; then
        echo -e "${GREEN}  ✓ .env correcto (GA_ROLE=primary)${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠ Archivo .env no existe${NC}"
fi
echo

# 7. Resumen y Recomendaciones
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                         DIAGNÓSTICO                                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo

PROBLEMA_ENCONTRADO=false

# Analizar resultados
if [ -n "$GA_PID" ]; then
    if [[ "$GA_PORT" == ":6001" ]]; then
        echo -e "${RED}❌ PROBLEMA: GA está en puerto 6001 (secondary) en lugar de 6000${NC}"
        PROBLEMA_ENCONTRADO=true
    fi

    GA_ENV_ROLE=$(tr '\0' '\n' < /proc/$GA_PID/environ 2>/dev/null | grep "^GA_ROLE=" || echo "")
    if [[ "$GA_ENV_ROLE" == *"secondary"* ]]; then
        echo -e "${RED}❌ PROBLEMA: GA se lanzó con GA_ROLE=secondary${NC}"
        PROBLEMA_ENCONTRADO=true
    fi
fi

if [ -f ".env" ]; then
    GA_ROLE_ENV=$(grep "^GA_ROLE=" .env 2>/dev/null || echo "")
    if [[ "$GA_ROLE_ENV" == *"secondary"* ]]; then
        echo -e "${RED}❌ PROBLEMA: .env tiene GA_ROLE=secondary${NC}"
        PROBLEMA_ENCONTRADO=true
    fi
fi

if [ -z "$MONITOR_PID" ]; then
    echo -e "${YELLOW}⚠️  ADVERTENCIA: Monitor no está corriendo (estado no se actualiza)${NC}"
fi

echo

if [ "$PROBLEMA_ENCONTRADO" = true ]; then
    echo -e "${YELLOW}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║                    SOLUCIÓN RECOMENDADA                            ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo "Ejecuta el script de reseteo completo:"
    echo
    echo -e "${GREEN}  bash scripts/reset_to_primary.sh${NC}"
    echo
    echo "Esto hará:"
    echo "  1. Detener todos los procesos"
    echo "  2. Corregir .env para GA_ROLE=primary"
    echo "  3. Limpiar ga_activo.txt"
    echo "  4. Reiniciar el sistema en modo primary"
    echo "  5. Esperar a que el monitor detecte el estado"
    echo
else
    echo -e "${GREEN}✓ No se encontraron problemas obvios${NC}"
    echo
    echo "Espera 15 segundos y verifica:"
    echo "  cat gc/ga_activo.txt"
    echo
    echo "Si sigue en 'secondary', usa el script de reseteo:"
    echo "  bash scripts/reset_to_primary.sh"
fi

