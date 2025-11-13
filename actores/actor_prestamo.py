#!/usr/bin/env python3
# archivo: actores/actor_prestamo.py
#
# Actor de PRÉSTAMO. Suscrito al tópico "Prestamo".
# Lee gc/ga_activo.txt por cada mensaje y envía al GA activo:
#   {"operacion":"prestamo","book_code":...,"user_id":...}
# Espera respuesta síncrona del GA y la registra en log_actor_prestamo.txt.

import zmq
import json
import signal
import sys
import os
from datetime import datetime

# ---------- Configuración ----------
DIRECCION_GC_PUB = "tcp://127.0.0.1:5556"
TOPICO_SUSCRIPCION = "Prestamo"
ARCHIVO_LOG = "log_actor_prestamo.txt"
FILE_GA_ACTIVO = "gc/ga_activo.txt"
GA_PRIMARY = "tcp://localhost:6000"
GA_SECONDARY = "tcp://localhost:6001"
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
    addr = ga_addr_actual()
    sock = None
    try:
        sock = contexto.socket(zmq.REQ)
        sock.setsockopt(zmq.RCVTIMEO, REQ_TIMEOUT_MS)
        sock.setsockopt(zmq.SNDTIMEO, REQ_TIMEOUT_MS)
        sock.connect(addr)
        sock.send_string(json.dumps(payload))
        reply = sock.recv_string()
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
    print(" ACTOR DE PRÉSTAMO — SUSCRIPCIÓN PUB/SUB ".center(72, " "))
    print("-" * 72)
    print(f"  Tópico        : {TOPICO_SUSCRIPCION}")
    print(f"  Dirección PUB : {DIRECCION_GC_PUB}")
    print(f"  Log           : {ARCHIVO_LOG}")
    print(f"  GA activo     : {leer_ga_activo()} -> {ga_addr_actual()}")
    print("=" * 72 + "\n")

def print_bloque_prestamo(datos: dict, respuesta_ga: dict):
    operacion     = datos.get("operacion", "N/A")
    codigo_libro  = datos.get("book_code", "N/A")
    id_usuario    = datos.get("user_id", "N/A")
    recv_ts       = datos.get("recv_ts", "N/A")
    published_ts  = datos.get("published_ts", "N/A")
    procesado_ts  = iso()

    print("-" * 72)
    print(" PRÉSTAMO PROCESADO ".center(72, " "))
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
        "PRESTAMO PROCESADO | "
        f"Usuario={id_usuario} | Libro={codigo_libro} | RecibidoGC={recv_ts} | "
        f"Publicado={published_ts} | Procesado={procesado_ts} | GA={respuesta_ga}"
    )
    escribir_log(mensaje_log)

# ---------- Manejo señales ----------
def manejar_senal(sig, frame):
    global EJECUTANDO
    print(f"\n[{iso()}] Señal recibida ({sig}). Deteniendo Actor Préstamo...\n")
    EJECUTANDO = False

signal.signal(signal.SIGINT, manejar_senal)
signal.signal(signal.SIGTERM, manejar_senal)

# ---------- Bucle principal ----------
banner_inicio()
escribir_log(f"Actor Préstamo iniciado. Suscrito a tópico: {TOPICO_SUSCRIPCION}")

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

            payload = {
                "operacion": "prestamo",
                "book_code": datos.get("book_code"),
                "user_id": datos.get("user_id"),
                "recv_ts": datos.get("recv_ts"),
                "published_ts": datos.get("published_ts"),
                "origen": "actor_prestamo",
                "procesado_ts": iso(),
            }

            respuesta = contactar_ga(payload)
            print_bloque_prestamo(datos, respuesta)
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
    escribir_log("Actor Préstamo detenido correctamente")
    print(f"[{iso()}] Actor Préstamo detenido correctamente.\n")
except Exception:
    pass
