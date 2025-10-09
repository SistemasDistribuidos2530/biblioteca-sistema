# Makefile — biblioteca-sistema (GC + Actores)
# Universidad: Pontificia Universidad Javeriana
# Materia: Introducción a Sistemas Distribuidos
# Profesor: Rafael Páez Méndez
# Integrantes: Thomas Arévalo, Santiago Mesa, Diego Castrillón
# Fecha: 8 de octubre de 2025
#
# Uso rápido:
#   make help
#   make setup
#   make run-gc                     # inicia el Gestor de Carga (REP+PUB)
#   make run-actor-devolucion       # inicia actor de Devolución (foreground)
#   make run-actor-renovacion       # inicia actor de Renovación (foreground)
#   make start-actors               # inicia ambos actores en background y guarda PIDs
#   make stop-actors                # detiene actores iniciados en background
#   make ps-prueba                  # prueba local enviando 2 mensajes al GC
#   make logs                       # muestra últimas líneas de los logs de actores
#   make tail-logs                  # tail -f de los logs de actores
#   make check-ports                # verifica puertos 5555/5556 escuchando
#   make clean-logs                 # limpia logs de actores
#
# Notas:
# - Si existe .venv/, se usa su python/pip automáticamente.
# - El GC puede leer GC_REP_BIND y GC_PUB_BIND desde el entorno. Este Makefile
#   exporta estas variables al ejecutar gc.py (no se requiere python-dotenv).
# - Los actores están configurados para suscribirse a tcp://127.0.0.1:5556
#   (mismo host que el GC). Si mueves actores a otra máquina, edita sus .py.

SHELL := /bin/bash

# Detecta intérpretes preferidos (usa .venv si existe)
PY  := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else command -v python3; fi)
PIP := $(shell if [ -x .venv/bin/pip ]; then echo .venv/bin/pip; else command -v pip3 || echo pip; fi)

# Bind del GC (puedes override: make run-gc GC_REP_BIND=tcp://0.0.0.0:5555 GC_PUB_BIND=tcp://0.0.0.0:5556)
GC_REP_BIND ?= tcp://0.0.0.0:5555
GC_PUB_BIND ?= tcp://0.0.0.0:5556

# Directorio para PIDs (cuando actores corren en background)
PID_DIR := .pids
DEVO_PID := $(PID_DIR)/actor_devolucion.pid
RENO_PID := $(PID_DIR)/actor_renovacion.pid

.PHONY: help setup run-gc run-actor-devolucion run-actor-renovacion start-actors stop-actors ps-prueba logs tail-logs check-ports check-ip clean-logs _ensure-piddir

help:
	@echo ""
	@echo "=========================== HELP — biblioteca-sistema =========================="
	@echo "make setup                          # crea .venv e instala dependencias"
	@echo "make run-gc [GC_REP_BIND=.. GC_PUB_BIND=..]    # inicia el GC (REP+PUB)"
	@echo "make run-actor-devolucion           # inicia actor Devolución (foreground)"
	@echo "make run-actor-renovacion           # inicia actor Renovación (foreground)"
	@echo "make start-actors                   # inicia ambos actores en background"
	@echo "make stop-actors                    # detiene actores iniciados en background"
	@echo "make ps-prueba                      # prueba local del GC con 2 mensajes"
	@echo "make logs                           # últimas líneas de logs de actores"
	@echo "make tail-logs                      # tail -f de logs de actores"
	@echo "make check-ports                    # verifica puertos 5555/5556 escuchando"
	@echo "make clean-logs                     # limpia logs de actores"
	@echo "==============================================================================="
	@echo ""

setup:
	@echo ">> Creando entorno virtual (.venv) si no existe..."
	@if [ ! -d .venv ]; then python3 -m venv .venv; fi
	@echo ">> Instalando dependencias..."
	@$(PIP) install --upgrade pip
	@($(PIP) install -r requirements.txt) || ($(PIP) install pyzmq python-dotenv)
	@echo ">> Listo. Usa: source .venv/bin/activate"

run-gc:
	@echo ">> Iniciando GC (REP=$(GC_REP_BIND)  PUB=$(GC_PUB_BIND))"
	@GC_REP_BIND=$(GC_REP_BIND) GC_PUB_BIND=$(GC_PUB_BIND) $(PY) gc/gc.py

run-actor-devolucion:
	@echo ">> Iniciando Actor Devolucion (foreground)"
	@$(PY) actores/actor_devolucion.py

run-actor-renovacion:
	@echo ">> Iniciando Actor Renovacion (foreground)"
	@$(PY) actores/actor_renovacion.py

_ensure-piddir:
	@mkdir -p $(PID_DIR)

start-actors: _ensure-piddir
	@echo ">> Iniciando actores en background..."
	@nohup $(PY) actores/actor_devolucion.py > actores/actor_devolucion.out 2>&1 & echo $$! > $(DEVO_PID)
	@nohup $(PY) actores/actor_renovacion.py > actores/actor_renovacion.out 2>&1 & echo $$! > $(RENO_PID)
	@echo ">> PIDs guardados en $(PID_DIR):"
	@echo "   - Devolucion : $$(cat $(DEVO_PID))"
	@echo "   - Renovacion : $$(cat $(RENO_PID))"

stop-actors:
	@echo ">> Deteniendo actores (si están corriendo)..."
	@if [ -f $(DEVO_PID) ]; then kill $$(cat $(DEVO_PID)) 2>/dev/null || true; rm -f $(DEVO_PID); echo ' - Devolucion: detenido'; else echo ' - Devolucion: no PID'; fi
	@if [ -f $(RENO_PID) ]; then kill $$(cat $(RENO_PID)) 2>/dev/null || true; rm -f $(RENO_PID); echo ' - Renovacion: detenido'; else echo ' - Renovacion: no PID'; fi

ps-prueba:
	@echo ">> Ejecutando prueba local (gc/ps_prueba.py)"
	@$(PY) gc/ps_prueba.py

logs:
	@echo ">> Últimas líneas de logs de actores:"
	@echo "--- actores/log_actor_devolucion.txt ---"; tail -n 10 actores/log_actor_devolucion.txt 2>/dev/null || echo "(aún sin log)"
	@echo "--- actores/log_actor_renovacion.txt ---"; tail -n 10 actores/log_actor_renovacion.txt 2>/dev/null || echo "(aún sin log)"

tail-logs:
	@echo ">> Tail de logs de actores (Ctrl+C para salir)"
	@tail -f actores/log_actor_devolucion.txt actores/log_actor_renovacion.txt

check-ports:
	@echo ">> Chequeando puertos 5555/5556 escuchando..."
	@ss -tulpen | grep -E ':5555|:5556' || netstat -tulpen | grep -E ':5555|:5556' || true

check-ip:
	@echo ">> IPs locales:"
	@hostname -I || true
	@ip -4 addr show | sed -n 's/^\\s*inet\\s\\+\\([0-9.]\\+\\).*/\\1/p'

clean-logs:
	@echo ">> Limpiando logs de actores..."
	@rm -f actores/log_actor_devolucion.txt actores/log_actor_renovacion.txt
