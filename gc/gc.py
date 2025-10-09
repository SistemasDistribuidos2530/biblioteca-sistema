#!/usr/bin/env python3
"""

Gestor de Carga (GC) - gc.py

--------------------------------

Funcionalidad mínima para la primera entrega:
- REQ/REP socket para recibir peticiones desde PS (síncrono).
- PUB socket para publicar tópicos "Devolución" y "Renovacion" hacia Actores.
- Responder confirmación inmediata al PS antes de publicar.
- Mensajes en JSON (utf-8).
"""

import zmq	# ZeroMQ Python bindings
import json	# Para serializar mensajes
import os
import time	# Timestamps y delays opcionales
import signal	# Para manejo de Ctrl+C/graceful shutdown
import sys
from datetime import datetime


# ---------- Configuracion de IPs/puertos ----------

ENLACE_REP = os.getenv("GC_REP_BIND", "tcp://0.0.0.0:5555")  # REP (PS -> GC)
ENLACE_PUB = os.getenv("GC_PUB_BIND", "tcp://0.0.0.0:5556")  # PUB (GC -> Actores)

# ---------- Inicialización de ZeroMQ ----------

contexto = zmq.Context()		#Crea el contexto global de ZeroMQ (thread-safe)

socket_rep = contexto.socket(zmq.REP)	# Socket REP: atiende peticiones cincrónicas de PS
socket_rep.bind(ENLACE_REP)		# Vincula al puerto configurado para recibir conexiones

socket_pub = contexto.socket(zmq.PUB)	# Socket PUB: publica tópicos para Actores (asíncrono)
socket_pub.bind(ENLACE_PUB)		# Vincula al puerto configurado para publicar

# Poller para controlar sockets con timeout

poller = zmq.Poller()
poller.register(socket_rep, zmq.POLLIN)

# ---------- Estado y utilidades ----------

EJECUTANDO = True		# Flag para loop principal

def iso():
	"""Retorna timestamp en formato ISO UTC con sufijo Z."""
	return datetime.utcnow().isoformat() + "Z"

def cargar_json_seguro(s: str):
	"""Carga JSON de forma segura, retornando None si falla."""
	try:
		return json.loads(s)
	except Exception:
		return None

def construir_respuesta(estado="ok", mensaje="ok", informacion=None):
	"""Construye mensaje de respuesta al PS (serializable)."""
	carga = {"estado": estado, "mensaje": mensaje, "ts":iso()}
	if informacion is not None:
		carga["info"] = informacion
	return json.dumps(carga)

def publicar_topico(topico: str, carga: dict):
	"""
	Publica un mensaje en el tópico indicado usando la convención:
	'TOPICO <json>'.
	Los suscriptores SUB pueden filtrar por prefijo 'TOPICO'.
	"""

	try:
		mensaje = json.dumps(carga)
		socket_pub.send_string(f"{topico} {mensaje}")	# Envío como string "topico json"
	except Exception as e:
		# Para esta primera version solo se imprimer el error, para la segunda se harían reintentos/logs
		print(f"\n[{iso()}] ERROR publicando topico {topico}: {e}", file=sys.stderr)


# ---------- Manejo de señales para apagado ordenado ----------

def manejar_senal(sig, frame):
	"""HAndler para señales (SIGINT/SIGTERM) que cambia la bandera de ejecucion."""
	global EJECUTANDO
	print(f"\n[{iso()}] Señal recibida ({sig}), deteniendo GC...")
	EJECUTANDO = False

signal.signal(signal.SIGINT, manejar_senal)	# Ctrl+C
signal.signal(signal.SIGTERM, manejar_senal)	# kill

# ---------- Operaciones válidas (mapa de entrada -> tópico) ----------

OPERACIONES_VALIDAS = {
	"devolucion": "Devolucion",
	"renovacion": "Renovacion"
}

# ---------- Bucle principal ----------
print(f"[{iso()}] Gestor de Carga iniciado. REP en {ENLACE_REP} | PUB en {ENLACE_PUB}")

while EJECUTANDO:
	try:
		eventos = dict(poller.poll(500))	# Espera hasta 500 ms (medio segundo)
		if socket_rep in eventos:

			# Espera bloqueante por una petición desde un PS (socket REP)
			raw = socket_rep.recv_string()	#REcibe cadena (bloqueante)
			recibido_ts = iso()	# Timestamp de recepción

			# Intentar parsear JSON, si falla, interpretar formato simplificado "op|codigo|usuario"
			solicitud = cargar_json_seguro(raw)
			if solicitud is None:
				partes = raw.split("|")
				oper = partes[0].strip().lower() if len(partes) >= 1 else ""
				codigo_libro = partes[1].strip() if len(partes) > 1 else None
				id_usuario = partes[2].strip() if len(partes) > 2 else None
				solicitud = {"operation": oper, "book_code": codigo_libro, "user_id": id_usuario}

			# Normalizar campos de la solicitud
			operacion = solicitud.get("operation", "").strip().lower()
			codigo_libro = solicitud.get("book_code")
			id_usuario = solicitud.get("user_id")

			# Validación mínima: operacion soportada
			if operacion not in OPERACIONES_VALIDAS:
				# Responde inmediatamente con error si la operacion es inválida
				respuesta_error = construir_respuesta(
					estado = "error",
					mensaje = "Operacion no soportada",
					informacion = {"operacion_recibida": operacion}
				)
				socket_rep.send_string(respuesta_error)		# RESPUESTA en patrón REQ/REP
				continue	#No publica nada

			# Respuesta inmediata al PS (aceptada)
			respuesta_ok = construir_respuesta(
				estado = "ok",
				mensaje = "Operacion aceptada",
				informacion = {
					"operacion": operacion,
					"book_code": codigo_libro,
					"user_id": id_usuario,
					"recv_ts": recibido_ts
				}
			)
			socket_rep.send_string(respuesta_ok)		# Envía respuesta al PS

			# Preparar carga para publicar a los Actores
			topico = OPERACIONES_VALIDAS[operacion]		# "Devolucion" o "Renovacion"
			payload_publicacion = {
				"operacion": operacion,
				"book_code": codigo_libro,
				"user_id": id_usuario,
				"published_ts": iso(),
				"origen": "GC",
				"recv_ts": recibido_ts
			}

			# Publicar en el tópico correspondiente (asíncrono)
			publicar_topico(topico, payload_publicacion)

			# Registro por consola (se puede sustituir por loggin a archivo)
			print(f"[{iso()}] Peticion procesada op = {operacion} libro = {codigo_libro} user = {id_usuario} -> topico = {topico}")

	except zmq.ZMQError as e:
			# Capturar errores específicos de ZeroMQ (por ejemplo sockets cerrados)
			print(f"[{iso()}] ZMQError: {e}", file=sys.stderr)
			time.sleep(0.1)		# Esperar antes de reintentar
	except Exception as e:
			# Capturar errores generales para evitar que el bucle termine inseperadamente
			print(f"[{iso()}] ERROR inesperado en GC: {e}", file=sys.stderr)
			time.sleep(0.1)

# ---------- Cierre ordenado de sockets y contexto ----------
try:
	socket_rep.close(linger = 0)		# Cerrar socket REP sin esperar colas pendientes
	socket_pub.close(linger = 0)		# Cerrar socket PUB
	contexto.term()				# Terminar contexto de ZeroMQ
	print(f"[{iso()}] GC detenido correctamente.")
except Exception:
	pass
