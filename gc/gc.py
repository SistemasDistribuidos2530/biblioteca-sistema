#!/usr/bin/env python3
# archivo: gc/gc.py
#
# Universidad: Pontificia Universidad Javeriana
# Materia: INTRODUCCIÓN A SISTEMAS DISTRIBUIDOS
# Profesor: Rafael Páez Méndez
# Integrantes: Thomas Arévalo, Santiago Mesa, Diego Castrillón
# Fecha: 8 de octubre de 2025
#
# Qué hace:
#   Gestor de Carga (GC) con dos sockets ZeroMQ:
#     - REP: recibe solicitudes desde PS (JSON o "op|codigo|usuario")
#     - PUB: publica a actores en tópicos "Devolucion" y "Renovacion"
#   Responde al PS y publica a los actores con el payload correspondiente.
#
# Mensajes:
#   PS -> GC (JSON):
#     {"operation":"devolucion|renovacion","book_code":"BOOK-123","user_id":45}
#   GC -> PS (JSON de respuesta):
#     {"estado":"ok|error","mensaje":"...","ts":"...","info":{...}}
#   GC -> Actores (string, 1 frame):
#     "TOPICO {json}"
#
# Uso:
#   python gc/gc.py

import zmq            # ZeroMQ: sockets distribuidos
import json           # Serialización de mensajes
import os
import time           # Pequeños sleeps ante errores
import signal         # Ctrl+C y apagado ordenado
import sys
from datetime import datetime

# ---------- Configuración de IPs/puertos ----------
# Bindea a toda la red para que PS remoto pueda conectar (defaults fijos).
ENLACE_REP = os.getenv("GC_REP_BIND", "tcp://0.0.0.0:5555")  # REP (PS -> GC)
ENLACE_PUB = os.getenv("GC_PUB_BIND", "tcp://0.0.0.0:5556")  # PUB (GC -> Actores)

# ---------- Inicialización de ZeroMQ ----------
contexto = zmq.Context()                 # Crea contexto global

socket_rep = contexto.socket(zmq.REP)    # Socket REP: atiende PS (síncrono)
socket_rep.bind(ENLACE_REP)              # Vincula el puerto de escucha

socket_pub = contexto.socket(zmq.PUB)    # Socket PUB: publica a Actores
socket_pub.bind(ENLACE_PUB)              # Vincula el puerto de publicación

# Poller: permite esperar con timeout (no bloquear indefinidamente).
poller = zmq.Poller()
poller.register(socket_rep, zmq.POLLIN)

# ---------- Estado y utilidades ----------
EJECUTANDO = True

def iso():
    # Retorna timestamp ISO-8601 (UTC) con sufijo 'Z'.
    return datetime.utcnow().isoformat() + "Z"

def banner_inicio():
    # Imprime banner de inicio (bloque multilínea legible).
    print("\n" + "=" * 72)
    print(" GESTOR DE CARGA (GC) — REQ/REP + PUB/SUB ".center(72, " "))
    print("-" * 72)
    print(f"  REP (escucha) : {ENLACE_REP}")
    print(f"  PUB (publica) : {ENLACE_PUB}")
    print("=" * 72 + "\n")

def cargar_json_seguro(s: str):
    # Intenta json.loads(s); None si falla.
    try:
        return json.loads(s)
    except Exception:
        return None

def construir_respuesta(estado="ok", mensaje="ok", informacion=None):
    # Construye respuesta JSON para PS (como string).
    carga = {"estado": estado, "mensaje": mensaje, "ts": iso()}
    if informacion is not None:
        carga["info"] = informacion
    return json.dumps(carga)

def publicar_topico(topico: str, carga: dict):
    # Publica a un tópico con la convención "TOPICO {json}" (1 frame string).
    try:
        socket_pub.send_string(f"{topico} {json.dumps(carga)}")
    except Exception as e:
        print(
            f"\n[{iso()}] ERROR publicando tópico '{topico}':\n"
            f"  Detalle: {e}\n",
            file=sys.stderr,
        )

def print_bloque_solicitud(operacion, codigo_libro, id_usuario, recibido_ts, topico):
    # Imprime bloque multilínea con la solicitud procesada.
    print("-" * 72)
    print(" SOLICITUD PROCESADA ".center(72, " "))
    print("-" * 72)
    print(f"  Operación   : {operacion}")
    print(f"  Usuario     : {id_usuario}")
    print(f"  Libro       : {codigo_libro}")
    print(f"  Recibido GC : {recibido_ts}")
    print(f"  Tópico PUB  : {topico}")
    print("-" * 72 + "\n")

def print_bloque_error_operacion(operacion_raw):
    # Imprime bloque de error por operación no soportada.
    print("-" * 72, file=sys.stderr)
    print(" OPERACIÓN NO SOPORTADA ".center(72, " "), file=sys.stderr)
    print("-" * 72, file=sys.stderr)
    print(f"  Recibido: '{operacion_raw}'", file=sys.stderr)
    print(f"  Válidas : devolucion, renovacion", file=sys.stderr)
    print("-" * 72 + "\n", file=sys.stderr)

# ---------- Operaciones válidas (mapa de entrada -> tópico) ----------
OPERACIONES_VALIDAS = {
    "devolucion": "Devolucion",
    "renovacion": "Renovacion",
}

# ---------- Manejo de señales ----------
def manejar_senal(sig, frame):
    # Señales (SIGINT/SIGTERM) para salida ordenada.
    global EJECUTANDO
    print(f"\n[{iso()}] Señal recibida ({sig}). Deteniendo GC...\n")
    EJECUTANDO = False

signal.signal(signal.SIGINT, manejar_senal)   # Ctrl+C
signal.signal(signal.SIGTERM, manejar_senal)  # kill

# ---------- Bucle principal ----------
banner_inicio()

while EJECUTANDO:
    try:
        # Espera hasta 500 ms por actividad en REP.
        eventos = dict(poller.poll(500))
        if socket_rep in eventos:
            # Recibe una cadena: puede ser JSON o "op|codigo|usuario".
            raw = socket_rep.recv_string()
            recibido_ts = iso()

            # Intenta parsear JSON; si falla, interpreta formato simple.
            solicitud = cargar_json_seguro(raw)
            if solicitud is None:
                partes = raw.split("|")
                oper = partes[0].strip().lower() if len(partes) >= 1 else ""
                codigo_libro = partes[1].strip() if len(partes) > 1 else None
                id_usuario = partes[2].strip() if len(partes) > 2 else None
                solicitud = {
                    "operation": oper,
                    "book_code": codigo_libro,
                    "user_id": id_usuario,
                }

            # Normaliza campos.
            operacion = (solicitud.get("operation") or "").strip().lower()
            codigo_libro = solicitud.get("book_code")
            id_usuario = solicitud.get("user_id")

            # Valida operación soportada.
            if operacion not in OPERACIONES_VALIDAS:
                socket_rep.send_string(construir_respuesta(
                    estado="error",
                    mensaje="Operacion no soportada",
                    informacion={"operacion_recibida": operacion},
                ))
                print_bloque_error_operacion(operacion_raw=operacion)
                continue  # No publica nada

            # Respuesta inmediata al PS (aceptada).
            socket_rep.send_string(construir_respuesta(
                estado="ok",
                mensaje="Operacion aceptada",
                informacion={
                    "operacion": operacion,
                    "book_code": codigo_libro,
                    "user_id": id_usuario,
                    "recv_ts": recibido_ts,
                },
            ))

            # Prepara carga a publicar a actores.
            topico = OPERACIONES_VALIDAS[operacion]  # "Devolucion" | "Renovacion"
            payload_publicacion = {
                "operacion": operacion,
                "book_code": codigo_libro,
                "user_id": id_usuario,
                "published_ts": iso(),
                "origen": "GC",
                "recv_ts": recibido_ts,
            }

            # Publica en el tópico correspondiente.
            publicar_topico(topico, payload_publicacion)

            # Reporte legible por consola.
            print_bloque_solicitud(
                operacion=operacion,
                codigo_libro=codigo_libro,
                id_usuario=id_usuario,
                recibido_ts=recibido_ts,
                topico=topico,
            )

    except zmq.ZMQError as e:
        # Errores de ZeroMQ (sockets, etc.) → espera breve y continúa.
        print(f"[{iso()}] ZMQError:\n  {e}\n", file=sys.stderr)
        time.sleep(0.1)

    except Exception as e:
        # Errores generales → no tumbar el loop.
        print(f"[{iso()}] ERROR inesperado en GC:\n  {e}\n", file=sys.stderr)
        time.sleep(0.1)

# ---------- Cierre ordenado ----------
try:
    socket_rep.close(linger=0)   # Cierra REP sin esperar colas
    socket_pub.close(linger=0)   # Cierra PUB
    contexto.term()              # Libera el contexto ZMQ
    print(f"[{iso()}] GC detenido correctamente.\n")
except Exception:
    pass
