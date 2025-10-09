#!/usr/bin/env python3
# archivo: actores/actor_devolucion.py
#
# Universidad: Pontificia Universidad Javeriana
# Materia: INTRODUCCIÓN A SISTEMAS DISTRIBUIDOS
# Profesor: Rafael Páez Méndez
# Integrantes: Thomas Arévalo, Santiago Mesa, Diego Castrillón
# Fecha: 8 de octubre de 2025
#
# Qué hace:
#   Actor de DEVOLUCIÓN que se suscribe al tópico "Devolucion" publicado por el GC (ZeroMQ PUB/SUB).
#   Recibe mensajes en el formato: "TOPICO {json}" y registra en log_actor_devolucion.txt.
#   Muestra en consola información legible en bloques (varias líneas) por cada devolución procesada.
#
# Formato esperado del payload JSON:
#   {
#     "operacion": "devolucion",
#     "book_code": "BOOK-123",
#     "user_id": 45,
#     "recv_ts": "...",         # opcional (timestamp en GC al recibir del PS)
#     "published_ts": "..."     # opcional (timestamp en GC al publicar a actores)
#   }
#
# Uso:
#   python actores/actor_devolucion.py

import zmq
import json
import signal
import sys
from datetime import datetime

# ---------- Configuración (M1: GC y actores en el MISMO host) ----------
DIRECCION_GC_PUB = "tcp://127.0.0.1:5556"   # GC PUB en el mismo equipo
TOPICO_SUSCRIPCION = "Devolucion"           # tópico publicado por el GC
ARCHIVO_LOG = "log_actor_devolucion.txt"    # archivo de log local

# ---------- Inicialización de ZeroMQ ----------
contexto = zmq.Context()
socket_sub = contexto.socket(zmq.SUB)        # socket SUB para publicaciones
socket_sub.connect(DIRECCION_GC_PUB)         # conecta al PUB del GC
socket_sub.setsockopt_string(zmq.SUBSCRIBE, TOPICO_SUSCRIPCION)  # filtro por tópico

# Poller para espera con timeout (no bloqueo indefinido)
poller = zmq.Poller()
poller.register(socket_sub, zmq.POLLIN)

# ---------- Estado y utilidades ----------
EJECUTANDO = True

def iso():
    # Retorna timestamp en formato ISO (UTC) con sufijo 'Z'.
    return datetime.utcnow().isoformat() + "Z"

def escribir_log(mensaje: str):
    # Escribe una línea con timestamp en el archivo de log.
    try:
        with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{iso()}] {mensaje}\n")
    except Exception as e:
        print(f"[{iso()}] ERROR escribiendo log: {e}", file=sys.stderr)

def banner_inicio():
    # Imprime un encabezado legible al iniciar el actor (bloque multilínea).
    print("\n" + "=" * 72)
    print(" ACTOR DE DEVOLUCIÓN — SUSCRIPCIÓN PUB/SUB ".center(72, " "))
    print("-" * 72)
    print(f"  Tópico        : {TOPICO_SUSCRIPCION}")
    print(f"  Dirección PUB : {DIRECCION_GC_PUB}")
    print(f"  Log           : {ARCHIVO_LOG}")
    print("=" * 72 + "\n")

def print_bloque_devolucion(datos: dict):
    # Imprime un bloque multilínea con campos relevantes de la devolución.
    # Normaliza con valores 'N/A' si faltan claves.
    operacion     = datos.get("operacion", "N/A")
    codigo_libro  = datos.get("book_code", "N/A")
    id_usuario    = datos.get("user_id", "N/A")
    recv_ts       = datos.get("recv_ts", "N/A")         # Cuándo el GC recibió del PS (si viene)
    published_ts  = datos.get("published_ts", "N/A")    # Cuándo el GC publicó (si viene)
    procesado_ts  = iso()

    # Bloque legible en consola (alineado y con separadores).
    print("-" * 72)
    print(" DEVOLUCIÓN PROCESADA ".center(72, " "))
    print("-" * 72)
    print(f"  Operación   : {operacion}")
    print(f"  Usuario     : {id_usuario}")
    print(f"  Libro       : {codigo_libro}")
    print(f"  Recibido GC : {recv_ts}")
    print(f"  Publicado   : {published_ts}")
    print(f"  Procesado   : {procesado_ts}")
    print("-" * 72 + "\n")

    # Línea compacta al log (una línea por evento).
    mensaje_log = (
        "DEVOLUCION PROCESADA | "
        f"Usuario={id_usuario} | "
        f"Libro={codigo_libro} | "
        f"RecibidoGC={recv_ts} | "
        f"Publicado={published_ts} | "
        f"Procesado={procesado_ts}"
    )
    escribir_log(mensaje_log)

def procesar_devolucion(datos: dict):
    # Procesa una devolución:
    #   - Lee campos del JSON recibido.
    #   - Imprime bloque en consola (multilínea).
    #   - Registra una línea en el log con resumen.
    print_bloque_devolucion(datos)

# ---------- Manejo de señales ----------
def manejar_senal(sig, frame):
    # Intercepta Ctrl+C (SIGINT) o kill (SIGTERM) para salir ordenado.
    global EJECUTANDO
    print(f"\n[{iso()}] Señal recibida ({sig}). Deteniendo Actor Devolución...\n")
    EJECUTANDO = False

signal.signal(signal.SIGINT, manejar_senal)   # Ctrl+C
signal.signal(signal.SIGTERM, manejar_senal)  # kill

# ---------- Bucle principal ----------
banner_inicio()
escribir_log(f"Actor Devolución iniciado. Suscrito a tópico: {TOPICO_SUSCRIPCION}")

while EJECUTANDO:
    try:
        # Espera hasta 500 ms por eventos de lectura (evita bloqueo infinito).
        eventos = dict(poller.poll(500))

        if socket_sub in eventos:
            # Recibe mensaje completo como string: "TOPICO {json}".
            raw = socket_sub.recv_string()

            # Convierte "TOPICO {json}" a ('TOPICO', '{json}').
            # Convierte una cadena "A B" a dos partes (A, B).
            # Valida y normaliza el formato (si no hay parte JSON → mensaje mal formado).
            partes = raw.split(" ", 1)
            if len(partes) < 2:
                print(
                    f"[{iso()}] Mensaje mal formado (sin JSON):\n"
                    f"  RAW: {raw}\n",
                    file=sys.stderr,
                )
                continue

            _, contenido_json = partes[0], partes[1]

            # Intenta parsear el JSON recibido.
            try:
                datos = json.loads(contenido_json)
            except json.JSONDecodeError as e:
                print(
                    f"[{iso()}] Error parseando JSON:\n"
                    f"  Detalle  : {e}\n"
                    f"  Contenido: {contenido_json}\n",
                    file=sys.stderr,
                )
                escribir_log(f"ERROR_JSON | {e} | Contenido={contenido_json}")
                continue

            # Procesa la devolución (muestra bloque y registra log).
            procesar_devolucion(datos)

    except zmq.ZMQError as e:
        # Errores de ZeroMQ durante poll/recv.
        print(f"[{iso()}] ZMQError:\n  {e}\n", file=sys.stderr)
        escribir_log(f"ERROR_ZMQ | {e}")

    except Exception as e:
        # Cualquier otra excepción inesperada.
        print(f"[{iso()}] ERROR inesperado:\n  {e}\n", file=sys.stderr)
        escribir_log(f"ERROR_INESPERADO | {e}")

# ---------- Cierre ordenado ----------
try:
    socket_sub.close(linger=0)   # Cierra SUB sin esperar más mensajes.
    contexto.term()              # Libera el contexto de ZeroMQ.
    escribir_log("Actor Devolución detenido correctamente")
    print(f"[{iso()}] Actor Devolución detenido correctamente.\n")
except Exception:
    # Si algo falla al cerrar, se ignora para no ensuciar la salida.
    pass
