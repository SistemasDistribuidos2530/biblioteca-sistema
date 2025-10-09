#!/usr/bin/env python3
"""
Actor Renovación - actor_renovacion.py

Funcionalidad:
- Se suscribe al tópico "Renovacion" publicado por el GC.
- Procesa mensajes de renovación de préstamos de libros.
- Registra operaciones en log_actor_renovacion.txt
"""

import zmq
import json
import signal
import sys
from datetime import datetime, timedelta

# ---------- Configuración ----------

DIRECCION_GC_PUB = "tcp://127.0.0.1:5556"  # Dirección del socket PUB del GC
TOPICO_SUSCRIPCION = "Renovacion"          # Tópico al que se suscribe
ARCHIVO_LOG = "log_actor_renovacion.txt"   # Archivo de log

# ---------- Inicialización de ZeroMQ ----------

contexto = zmq.Context()

socket_sub = contexto.socket(zmq.SUB)      # Socket SUB para recibir publicaciones
socket_sub.connect(DIRECCION_GC_PUB)       # Conecta al puerto PUB del GC
socket_sub.setsockopt_string(zmq.SUBSCRIBE, TOPICO_SUSCRIPCION)  # Filtra por tópico

# Poller para controlar timeout
poller = zmq.Poller()
poller.register(socket_sub, zmq.POLLIN)

# ---------- Estado y utilidades ----------

EJECUTANDO = True

def iso():
    """Retorna timestamp en formato ISO UTC con sufijo Z."""
    return datetime.utcnow().isoformat() + "Z"

def escribir_log(mensaje: str):
    """Escribe un mensaje en el archivo de log con timestamp."""
    try:
        with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{iso()}] {mensaje}\n")
    except Exception as e:
        print(f"[{iso()}] ERROR escribiendo log: {e}", file=sys.stderr)

def procesar_renovacion(datos: dict):
    """
    Procesa una solicitud de renovación de préstamo.
    
    Args:
        datos: Diccionario con información de la renovación
    """
    operacion = datos.get("operacion", "N/A")
    codigo_libro = datos.get("book_code", "N/A")
    id_usuario = datos.get("user_id", "N/A")
    recv_ts = datos.get("recv_ts", "N/A")
    published_ts = datos.get("published_ts", "N/A")
    
    # Simulación de procesamiento de renovación
    # Calcular nueva fecha de vencimiento (ejemplo: +14 días)
    nueva_fecha = (datetime.utcnow() + timedelta(days=14)).isoformat() + "Z"
    
    mensaje_log = (
        f"RENOVACION PROCESADA | "
        f"Usuario: {id_usuario} | "
        f"Libro: {codigo_libro} | "
        f"Recibido GC: {recv_ts} | "
        f"Publicado: {published_ts} | "
        f"Nueva fecha vencimiento: {nueva_fecha} | "
        f"Procesado: {iso()}"
    )
    
    escribir_log(mensaje_log)
    print(f"[{iso()}] Renovación procesada: Usuario={id_usuario}, Libro={codigo_libro}, Nueva fecha={nueva_fecha}")
    
    # Aquí iría la lógica real de renovación:
    # - Verificar que el préstamo esté activo
    # - Verificar límite de renovaciones permitidas
    # - Actualizar fecha de vencimiento en base de datos
    # - Verificar si hay reservas pendientes del libro
    # - Enviar notificación al usuario
    # - etc.

# ---------- Manejo de señales ----------

def manejar_senal(sig, frame):
    """Handler para señales (SIGINT/SIGTERM)."""
    global EJECUTANDO
    print(f"\n[{iso()}] Señal recibida ({sig}), deteniendo Actor Renovación...")
    EJECUTANDO = False

signal.signal(signal.SIGINT, manejar_senal)   # Ctrl+C
signal.signal(signal.SIGTERM, manejar_senal)  # kill

# ---------- Bucle principal ----------

print(f"[{iso()}] Actor Renovación iniciado. Escuchando tópico '{TOPICO_SUSCRIPCION}' en {DIRECCION_GC_PUB}")
escribir_log(f"Actor Renovación iniciado. Suscrito a tópico: {TOPICO_SUSCRIPCION}")

while EJECUTANDO:
    try:
        eventos = dict(poller.poll(500))  # Espera hasta 500 ms
        
        if socket_sub in eventos:
            # Recibe mensaje completo: "TOPICO <json>"
            raw = socket_sub.recv_string()
            
            # Separa tópico del contenido JSON
            partes = raw.split(" ", 1)
            if len(partes) < 2:
                print(f"[{iso()}] Mensaje mal formado recibido: {raw}", file=sys.stderr)
                continue
            
            topico_recibido = partes[0]
            contenido_json = partes[1]
            
            # Parsear JSON
            try:
                datos = json.loads(contenido_json)
            except json.JSONDecodeError as e:
                print(f"[{iso()}] Error parseando JSON: {e}", file=sys.stderr)
                escribir_log(f"ERROR: JSON inválido - {contenido_json}")
                continue
            
            # Procesar la renovación
            procesar_renovacion(datos)
            
    except zmq.ZMQError as e:
        print(f"[{iso()}] ZMQError: {e}", file=sys.stderr)
        escribir_log(f"ERROR ZMQ: {e}")
        
    except Exception as e:
        print(f"[{iso()}] ERROR inesperado: {e}", file=sys.stderr)
        escribir_log(f"ERROR inesperado: {e}")

# ---------- Cierre ordenado ----------

try:
    socket_sub.close(linger=0)
    contexto.term()
    escribir_log("Actor Renovación detenido correctamente")
    print(f"[{iso()}] Actor Renovación detenido correctamente.")
except Exception:
    pass
