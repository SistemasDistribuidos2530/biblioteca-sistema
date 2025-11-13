#!/usr/bin/env python3
# archivo: actores/actor_devolucion.py
#
# Actor de DEVOLUCIÓN. Suscrito al tópico "Devolucion".
# Lee gc/ga_activo.txt en cada mensaje para decidir GA activo (primary/secondary).
# Envía al GA un JSON síncrono {"operacion":"devolucion", ...} y espera respuesta.
# Registra en log_actor_devolucion.txt.

import zmq
import json
import signal
import sys
import os
import time
from datetime import datetime

# ---------- Configuración ----------
DIRECCION_GC_PUB = "tcp://127.0.0.1:5556"
TOPICO_SUSCRIPCION = "Devolucion"
ARCHIVO_LOG = "log_actor_devolucion.txt"
FILE_GA_ACTIVO = "gc/ga_activo.txt"
GA_PRIMARY = "tcp://0.0.0.0:6000"
GA_SECONDARY = "tcp://0.0.0.0:6001"

# Timeouts en ms para socket REQ temporal al GA
REQ_TIMEOUT_MS = 5000

# ---------- Inicialización ZeroMQ ----------
contexto = zmq.Context()
socket_sub = contexto.socket(zmq.SUB)
socket_sub.connect(DIRECCION_GC_PUB)
socket_sub.setsockopt_string(zmq.SUBSCRIBE, TOPICO_SUSCRIPCION)

poller = zmq.Poller()
poller.register(socket_sub, zmq.POLLIN)

# ---------- Estado y utilidades ----------
EJECUTANDO = True

def iso():
    return datetime.utcnow().isoformat() + "Z"

def escribir_log(mensaje: str):
    try:
        with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{iso()}] {mensaje}\n")
    except Exception as e:
        print(f"[{iso()}] ERROR escribiendo log: {e}", file=sys.stderr)

def leer_ga_activo():
    """Lee gc/ga_activo.txt; por defecto 'primary' si no existe o vacío."""
    try:
        if not os.path.exists(FILE_GA_ACTIVO):
            return "primary"
        with open(FILE_GA_ACTIVO, "r", encoding="utf-8") as f:
            v = f.read().strip().lower()
            return v if v in ("primary", "secondary") else "primary"
    except Exception:
        return "primary"

def ga_addr_actual():
    return GA_PRIMARY if leer_ga_activo() == "primary" else GA_SECONDARY

def contactar_ga(payload: dict):
    """
    Crea socket REQ temporal, envía payload JSON al GA activo y retorna la respuesta (dict).
    En caso de timeout o error retorna dict con 'estado':'error' y 'detalle'.
    """
    addr = ga_addr_actual()
    sock = None
    try:
        sock = contexto.socket(zmq.REQ)
        sock.setsockopt(zmq.RCVTIMEO, REQ_TIMEOUT_MS)
        sock.setsockopt(zmq.SNDTIMEO, REQ_TIMEOUT_MS)
        sock.connect(addr)

        raw = json.dumps(payload)
        sock.send_string(raw)

        reply = sock.recv_string()  # puede lanzar ZMQError en timeout
        try:
            return json.loads(reply)
        except Exception:
            return {"estado": "error", "mensaje": "Respuesta no JSON del GA", "raw": reply}
    except zmq.ZMQError as e:
        return {"estado": "error", "mensaje": "ZMQError comunicando con GA", "detalle": str(e)}
    except Exception as e:
        return {"estado": "error", "mensaje": "Excepción comunicando con GA", "detalle": str(e)}
    finally:
        if sock is not None:
            try:
                sock.close(linger=0)
            except Exception:
                pass

def banner_inicio():
    print("\n" + "=" * 72)
    print(" ACTOR DE DEVOLUCIÓN — SUSCRIPCIÓN PUB/SUB ".center(72, " "))
    print("-" * 72)
    print(f"  Tópico        : {TOPICO_SUSCRIPCION}")
    print(f"  Dirección PUB : {DIRECCION_GC_PUB}")
    print(f"  Log           : {ARCHIVO_LOG}")
    print(f"  GA activo     : {leer_ga_activo()} -> {ga_addr_actual()}")
    print("=" * 72 + "\n")

def print_bloque_devolucion(datos: dict, respuesta_ga: dict):
    operacion     = datos.get("operacion", "N/A")
    codigo_libro  = datos.get("book_code", "N/A")
    id_usuario    = datos.get("user_id", "N/A")
    recv_ts       = datos.get("recv_ts", "N/A")
    published_ts  = datos.get("published_ts", "N/A")
    procesado_ts  = iso()

    print("-" * 72)
    print(" DEVOLUCIÓN PROCESADA ".center(72, " "))
    print("-" * 72)
    print(f"  Operación   : {operacion}")
    print(f"  Usuario     : {id_usuario}")
    print(f"  Libro       : {codigo_libro}")
    print(f"  Recibido GC : {recv_ts}")
    print(f"  Publicado   : {published_ts}")
    print(f"  Procesado   : {procesado_ts}")
    print(f"  GA respuesta: {respuesta_ga}")
    print("-" * 72 + "\n")

    mensaje_log = (
        "DEVOLUCION PROCESADA | "
        f"Usuario={id_usuario} | Libro={codigo_libro} | RecibidoGC={recv_ts} | "
        f"Publicado={published_ts} | Procesado={procesado_ts} | GA={respuesta_ga}"
    )
    escribir_log(mensaje_log)

# ---------- Manejo de señales ----------
def manejar_senal(sig, frame):
    global EJECUTANDO
    print(f"\n[{iso()}] Señal recibida ({sig}). Deteniendo Actor Devolución...\n")
    EJECUTANDO = False

signal.signal(signal.SIGINT, manejar_senal)
signal.signal(signal.SIGTERM, manejar_senal)

# ---------- Bucle principal ----------
banner_inicio()
escribir_log(f"Actor Devolución iniciado. Suscrito a tópico: {TOPICO_SUSCRIPCION}")

while EJECUTANDO:
    try:
        eventos = dict(poller.poll(500))
        if socket_sub in eventos:
            raw = socket_sub.recv_string()
            partes = raw.split(" ", 1)
            if len(partes) < 2:
                print(f"[{iso()}] Mensaje mal formado (sin JSON): RAW: {raw}", file=sys.stderr)
                continue
            contenido_json = partes[1]
            try:
                datos = json.loads(contenido_json)
            except json.JSONDecodeError as e:
                print(f"[{iso()}] Error parseando JSON: {e} | Contenido: {contenido_json}", file=sys.stderr)
                escribir_log(f"ERROR_JSON | {e} | Contenido={contenido_json}")
                continue

            # Construir payload al GA
            payload = {
                "operacion": "devolucion",
                "book_code": datos.get("book_code"),
                "user_id": datos.get("user_id"),
                "recv_ts": datos.get("recv_ts"),
                "published_ts": datos.get("published_ts"),
                "origen": "actor_devolucion",
                "procesado_ts": iso(),
            }

            # Contactar GA activo
            respuesta = contactar_ga(payload)
            # Registrar respuesta en consola y log
            print_bloque_devolucion(datos, respuesta)
    except zmq.ZMQError as e:
        print(f"[{iso()}] ZMQError:\n  {e}\n", file=sys.stderr)
        escribir_log(f"ERROR_ZMQ | {e}")
    except Exception as e:
        print(f"[{iso()}] ERROR inesperado:\n  {e}\n", file=sys.stderr)
        escribir_log(f"ERROR_INESPERADO | {e}")

# ---------- Cierre ordenado ----------
try:
    socket_sub.close(linger=0)
    contexto.term()
    escribir_log("Actor Devolución detenido correctamente")
    print(f"[{iso()}] Actor Devolución detenido correctamente.\n")
except Exception:
    pass
