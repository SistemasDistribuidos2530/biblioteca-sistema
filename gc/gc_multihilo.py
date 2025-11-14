#!/usr/bin/env python3
# archivo: gc/gc_multihilo.py
#
# Universidad: Pontificia Universidad Javeriana
# Materia: INTRODUCCIÓN A SISTEMAS DISTRIBUIDOS
# Profesor: Rafael Páez Méndez
# Integrantes: Thomas Arévalo, Santiago Mesa, Diego Castrillón
# Fecha: 13 de noviembre de 2025
#
# Qué hace:
#   Versión MULTIHILO del Gestor de Carga (GC) para comparación de rendimiento.
#   Utiliza un pool de threads para procesar solicitudes en paralelo.
#   Mantiene la misma lógica de negocio que gc.py pero con concurrencia.
#
# Diferencias con gc.py serial:
#   - Pool de workers (threads) para procesar solicitudes REQ/REP
#   - Cada thread maneja una solicitud completa (recv -> process -> send)
#   - Socket PUB es thread-safe en ZeroMQ (puede compartirse)
#
# Uso:
#   python gc/gc_multihilo.py

import zmq
import json
import os
import time
import signal
import sys
import threading
from datetime import datetime
from queue import Queue, Empty

# Configuración de IPs/puertos (igual que gc.py)
ENLACE_REP = os.getenv("GC_REP_BIND", "tcp://0.0.0.0:5555")
ENLACE_PUB = os.getenv("GC_PUB_BIND", "tcp://0.0.0.0:5556")
ACTOR_PRESTAMO = os.getenv("GC_ACTOR_PRESTAMO", "tcp://localhost:5560")

# Configuración de workers
NUM_WORKERS = int(os.getenv("GC_NUM_WORKERS", "10"))

# Estado global y sincronización
EJECUTANDO = True
lock_pub = threading.Lock()  # Lock para publicaciones (aunque ZMQ es thread-safe, por precaución)
stats_lock = threading.Lock()
stats = {"procesadas": 0, "errores": 0, "por_operacion": {}}

# Operaciones válidas (mapa de entrada -> tópico)
OPERACIONES_VALIDAS = {
    "devolucion": "Devolucion",
    "renovacion": "Renovacion",
    "prestamo": "Prestamo",
}

def iso():
    """Retorna timestamp ISO-8601 (UTC) con sufijo Z."""
    return datetime.utcnow().isoformat() + "Z"

def banner_inicio():
    """Imprime banner de inicio con configuración."""
    print("\n" + "=" * 72)
    print(" GESTOR DE CARGA MULTIHILO (GC) — REQ/REP + PUB/SUB ".center(72, " "))
    print("-" * 72)
    print(f"  REP (escucha) : {ENLACE_REP}")
    print(f"  PUB (publica) : {ENLACE_PUB}")
    print(f"  Num Workers   : {NUM_WORKERS}")
    print("=" * 72 + "\n")

def cargar_json_seguro(s: str):
    """Intenta json.loads(s); retorna None si falla."""
    try:
        return json.loads(s)
    except Exception:
        return None

def construir_respuesta(estado="ok", mensaje="ok", informacion=None):
    """Construye respuesta JSON para PS."""
    carga = {"estado": estado, "mensaje": mensaje, "ts": iso()}
    if informacion is not None:
        carga["info"] = informacion
    return json.dumps(carga)

def publicar_topico(socket_pub, topico: str, carga: dict):
    """Publica a un tópico con la convención TOPICO {json}."""
    try:
        with lock_pub:
            socket_pub.send_string(f"{topico} {json.dumps(carga)}")
    except Exception as e:
        print(f"[{iso()}] ERROR publicando tópico '{topico}': {e}", file=sys.stderr)

def actualizar_stats(operacion: str, exito: bool):
    """Actualiza estadísticas de forma thread-safe."""
    with stats_lock:
        if exito:
            stats["procesadas"] += 1
        else:
            stats["errores"] += 1
        
        if operacion not in stats["por_operacion"]:
            stats["por_operacion"][operacion] = {"ok": 0, "error": 0}
        
        if exito:
            stats["por_operacion"][operacion]["ok"] += 1
        else:
            stats["por_operacion"][operacion]["error"] += 1

def print_bloque_solicitud(operacion, codigo_libro, id_usuario, thread_id):
    """Imprime bloque con la solicitud procesada incluyendo ID del thread."""
    print("-" * 72)
    print(f" SOLICITUD PROCESADA [Thread-{thread_id}] ".center(72, " "))
    print("-" * 72)
    print(f"  Operación : {operacion}")
    print(f"  Usuario   : {id_usuario}")
    print(f"  Libro     : {codigo_libro}")
    print(f"  Timestamp : {iso()}")
    print("-" * 72 + "\n")

def procesar_solicitud(socket_rep, socket_pub, contexto, thread_id):
    """
    Función ejecutada por cada worker thread.
    Recibe solicitud, la procesa y envía respuesta.
    """
    while EJECUTANDO:
        try:
            # Recibir solicitud (blocking con timeout)
            if socket_rep.poll(500, zmq.POLLIN):
                raw = socket_rep.recv_string()
                recibido_ts = iso()

                # Parsear JSON o formato simple
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

                # Normalizar campos
                operacion = (solicitud.get("operation") or "").strip().lower()
                codigo_libro = solicitud.get("book_code")
                id_usuario = solicitud.get("user_id")

                # Validar operación soportada
                if operacion not in OPERACIONES_VALIDAS:
                    socket_rep.send_string(construir_respuesta(
                        estado="error",
                        mensaje="Operacion no soportada",
                        informacion={"operacion_recibida": operacion},
                    ))
                    actualizar_stats(operacion, False)
                    continue

                # Manejo especial: PRESTAMO (síncrono con actor)
                if operacion == "prestamo":
                    req_socket = None
                    try:
                        req_socket = contexto.socket(zmq.REQ)
                        req_socket.setsockopt(zmq.RCVTIMEO, 5000)
                        req_socket.setsockopt(zmq.SNDTIMEO, 5000)
                        req_socket.connect(ACTOR_PRESTAMO)

                        payload_al_actor = json.dumps(solicitud)
                        req_socket.send_string(payload_al_actor)

                        try:
                            respuesta_actor = req_socket.recv_string()
                        except zmq.ZMQError as e_recv:
                            socket_rep.send_string(construir_respuesta(
                                estado="error",
                                mensaje="Error comunicando con actor de prestamo",
                                informacion={"detalle": str(e_recv)},
                            ))
                            actualizar_stats(operacion, False)
                            continue

                        socket_rep.send_string(respuesta_actor)
                        actualizar_stats(operacion, True)
                        print_bloque_solicitud(operacion, codigo_libro, id_usuario, thread_id)

                    except Exception as e:
                        socket_rep.send_string(construir_respuesta(
                            estado="error",
                            mensaje="Error inesperado en GC durante prestamo",
                            informacion={"detalle": str(e)},
                        ))
                        actualizar_stats(operacion, False)

                    finally:
                        if req_socket is not None:
                            try:
                                req_socket.close(linger=0)
                            except Exception:
                                pass
                    
                    continue

                # Caso general: devolucion / renovacion
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

                # Preparar y publicar a actores
                topico = OPERACIONES_VALIDAS[operacion]
                payload_publicacion = {
                    "operacion": operacion,
                    "book_code": codigo_libro,
                    "user_id": id_usuario,
                    "published_ts": iso(),
                    "origen": "GC",
                    "recv_ts": recibido_ts,
                }

                publicar_topico(socket_pub, topico, payload_publicacion)
                actualizar_stats(operacion, True)
                print_bloque_solicitud(operacion, codigo_libro, id_usuario, thread_id)

        except zmq.ZMQError as e:
            if EJECUTANDO:
                print(f"[{iso()}] Thread-{thread_id} ZMQError: {e}", file=sys.stderr)
            time.sleep(0.1)

        except Exception as e:
            if EJECUTANDO:
                print(f"[{iso()}] Thread-{thread_id} ERROR: {e}", file=sys.stderr)
            time.sleep(0.1)

def worker_thread(contexto_compartido, socket_pub, thread_id):
    """
    Thread worker que maneja solicitudes.
    Cada worker tiene su propio socket REP conectado al mismo endpoint.
    """
    socket_rep_worker = contexto_compartido.socket(zmq.REP)
    socket_rep_worker.connect("inproc://backend")
    
    try:
        procesar_solicitud(socket_rep_worker, socket_pub, contexto_compartido, thread_id)
    finally:
        socket_rep_worker.close(linger=0)

def manejar_senal(sig, frame):
    """Maneja señales para cierre ordenado."""
    global EJECUTANDO
    print(f"\n[{iso()}] Señal recibida ({sig}). Deteniendo GC multihilo...\n")
    EJECUTANDO = False

def print_stats_final():
    """Imprime estadísticas finales."""
    print("\n" + "=" * 72)
    print(" ESTADÍSTICAS FINALES GC MULTIHILO ".center(72, " "))
    print("-" * 72)
    print(f"  Total procesadas : {stats['procesadas']}")
    print(f"  Total errores    : {stats['errores']}")
    print("\n  Por operación:")
    for op, counts in stats["por_operacion"].items():
        print(f"    {op:12} : OK={counts['ok']:>5}  ERROR={counts['error']:>5}")
    print("=" * 72 + "\n")

def main():
    """Función principal que inicializa el GC multihilo."""
    global EJECUTANDO
    
    signal.signal(signal.SIGINT, manejar_senal)
    signal.signal(signal.SIGTERM, manejar_senal)
    
    banner_inicio()
    
    contexto = zmq.Context.instance()
    
    # Socket REP (frontend) que recibe del PS
    socket_rep_frontend = contexto.socket(zmq.REP)
    socket_rep_frontend.bind(ENLACE_REP)
    
    # Socket PUB compartido por todos los workers
    socket_pub = contexto.socket(zmq.PUB)
    socket_pub.bind(ENLACE_PUB)
    
    # Backend inproc para distribuir trabajo a workers
    socket_backend = contexto.socket(zmq.DEALER)
    socket_backend.bind("inproc://backend")
    
    # Crear pool de workers
    workers = []
    for i in range(NUM_WORKERS):
        t = threading.Thread(
            target=worker_thread,
            args=(contexto, socket_pub, i+1),
            daemon=True
        )
        t.start()
        workers.append(t)
    
    print(f"[{iso()}] {NUM_WORKERS} workers iniciados\n")
    
    try:
        # Proxy entre frontend y backend
        zmq.proxy(socket_rep_frontend, socket_backend)
    except zmq.ZMQError:
        pass  # Interrupción normal por señal
    except Exception as e:
        print(f"[{iso()}] ERROR en proxy: {e}", file=sys.stderr)
    
    # Esperar a que los workers terminen
    print(f"[{iso()}] Esperando a que los workers terminen...")
    for t in workers:
        t.join(timeout=2)
    
    # Cerrar sockets
    try:
        socket_rep_frontend.close(linger=0)
        socket_backend.close(linger=0)
        socket_pub.close(linger=0)
        contexto.term()
    except Exception:
        pass
    
    print_stats_final()
    print(f"[{iso()}] GC multihilo detenido correctamente.\n")

if __name__ == "__main__":
    main()

