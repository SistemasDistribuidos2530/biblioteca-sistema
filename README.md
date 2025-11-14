# Biblioteca – Sistema (GC + Actores)

**Universidad:** Pontificia Universidad Javeriana  
**Materia:** Introducción a Sistemas Distribuidos  
**Profesor:** Rafael Páez Méndez  
**Integrantes:** Thomas Arévalo, Santiago Mesa, Diego Castrillón  
**Fecha:** 8 de octubre de 2025

## 🧠 Descripción

Este repositorio implementa el **Gestor de Carga (GC)** y los **Actores** de un sistema distribuido de biblioteca:

- **GC (gc/gc.py)**: servidor **ZeroMQ REP** (recibe solicitudes) y **ZeroMQ PUB** (publica a actores).
- **Actores (actores/…)**: procesos **SUB** que se suscriben a tópicos del GC:
  - `actor_renovacion.py` → tópico **"Renovacion"**
  - `actor_devolucion.py` → tópico **"Devolucion"**

> **Topología final de integración**  
> PS (M3: `10.43.102.38`) → **REQ** → GC (M1: `10.43.101.220:5555`) → **PUB** → Actores (M1: `127.0.0.1:5556`)

```
+--------------------+          REQ/REP           +---------------------------+      PUB/SUB      +------------------------+
|  PS (M3)           |  --->  tcp://10.43.101.220:5555  ---> |  GC (M1)                  | ---> tcp://127.0.0.1:5556 ---> |  Actores (M1)       |
|  biblioteca-clientes|                                  |  biblioteca-sistema (gc.py) |                          |  Renovación/Devolución |
+--------------------+                                  +---------------------------+                          +------------------------+
```

---

## 📦 Requisitos del entorno (M1)

- **SO**: Ubuntu 22.04.5 LTS (jammy)
- **Python**: 3.10.12
- **ZeroMQ**:
  - `pyzmq`: 27.1.0
  - `libzmq`: 4.3.5
- (Opcional) `python-dotenv` (si quieres cargar `.env` desde el código; **NO es requerido** con el Makefile provisto).

> En las pruebas actuales, `python-dotenv` **no está instalado** en M1 (OK).

---

## 🗂️ Estructura del repo

```
biblioteca-sistema/
├── actores/
│   ├── actor_devolucion.py        # SUB -> tópico "Devolucion"
│   ├── actor_renovacion.py        # SUB -> tópico "Renovacion"
│   └── log_actor_*.txt            # logs de actores
├── gc/
│   ├── gc.py                      # GC: REP (5555) + PUB (5556)
│   └── ps_prueba.py               # cliente local de prueba
├── requirements.txt               # dependencias principales
├── Makefile                       # tareas comunes (run-gc, actores, etc.)
└── .venv/                         # entorno virtual (local, no versionar)
```

---

## ⚙️ Instalación

```bash
cd ~/biblioteca-sistema
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt || pip install pyzmq python-dotenv
```

---

## 🔧 Configuración

### Binds del GC (puertos/IP)

- **REP** (recibir de PS): `GC_REP_BIND` → default `tcp://0.0.0.0:5555`
- **PUB** (publicar a actores): `GC_PUB_BIND` → default `tcp://0.0.0.0:5556`

> Los **Actores** se conectan a `tcp://127.0.0.1:5556` (mismo host que el GC).  
> Si cambias el puerto del PUB, asegúrate de actualizarlo también en los actores.

### Cómo pasar la configuración
- Con el **Makefile** (recomendado): exporta automáticamente a `gc.py`.
  ```bash
  make run-gc
  # o con overrides
  make run-gc GC_REP_BIND=tcp://0.0.0.0:5555 GC_PUB_BIND=tcp://0.0.0.0:5556
  ```
- **Opcional (.env)**: si decides cargar `.env` desde el código, instala `python-dotenv` y añade `load_dotenv()` en `gc.py`, luego crea `.env`:
  ```env
  GC_REP_BIND=tcp://0.0.0.0:5555
  GC_PUB_BIND=tcp://0.0.0.0:5556
  ```

---

## ▶️ Ejecución con Makefile

```bash
# 1) Activar entorno (una vez por terminal)
source .venv/bin/activate

# 2) Iniciar GC (REP+PUB)
make run-gc
#   Overrides opcionales:
#   make run-gc GC_REP_BIND=tcp://0.0.0.0:5555 GC_PUB_BIND=tcp://0.0.0.0:5556

# 3) Iniciar actores (en 2 terminales) o en background:
make run-actor-devolucion
make run-actor-renovacion
# o bien:
make start-actors

# 4) (Opcional) Prueba local rápida del GC
make ps-prueba

# 5) Ver logs de actores
make logs
make tail-logs     # tail -f hasta Ctrl+C

# 6) Verificar puertos
make check-ports

# 7) Limpiar logs de actores
make clean-logs
```

---

## 🏃 Ejecución TRADICIONAL (SIN Makefile)

### 1) Entorno e instalación
```bash
cd ~/biblioteca-sistema
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt || pip install pyzmq
```

### 2) Iniciar GC (binds por defecto o personalizados)
```bash
# binds por defecto
export GC_REP_BIND=tcp://0.0.0.0:5555
export GC_PUB_BIND=tcp://0.0.0.0:5556

# iniciar GC
python3 gc/gc.py
```

### 3) Iniciar Actores (en terminales separadas)
```bash
python3 actores/actor_devolucion.py
python3 actores/actor_renovacion.py
```

### 4) Prueba local del GC (opcional, mismo host)
```bash
python3 gc/ps_prueba.py
```

### 5) Verificación de puertos y logs
```bash
# Puertos escuchando
ss -tulpen | grep -E ':5555|:5556' || netstat -tulpen | grep -E ':5555|:5556'

# Últimas líneas de logs de actores
tail -n 10 actores/log_actor_devolucion.txt 2>/dev/null || echo "(aún sin log)"
tail -n 10 actores/log_actor_renovacion.txt 2>/dev/null || echo "(aún sin log)"
```

---

## 🔐 Formatos de mensaje

### 1) De PS → GC (JSON string por REQ/REP)
El GC espera **strings** con JSON:
```json
{
  "operation": "renovacion",
  "book_code": "BOOK-123",
  "user_id": 45
}
```
<!-- Operaciones posibles: renovacion, devolucion, prestamo; user_id entero -->

### 2) De GC → Actores (PUB/SUB)
El GC publica **"TOPICO {json}"** en:
- Tópico **"Renovacion"**
- Tópico **"Devolucion"**

Ejemplo de contenido JSON publicado:
```json
{
  "operacion": "renovacion",
  "book_code": "BOOK-123",
  "user_id": 45,
  "recv_ts": "2025-10-06T21:11:32.997813Z",
  "published_ts": "2025-10-06T21:11:32.997872Z"
}
```

### 3) Respuesta del GC al PS (string JSON)
```json
{"estado":"ok","mensaje":"Operacion aceptada"}
```

---

## 🔍 Verificación M3 ↔ M1

En **M3 (`biblioteca-clientes`)**:
1. `.env` con `GC_ADDR=tcp://10.43.101.220:5555`
2. Generar y enviar:
   ```bash
   python3 ps/gen_solicitudes.py --n 10 --seed 123 --mix 70:30
   python3 ps/ps.py
   ```
3. Métricas:
   ```bash
   python3 ps/log_parser.py
   ```

En **M1 (`biblioteca-sistema`)** deberías ver:
- En GC: bloques de solicitudes.
- En Actores: bloques **RENOVACIÓN/DEVOLUCIÓN PROCESADA** y líneas nuevas en `log_actor_renovacion.txt` / `log_actor_devolucion.txt`.

---

## 🧱 Arquitectura Global del Sistema (Sede)
Componentes en una sede:
| Componente | Tipo | Canal | Función |
|------------|------|-------|---------|
| GC (gc.py) | Servicio | REQ/REP (5555), PUB (5556) | Recepción de solicitudes, clasificación y publicación a actores |
| GC Multihilo (gc_multihilo.py) | Servicio | REQ/REP (proxy), PUB | Procesamiento concurrente (pool threads) |
| Actor Renovación | Proceso | SUB (tópico "Renovacion") | Procesa renovaciones (lógica simulada) |
| Actor Devolución | Proceso | SUB (tópico "Devolucion") | Procesa devoluciones |
| Actor Préstamo | Proceso | SUB (tópico "Prestamo") + REQ/REP GA | Verifica disponibilidad, actualiza GA |
| GA (ga.py) | Servicio | REQ/REP (6000/6001) | Persistencia simple y WAL |
| Monitor Failover | Proceso | Lectura estado GA | Detecta pérdida de heartbeats y actualiza `ga_activo.txt` |

### Flujo Mensajes (Simplificado)
1. PS → GC (REQ/REP JSON) `operation/book_code/user_id`
2. GC responde OK/ERROR y publica a PUB/SUB si la operación es asíncrona.
3. Actores SUB leen tópico y procesan.
4. Actor Préstamo realiza REQ al GA (síncrono) para alterar/consultar estado.
5. Monitor Failover escribe `gc/ga_activo.txt` (primary|secondary) que consumen actores/GC.

---
## 🔐 Seguridad (Perspectiva Sede)
| Riesgo | Control | Archivo/Fuente |
|--------|---------|-----------------|
| Mensaje malicioso desde PS | Validación operación (whitelist) | `gc.py` / `gc_multihilo.py` |
| Saturación de GC | Multihilo + backoff PS | `gc_multihilo.py` / PS `.env` |
| Replay hacia GA | request_id + posible timestamp (extensión futura) | Actores / GA |
| Corrupción DB | WAL + backups | `generate_db.py` / GA WAL |
| Fail-stop GA primario | Monitor failover + conmutación | `gc/monitor_failover.py` |

Pruebas relevantes (en sede):
- `pruebas/test_actor_failure.py` (caída actor)
- `pruebas/test_db_corruption.py` (corrupción DB)
- `pruebas/test_latency.py` (latencia artificial)
- `ga/test_failover.py` (menú failover manual)

---
## ⚠️ Modelo de Fallos (Sede)
| Falla | Impacto | Mitigación |
|-------|---------|-----------|
| Caída actor | Menor throughput de esa operación | Otros actores + reinicio manual |
| Caída GA primario | Escritos fallan temporalmente | Conmutación a secondary + WAL |
| Latencia PUB/SUB | Procesamiento demorado | Separación de roles + multihilo |
| Corrupción DB | Estado inconsistente | Replay WAL + backup |
| Saturación GC | Timeouts PS | Versión multihilo (pool) |

---
## 🔄 Failover GA (Detalle)
Indicadores:
- Archivo estado: `gc/ga_activo.txt` (primary|secondary)
- Logs de monitor: `logs/monitor_failover.log`
- MTTD: tiempo desde caída primaria hasta escritura de "secondary".
- MTTR: tiempo desde escritura "secondary" hasta primera respuesta OK post-failover.

Medición automática: `scripts/failover_measure.sh` (debe tener sedes activas).

---
## 🧪 Rendimiento y Multihilo
Comparar GC serial vs multihilo:
```bash
# Serial (gc.py) ya corre con start_site1.sh
# Multihilo manual:
GC_NUM_WORKERS=10 python3 gc/gc_multihilo.py
```
En clientes:
```bash
python3 pruebas/multi_ps.py --num-ps 10 --requests-per-ps 50 --mix 50:50:0 --seed 500 --mode concurrent
```
Resultados referenciales (depende hardware):
| Modo | PS | OK% | Lat media (s) | TPS |
|------|----|-----|---------------|-----|
| Serial | 6 | 95–100% | 0.18–0.25 | 30–35 |
| Multihilo | 6 | 95–100% | 0.12–0.20 | 38–45 |

---
## 🗂 Logs Clave
| Archivo | Fuente | Utilidad |
|---------|--------|----------|
| `logs/gc_serial.log` | GC serial | Diagnóstico REQ/REP |
| `logs/gc_multihilo.log` | GC multihilo | Hilos y errores |
| `logs/actor_*.log` | Actores | Flujo operación |
| `logs/ga_primary.log` | GA | Persistencia / errores |
| `logs/monitor_failover.log` | Monitor | Detección y timestamps |
| `gc/ga_activo.txt` | Monitor | Estado actual GA |

---
## 🧭 Multi-Máquina (Resumen rápido)
| Paso | M1 | M2 |
|------|----|----|
| BD inicial | generate_db.py | (opcional réplica) |
| Arranque sede | start_site1.sh | start_site2.sh |
| Failover | kill GA primario | espera ser secondary |

Ver documentación cruzada en `PASO_A_PASO_MULTI_MAQUINA.md`.

---
## ✅ Validaciones Rápidas (Sede)
```bash
# Actores vivos
pgrep -f actor_renovacion.py
pgrep -f actor_devolucion.py

# Estado GA
cat gc/ga_activo.txt

# Puerto REP abierto
ss -tnlp | grep 5555
```

Esperar: archivo `ga_activo.txt` con "primary" inicialmente y cambio a "secondary" tras failover.

---
## 📦 Scripts Principales (Sede)
| Script | Función |
|--------|---------|
| `scripts/start_site1.sh` | Arranca todos componentes primary |
| `scripts/start_site2.sh` | Arranca componentes secondary |
| `scripts/stop_all.sh` | Parada ordenada (SIGTERM + SIGKILL fallback) |
| `scripts/generate_db.py` | DB inicial + WALs vacíos |
| `gc/gc_multihilo.py` | GC concurrente |
| `gc/monitor_failover.py` | Actualiza `ga_activo.txt` |
| `ga/test_failover.py` | Menú de pruebas de caída/corrupción |

---
## 🩺 Troubleshooting Sede
| Problema | Causa común | Acción |
|----------|-------------|--------|
| GC no recibe | Puerto 5555 ocupado | Cambiar bind / liberar puerto |
| Actores no reciben | PUB bind incorrecto | Confirmar `GC_PUB_BIND` y SUB IP |
| Failover no cambia | Monitor detenido | Reiniciar `monitor_failover.py` |
| Latencias altas | Saturación serial | Usar `gc_multihilo.py` |
| DB no carga | Corrupción / formato | Restaurar backup o replay WAL |

---
## 📝 Notas de Implementación
- `gc_multihilo.py` usa `zmq.proxy(frontend, backend)` + sockets inproc para distribuir carga.
- Actores leen `gc/ga_activo.txt` para decidir a qué GA conectarse.
- WAL es **append only**; replay (simplificado) previsto al reinicio.
- Sin consenso: failover manual/simple (ventana inconsistencia documentada).

---
## 📄 Licencia y créditos
Uso académico – curso de **Introducción a Sistemas Distribuidos** (PUJ). Autores: **Thomas Arévalo, Santiago Mesa, Diego Castrillón**. Profesor: **Rafael Páez Méndez**. Año: **2025**.
