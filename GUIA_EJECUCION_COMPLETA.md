# 🎯 GUÍA COMPLETA DE EJECUCIÓN - SISTEMA BIBLIOTECA DISTRIBUIDA

**Proyecto:** Sistema Distribuido de Gestión de Biblioteca  
**Universidad:** Pontificia Universidad Javeriana  
**Materia:** Sistemas Distribuidos  
**Fecha:** Noviembre 2025

---

## 📋 TABLA DE CONTENIDOS

1. [Pre-requisitos](#pre-requisitos)
2. [Paso 1: Reseteo Completo del Sistema](#paso-1-reseteo-completo-del-sistema)
3. [Paso 2: Inicio del Sistema y Pruebas de Funcionamiento](#paso-2-inicio-del-sistema-y-pruebas-de-funcionamiento)
4. [Paso 3: Ejecución de Experimentos de Carga](#paso-3-ejecución-de-experimentos-de-carga)
5. [Paso 4: Prueba de Failover (Conmutación GA Primary → Secondary)](#paso-4-prueba-de-failover)
6. [Paso 5: Uso de BD Secundaria tras Falla del Primario](#paso-5-uso-de-bd-secundaria)
7. [Paso 6: Recuperación del GA Primario](#paso-6-recuperación-del-ga-primario)
8. [Paso 7: Detención del Sistema](#paso-7-detención-del-sistema)
9. [Verificación de Resultados](#verificación-de-resultados)
10. [Troubleshooting](#troubleshooting)

---

## PRE-REQUISITOS

### Máquinas y Roles

| Máquina | Rol | IP | Componentes |
|---------|-----|-----|-------------|
| **M1** | Sede 1 (Primary) | 10.43.101.220 | GA primario (6000), GC (5555/5556), Actores, Monitor |
| **M2** | Sede 2 (Secondary) | 10.43.102.248 | GA secundario (6001), GC (5555/5556), Actores, Monitor |
| **M3** | Clientes | 10.43.102.38 | Procesos Solicitantes (PS) |

### Verificación de Conectividad

Desde **M3**:
```bash
nc -vz 10.43.101.220 5555   # GC Sede 1
nc -vz 10.43.102.248 5555   # GC Sede 2
```

Desde **M1**:
```bash
nc -vz 10.43.102.248 7001   # GA Secondary PULL
nc -vz 10.43.102.248 6001   # GA Secondary REP
```

**Esperado:** Todos deben responder "succeeded"

---

## PASO 1: RESETEO COMPLETO DEL SISTEMA

**Objetivo:** Limpiar logs, bases de datos, WAL, PIDs y estado de failover para comenzar desde cero.

### M1 - Sede 1 (Primary)

```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema

# Detener todos los procesos
bash scripts/stop_all.sh

# Limpiar logs y estado
rm -rf logs/*
rm -rf .pids/*
rm -f gc/ga_activo.txt
rm -f gc/ga_db_*.pkl
rm -f gc/ga_wal_*.log

# Limpiar evidencias de failover anteriores (opcional)
rm -rf evidencias_failover/*

echo "✓ M1 limpio y listo"
```

### M2 - Sede 2 (Secondary)

```bash
cd ~/Desktop/DistribuidosProyecto/biblioteca-sistema

# Detener todos los procesos
bash scripts/stop_all.sh

# Limpiar logs y estado
rm -rf logs/*
rm -rf .pids/*
rm -f gc/ga_activo.txt
rm -f gc/ga_db_*.pkl
rm -f gc/ga_wal_*.log

echo "✓ M2 limpio y listo"
```

### M3 - Clientes

```bash
cd ~/biblioteca-clientes

# Limpiar logs y resultados anteriores
rm -rf logs/*
rm -rf multi_ps_logs/*
rm -rf experimentos/*
rm -f solicitudes*.bin
rm -f ps_logs*.txt

echo "✓ M3 limpio y listo"
```

---

## PASO 2: INICIO DEL SISTEMA Y PRUEBAS DE FUNCIONAMIENTO

**Objetivo:** Arrancar todos los componentes y verificar comunicación mediante una carga de prueba.

### 2.1. Arrancar M1 (Sede 1 - Primary)

**Terminal M1-T1:**
```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema
bash scripts/start_site1.sh
```

**Salida esperada:**
```
== Iniciando SEDE 1 (Primary) ==
[INFO] GA_REPL_PUSH_ADDR=tcp://10.43.102.248:7001
Componentes iniciados. PIDs en .../ProyectoDistribuidos/biblioteca-sistema/.pids
```

**Verificar puertos:**
```bash
ss -tnlp | grep -E ':5555|:5556|:6000'
```

**Esperado:** 3 líneas LISTEN (5555, 5556, 6000)

**Verificar estado GA:**
```bash
sleep 5
cat gc/ga_activo.txt
```

**Esperado:** `primary`

---

### 2.2. Arrancar M2 (Sede 2 - Secondary)

**Terminal M2-T1:**
```bash
cd ~/Desktop/DistribuidosProyecto/biblioteca-sistema
bash scripts/start_site2.sh
```

**Salida esperada:**
```
== Iniciando SEDE 2 (Secondary) ==
[INFO] GA_REPL_PULL_BIND=tcp://0.0.0.0:7001
Componentes iniciados. PIDs en .../biblioteca-sistema/.pids
```

**Verificar puertos:**
```bash
ss -tnlp | grep -E ':5555|:5556|:6001|:7001'
```

**Esperado:** 4 líneas LISTEN (5555, 5556, 6001, 7001)

---

### 2.3. Verificar Monitor de Failover (M1)

**Terminal M1-T2 (nueva terminal):**
```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema
tail -f logs/monitor_failover.log
```

**Esperado (cada ~2 segundos):**
```
[TIMESTAMP] Intentando ping a tcp://localhost:6000
[TIMESTAMP] Pong recibido desde tcp://localhost:6000
```

**Dejar corriendo para monitoreo continuo.**

---

### 2.4. Generar Carga de Prueba (M3)

**Objetivo:** Enviar solicitudes para verificar que el sistema procesa operaciones y replica a M2.

**Terminal M3-T1:**
```bash
cd ~/biblioteca-clientes

# Generar carga de prueba: 2 PS con 10 solicitudes cada uno
python3 pruebas/multi_ps.py --num-ps 2 --requests-per-ps 10 --mix 50:50:0
```

**Salida esperada:**
```
========================================================================
                 LANZADOR DE MÚLTIPLES PS CONCURRENTES                  
========================================================================

[...] PS lanzados         : 2
[...] PS exitosos         : 2
[...] Total solicitudes   : 20
```

---

### 2.5. Verificar Procesamiento en Tiempo Real

**Terminal M1-T3 (nueva terminal - Logs de Actores):**
```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema

# Ver procesamiento de renovaciones
tail -f logs/actor_renovacion.log | grep -E 'RENOVACIÓN PROCESADA|book_code'
```

**Esperado:** Verás bloques como:
```
------------------------------------------------------------------------
                          RENOVACIÓN PROCESADA                          
------------------------------------------------------------------------
  Operación   : renovacion
  Usuario     : XX
  Libro       : BOOK-XXX
  [...]
```

**Terminal M1-T4 (nueva terminal - Replicación):**
```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema
tail -f logs/ga_primary.log | grep 'REPL SEND'
```

**Esperado:**
```
[TIMESTAMP] REPL SEND -> renovacion book=BOOK-XXX user=YY to tcp://10.43.102.248:7001
[TIMESTAMP] REPL SEND -> devolucion book=BOOK-ZZZ user=WW to tcp://10.43.102.248:7001
```

**Terminal M2-T2 (nueva terminal - Recepción Replicación):**
```bash
cd ~/Desktop/DistribuidosProyecto/biblioteca-sistema
tail -f logs/ga_secondary.log | grep -E 'REPL RECV|REPL APPLY'
```

**Esperado:**
```
[TIMESTAMP] REPL RECV raw -> {"ts": "...", "op": {...}}
[TIMESTAMP] REPL APPLY -> renovacion book=BOOK-XXX user=YY
```

---

### 2.6. Verificar Sincronización de BD

**Comparar estados de BD entre M1 y M2:**

**Terminal M1:**
```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema
python3 - <<'PY'
import pickle
db=pickle.load(open('gc/ga_db_primary.pkl','rb'))
sample=list(db.items())[:3]
for k,v in sample:
    print(f"{k}: available={v.get('available')}, loans={len(v.get('loans',{}))}")
PY
```

**Terminal M2:**
```bash
cd ~/Desktop/DistribuidosProyecto/biblioteca-sistema
python3 - <<'PY'
import pickle
db=pickle.load(open('gc/ga_db_secondary.pkl','rb'))
sample=list(db.items())[:3]
for k,v in sample:
    print(f"{k}: available={v.get('available')}, loans={len(v.get('loans',{}))}")
PY
```

**Esperado:** Los valores de `available` y `loans` deben coincidir entre M1 y M2.

**Verificar WAL:**
```bash
# M1
tail -n 5 ~/ProyectoDistribuidos/biblioteca-sistema/gc/ga_wal_primary.log

# M2
tail -n 5 ~/Desktop/DistribuidosProyecto/biblioteca-sistema/gc/ga_wal_secondary.log
```

**Esperado:** Ambos WAL deben contener entradas JSON similares.

---

## PASO 3: EJECUCIÓN DE EXPERIMENTOS DE CARGA

**Objetivo:** Ejecutar escenarios automatizados (4, 6, 10 PS) y recolectar métricas.

### 3.1. Ejecutar Script de Experimentos

**Terminal M3-T1:**
```bash
cd ~/biblioteca-clientes
bash scripts/run_experiments.sh
```

**Duración:** ~1-2 minutos

**Salida esperada:**
```
[OK] Conectividad al GC (tcp://10.43.101.220:5555) verificada.
== Ejecutando experimentos de carga ==
-- Escenario: 4 PS --
[...]
Escenario 4ps completado

-- Escenario: 6 PS --
[...]
Escenario 6ps completado

-- Escenario: 10 PS --
[...]
Escenario 10ps completado

== Consolidando métricas ==
Listo. Resultados en /home/estudiante/biblioteca-clientes/experimentos
```

---

### 3.2. Consultar Resultados

**Listar archivos generados:**
```bash
ls -lh experimentos/
```

**Esperado:**
```
experimento_carga.md
experimento_carga.csv
experimento_carga.json
metricas_4ps.csv
metricas_6ps.csv
metricas_10ps.csv
ps_logs_4ps.txt
ps_logs_6ps.txt
ps_logs_10ps.txt
[...]
```

**Ver tabla comparativa:**
```bash
cat experimentos/experimento_carga.md
```

**Esperado (ejemplo):**
```markdown
| Escenario | Total | OK | ERROR | TIMEOUT | TPS | Lat Media | Lat p95 |
|-----------|-------|----|----|---------|-----|-----------|---------|
| 4ps       | 100   | 98 | 0  | 2       | 85  | 0.12s     | 0.25s   |
| 6ps       | 150   | 145| 0  | 5       | 120 | 0.15s     | 0.35s   |
| 10ps      | 250   | 240| 0  | 10      | 180 | 0.18s     | 0.45s   |
```

**Ver métricas detalladas de un escenario:**
```bash
head -20 experimentos/metricas_4ps.csv
```

---

## PASO 4: PRUEBA DE FAILOVER

**Objetivo:** Simular caída del GA primario, observar detección automática y conmutación al GA secundario.

### 4.1. Monitorear Estado Pre-Failover

**Terminal M1-T2 (Monitor):** Debe seguir mostrando ping/pong exitoso.

**Terminal M1-T5 (nueva terminal - Estado GA):**
```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema
watch -n 1 cat gc/ga_activo.txt
```

**Esperado:** `primary` (actualización cada segundo)

---

### 4.2. Obtener PID del GA Primario

**Terminal M1:**
```bash
pgrep -f ga/ga.py | head -1
```

**Anotar el PID (ejemplo: 123456)**

---

### 4.3. Simular Caída del GA Primario

**Terminal M1:**
```bash
# Reemplazar 123456 con el PID real
kill -9 123456

# Confirmar
pgrep -f ga/ga.py || echo "GA detenido"
```

---

### 4.4. Observar Detección y Conmutación

**Terminal M1-T2 (Monitor):** Verás secuencia de timeouts y conmutación:
```
[TIMESTAMP] Intentando ping a tcp://localhost:6000
[TIMESTAMP] Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
[TIMESTAMP] Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
[...] (3 fallos consecutivos)
[TIMESTAMP] Estado GA actualizado a 'secondary'
[TIMESTAMP] GA primario no responde, conmutando a secundario (tcp://10.43.102.248:6001)
```

**Terminal M1-T5 (watch ga_activo.txt):** Cambiará de `primary` → `secondary`

**Medir MTTD (Mean Time To Detect):**
- Tiempo entre el kill y la línea "Estado GA actualizado a 'secondary'"
- Típicamente: 6-15 segundos (dependiendo de PING_INTERVAL y FAILURE_THRESHOLD)

---

### 4.5. Verificar Logs de Detección

**Terminal M1:**
```bash
grep -E "conmutando|actualizado" logs/monitor_failover.log | tail -5
```

**Esperado:**
```
[TIMESTAMP] GA primario no responde, conmutando a secundario (tcp://10.43.102.248:6001)
[TIMESTAMP] Estado GA actualizado a 'secondary'
```

---

## PASO 5: USO DE BD SECUNDARIA TRAS FALLA

**Objetivo:** Demostrar que el sistema sigue operativo usando el GA secundario en M2.

### 5.1. Generar Carga Durante Failover

**Terminal M3-T1:**
```bash
cd ~/biblioteca-clientes

# Carga de prueba contra sistema en modo secondary
python3 pruebas/multi_ps.py --num-ps 2 --requests-per-ps 15 --mix 40:40:20
```

**Salida esperada:**
```
PS lanzados         : 2
PS exitosos         : 2
Total solicitudes   : 30
```

**Nota:** Puede haber algunos TIMEOUT durante la ventana de MTTD (esperado).

---

### 5.2. Verificar Procesamiento en GA Secundario (M2)

**Terminal M2-T3 (nueva terminal):**
```bash
cd ~/Desktop/DistribuidosProyecto/biblioteca-sistema
tail -f logs/ga_secondary.log | grep 'REP recibido'
```

**Esperado:** Verás mensajes JSON de operaciones (no solo pings):
```
[TIMESTAMP] REP recibido: {"operacion": "renovacion", "book_code": "BOOK-XXX", ...}
[TIMESTAMP] REP recibido: {"operacion": "devolucion", "book_code": "BOOK-YYY", ...}
```

---

### 5.3. Verificar Actualización de BD Secundaria

**Terminal M2:**
```bash
cd ~/Desktop/DistribuidosProyecto/biblioteca-sistema

# Antes de la carga
python3 - <<'PY'
import pickle
db=pickle.load(open('gc/ga_db_secondary.pkl','rb'))
print("BOOK-001 antes:", db.get('BOOK-001',{}).get('available'))
PY

# Esperar a que termine la carga

# Después de la carga
python3 - <<'PY'
import pickle
db=pickle.load(open('gc/ga_db_secondary.pkl','rb'))
print("BOOK-001 después:", db.get('BOOK-001',{}).get('available'))
PY
```

**Esperado:** Los valores de `available` deben cambiar reflejando las operaciones procesadas.

**Verificar WAL secundario:**
```bash
tail -n 10 gc/ga_wal_secondary.log
```

**Esperado:** Nuevas entradas JSON con las operaciones recién procesadas.

---

### 5.4. Verificar Métricas de Clientes

**Terminal M3:**
```bash
grep -c 'status=OK' multi_ps_logs/ps_logs_consolidado.txt
grep -c 'status=TIMEOUT' multi_ps_logs/ps_logs_consolidado.txt
```

**Interpretación:**
- **OK > 0:** Sistema procesando solicitudes contra GA secundario.
- **TIMEOUT:** Algunos pueden ocurrir durante la ventana de detección (MTTD).

---

## PASO 6: RECUPERACIÓN DEL GA PRIMARIO

**Objetivo:** Reiniciar el GA primario y verificar que el monitor conmuta de vuelta a primary.

### 6.1. Reiniciar GA Primario (M1)

**Terminal M1:**
```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema

# Relanzar solo el GA (sin tocar GC/Actores)
export GA_ROLE=primary
export GA_REPL_PUSH_ADDR=tcp://10.43.102.248:7001
python3 ga/ga.py > logs/ga_primary.log 2>&1 & echo $! > .pids/ga_primary.pid

echo "GA primario reiniciado"
```

---

### 6.2. Observar Restauración Automática

**Terminal M1-T2 (Monitor):** Verás el monitor detectar que el primario volvió:
```
[TIMESTAMP] Intentando ping a tcp://localhost:6000
[TIMESTAMP] Pong recibido desde tcp://localhost:6000
[TIMESTAMP] GA primario restaurado, regresando a modo normal
[TIMESTAMP] Estado GA actualizado a 'primary'
```

**Terminal M1-T5 (watch ga_activo.txt):** Cambiará de `secondary` → `primary`

---

### 6.3. Generar Carga de Validación

**Terminal M3-T1:**
```bash
cd ~/biblioteca-clientes

# Carga final para confirmar operación normal
python3 pruebas/multi_ps.py --num-ps 2 --requests-per-ps 10 --mix 50:50:0
```

**Salida esperada:**
```
PS exitosos         : 2
Total solicitudes   : 20
```

---

### 6.4. Verificar Replicación Restaurada

**Terminal M1-T4 (REPL SEND):** Debe volver a mostrar:
```
[TIMESTAMP] REPL SEND -> renovacion book=BOOK-XXX user=YY to tcp://10.43.102.248:7001
```

**Terminal M2-T2 (REPL RECV):** Debe volver a mostrar:
```
[TIMESTAMP] REPL RECV raw -> {"ts": "...", "op": {...}}
[TIMESTAMP] REPL APPLY -> renovacion book=BOOK-XXX user=YY
```

---

### 6.5. Comparar BD Final

**Terminal M1:**
```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema
python3 - <<'PY'
import pickle
db=pickle.load(open('gc/ga_db_primary.pkl','rb'))
print("Primary BOOK-050:", db.get('BOOK-050',{}).get('available'))
PY
```

**Terminal M2:**
```bash
cd ~/Desktop/DistribuidosProyecto/biblioteca-sistema
python3 - <<'PY'
import pickle
db=pickle.load(open('gc/ga_db_secondary.pkl','rb'))
print("Secondary BOOK-050:", db.get('BOOK-050',{}).get('available'))
PY
```

**Esperado:** Valores idénticos (sincronización restaurada).

---

## PASO 7: DETENCIÓN DEL SISTEMA

**Objetivo:** Detener todos los procesos manteniendo logs y evidencias para análisis.

### 7.1. Detener M3 (Clientes)

**Terminal M3:**
```bash
cd ~/biblioteca-clientes

# No hay procesos en background que detener si multi_ps ya terminó
# Si tienes scripts corriendo, Ctrl+C en las terminales

echo "✓ M3 detenido (logs preservados)"
```

---

### 7.2. Detener M1 (Sede 1)

**Terminal M1:**
```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema
bash scripts/stop_all.sh
```

**Salida esperada:**
```
== Deteniendo procesos (7 encontrados) ==
- actor_devolucion (PID XXXXX) -> SIGTERM
  * Terminó limpiamente (Xs)
[...]
Listo. Directorio .pids limpio.
```

**Logs preservados en:**
- `logs/ga_primary.log`
- `logs/gc_multihilo.log`
- `logs/actor_*.log`
- `logs/monitor_failover.log`
- `gc/ga_db_primary.pkl`
- `gc/ga_wal_primary.log`
- `gc/ga_activo.txt`

---

### 7.3. Detener M2 (Sede 2)

**Terminal M2:**
```bash
cd ~/Desktop/DistribuidosProyecto/biblioteca-sistema
bash scripts/stop_all.sh
```

**Logs preservados en:**
- `logs/ga_secondary.log`
- `logs/gc_multihilo.log`
- `logs/actor_*.log`
- `logs/monitor_failover.log`
- `gc/ga_db_secondary.pkl`
- `gc/ga_wal_secondary.log`

---

## VERIFICACIÓN DE RESULTADOS

### Métricas de Experimentos (M3)

**Ubicación:** `~/biblioteca-clientes/experimentos/`

**Archivos clave:**
```bash
cd ~/biblioteca-clientes/experimentos

# Tabla comparativa Markdown
cat experimento_carga.md

# Métricas CSV por escenario
head -20 metricas_4ps.csv
head -20 metricas_6ps.csv
head -20 metricas_10ps.csv

# Logs completos de solicitudes
wc -l ps_logs_*.txt
```

---

### Evidencias de Failover

**Si usaste `failover_demo.sh` (opcional):**
```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema/evidencias_failover
cat REPORTE_FAILOVER.md
```

**Datos clave:**
- **MTTD:** Tiempo de detección (segundos)
- **Estados:** PRE (primary) → DURANTE (secondary) → POST (secondary o primary si restauraste)
- **Impacto:** Total solicitudes, OK, TIMEOUT, ERROR

**Si hiciste failover manual:**
```bash
# M1
grep -E "conmutando|actualizado" logs/monitor_failover.log

# Calcular MTTD manualmente:
# Timestamp de kill - Timestamp de "Estado GA actualizado a 'secondary'"
```

---

### Logs de Operaciones

**M1 - Operaciones procesadas:**
```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema
grep -c 'REP recibido:.*operacion' logs/ga_primary.log
```

**M1 - Replicaciones enviadas:**
```bash
grep -c 'REPL SEND' logs/ga_primary.log
```

**M2 - Replicaciones recibidas:**
```bash
cd ~/Desktop/DistribuidosProyecto/biblioteca-sistema
grep -c 'REPL RECV' logs/ga_secondary.log
```

**M2 - Operaciones directas (durante failover):**
```bash
grep -c 'REP recibido:.*operacion' logs/ga_secondary.log
```

---

### Estado Final de BD

**M1:**
```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema
python3 - <<'PY'
import pickle
db=pickle.load(open('gc/ga_db_primary.pkl','rb'))
print(f"Total libros: {len(db)}")
total_loans = sum(len(v.get('loans',{})) for v in db.values())
print(f"Préstamos activos: {total_loans}")
PY
```

**M2:**
```bash
cd ~/Desktop/DistribuidosProyecto/biblioteca-sistema
python3 - <<'PY'
import pickle
db=pickle.load(open('gc/ga_db_secondary.pkl','rb'))
print(f"Total libros: {len(db)}")
total_loans = sum(len(v.get('loans',{})) for v in db.values())
print(f"Préstamos activos: {total_loans}")
PY
```

**Esperado:** Valores idénticos (sincronización completa).

---

## TROUBLESHOOTING

### Problema: ga_activo.txt dice "secondary" pero GA primario está arriba

**Causa:** Monitor no detecta el GA o tarda en conmutar.

**Solución:**
```bash
# M1
cd ~/ProyectoDistribuidos/biblioteca-sistema

# Verificar que GA está escuchando
ss -tnlp | grep 6000

# Ver logs del monitor
tail -20 logs/monitor_failover.log

# Si no hay ping/pong, reiniciar monitor
pkill -f monitor_failover.py
sleep 2
python3 gc/monitor_failover.py > logs/monitor_failover.log 2>&1 &

# Esperar ~10s y verificar
sleep 10
cat gc/ga_activo.txt
```

---

### Problema: No hay REPL SEND en M1

**Causa:** No se están generando operaciones de escritura contra el GA primario.

**Solución:**
```bash
# Verificar que clientes apuntan al GC correcto
# M3
cat ~/biblioteca-clientes/.env | grep GC_ADDR
# Debe ser: GC_ADDR=tcp://10.43.101.220:5555

# Verificar que gc/ga_activo.txt está en "primary"
# M1
cat ~/ProyectoDistribuidos/biblioteca-sistema/gc/ga_activo.txt

# Generar operación de prueba directa al GA
# M1
python3 - <<'PY'
import zmq, json
ctx=zmq.Context(); s=ctx.socket(zmq.REQ)
s.setsockopt(zmq.RCVTIMEO, 3000)
s.connect('tcp://127.0.0.1:6000')
msg={"operacion":"devolucion","book_code":"BOOK-999","user_id":1,"recv_ts":"test"}
s.send_string(json.dumps(msg))
print("Reply:", s.recv_string())
s.close(); ctx.term()
PY

# Verificar REPL SEND
tail -20 logs/ga_primary.log | grep 'REPL SEND'
```

---

### Problema: No hay REPL RECV en M2

**Causa:** Conectividad de red o puerto 7001 no escuchando.

**Solución:**
```bash
# Verificar conectividad desde M1 a M2
# M1
nc -vz 10.43.102.248 7001

# Verificar que M2 está escuchando en 7001
# M2
ss -tnlp | grep 7001

# Verificar GA_REPL_PUSH_ADDR en M1
# M1
grep GA_REPL_PUSH_ADDR ~/ProyectoDistribuidos/biblioteca-sistema/.env

# Debe ser: tcp://10.43.102.248:7001 (IP de M2, no localhost)

# Si está mal, corregir y reiniciar GA primario
# M1
cd ~/ProyectoDistribuidos/biblioteca-sistema
sed -i 's/^GA_REPL_PUSH_ADDR=.*/GA_REPL_PUSH_ADDR=tcp:\/\/10.43.102.248:7001/' .env
bash scripts/stop_all.sh
bash scripts/start_site1.sh
```

---

### Problema: Experimentos fallan con "No module named 'ps'"

**Causa:** Import fallido en consolidar_metricas.py.

**Solución:**
```bash
# M3
cd ~/biblioteca-clientes

# Verificar que __init__.py existe
ls -la ps/__init__.py

# Reinstalar dependencias
pip3 install -r ps/requirements.txt

# Re-ejecutar
bash scripts/run_experiments.sh
```

---

### Problema: Multi_ps.py falla con timeout

**Causa:** GC no responde o dirección incorrecta.

**Solución:**
```bash
# M3
cd ~/biblioteca-clientes

# Verificar conectividad
nc -vz 10.43.101.220 5555

# Verificar .env
cat .env | grep GC_ADDR

# Probar con timeout mayor
python3 pruebas/multi_ps.py --num-ps 1 --requests-per-ps 5 --timeout 5.0
```

---

### Problema: BD secundaria no sincroniza

**Causa:** GA_ROLE incorrecto en M2 o falta generar operaciones.

**Solución:**
```bash
# M2
cd ~/Desktop/DistribuidosProyecto/biblioteca-sistema

# Verificar rol en logs
head -20 logs/ga_secondary.log | grep Role

# Debe decir: Role        : secondary

# Si dice "primary", corregir y reiniciar
sed -i 's/^GA_ROLE=.*/GA_ROLE=secondary/' .env
bash scripts/stop_all.sh
bash scripts/start_site2.sh

# Verificar que escucha en 7001
ss -tnlp | grep 7001

# Generar operaciones desde M3 y verificar REPL RECV
tail -f logs/ga_secondary.log | grep 'REPL RECV'
```

---

## RESUMEN DE COMANDOS CLAVE

### Reseteo Completo

```bash
# M1, M2, M3 (en cada máquina)
cd <directorio-proyecto>
bash scripts/stop_all.sh
rm -rf logs/* .pids/* gc/ga_activo.txt gc/ga_db_*.pkl gc/ga_wal_*.log
```

### Inicio del Sistema

```bash
# M1
cd ~/ProyectoDistribuidos/biblioteca-sistema
bash scripts/start_site1.sh

# M2
cd ~/Desktop/DistribuidosProyecto/biblioteca-sistema
bash scripts/start_site2.sh
```

### Generar Carga

```bash
# M3
cd ~/biblioteca-clientes
python3 pruebas/multi_ps.py --num-ps 2 --requests-per-ps 10 --mix 50:50:0
```

### Experimentos

```bash
# M3
cd ~/biblioteca-clientes
bash scripts/run_experiments.sh
cat experimentos/experimento_carga.md
```

### Failover Manual

```bash
# M1 - Obtener PID y matar GA
pgrep -f ga/ga.py | head -1
kill -9 <PID>

# Observar conmutación
tail -f logs/monitor_failover.log
watch -n 1 cat gc/ga_activo.txt

# Restaurar
bash scripts/start_site1.sh
```

### Verificar Replicación

```bash
# M1
tail -f logs/ga_primary.log | grep 'REPL SEND'

# M2
tail -f logs/ga_secondary.log | grep -E 'REPL RECV|REPL APPLY'
```

### Detener Sistema

```bash
# M1, M2
cd <directorio-proyecto>
bash scripts/stop_all.sh
```

---

## NOTAS FINALES

- **Los logs NO se borran al detener:** Quedan en `logs/` para análisis posterior.
- **Para nueva ejecución completa:** Seguir el [Paso 1: Reseteo Completo](#paso-1-reseteo-completo-del-sistema).
- **Duración estimada de la demo completa:** 20-30 minutos.
- **Archivos clave para el informe:**
  - `experimentos/experimento_carga.md` (métricas)
  - `logs/monitor_failover.log` (evidencia de failover)
  - `gc/ga_wal_*.log` (trazabilidad de operaciones)
  - `evidencias_failover/REPORTE_FAILOVER.md` (si usaste failover_demo.sh)

---

**Última actualización:** 19 noviembre 2025  
**Versión:** 1.0  
**Repositorios:**
- Sistema: `https://github.com/SistemasDistribuidos2530/biblioteca-sistema`
- Clientes: `https://github.com/SistemasDistribuidos2530/biblioteca-clientes`

---

**¡Éxito en la demostración!** 🚀

