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
  "operation": "renovacion" | "devolucion",
  "book_code": "BOOK-<id>",
  "user_id": <int>
}
```

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

## 🩺 Troubleshooting

- **Puertos no escuchando**
  ```bash
  ss -tulpen | grep -E ':5555|:5556' || netstat -tulpen | grep -E ':5555|:5556'
  ```
  Asegúrate de correr `gc/gc.py` y que los binds usen `0.0.0.0` si recibirás de otra máquina.

- **Actores no reciben**
  - Verifica que están **suscritos** a los tópicos correctos.
  - Asegura que conectan a `tcp://127.0.0.1:5556` (mismo host del GC).
  - Revisa `log_actor_*.txt` y consola del actor.

- **No llega tráfico externo**
  - Firewall en M1 (si aplica):  
    `sudo ufw allow 5555/tcp && sudo ufw allow 5556/tcp`
  - Conectividad desde M3:  
    `ping -c 1 10.43.101.220`  
    `nc -vz 10.43.101.220 5555`

- **Formato de mensaje inválido**
  - Confirma que PS envía JSON con `operation`, `book_code`, `user_id` **como string por REQ**.
  - Revisa excepciones parseando JSON en GC.

---

## 📝 Notas

- Los scripts de actores presentan **salida legible** con bloques y separadores, y registran líneas resumen en sus logs.
- `ps_prueba.py` envía 2 mensajes de prueba al GC **local** para smoke test.
- El **Makefile** permite ejecutar GC y actores fácilmente y manejar logs/PIDs.

---

## 📄 Licencia y créditos

Uso académico – curso de **Introducción a Sistemas Distribuidos** (PUJ).  
Autores: **Thomas Arévalo, Santiago Mesa, Diego Castrillón**.  
Profesor: **Rafael Páez Méndez**.  
Año: **2025**.
