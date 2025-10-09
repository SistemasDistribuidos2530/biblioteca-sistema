#!/usr/bin/env python3
"""
Cliente de prueba (PS) para enviar solicitudes al GC.
- Conecta al GC vía REQ/REP en puerto 5555.
- Envía una solicitud de devolución y una de renovación.
- Imprime las respuestas.
"""

import zmq
import json

# Dirección del GC (ajusta si lo corres en otra máquina)
DIRECCION_GC = "tcp://10.43.101.220:5555"

contexto = zmq.Context()
socket = contexto.socket(zmq.REQ)
socket.connect(DIRECCION_GC)

# Solicitud de devolución
solicitud_devolucion = {
    "operation": "devolucion",
    "book_code": "ISBN123",
    "user_id": "usuario01"
}
socket.send_string(json.dumps(solicitud_devolucion))
print("Enviado:", solicitud_devolucion)
respuesta = socket.recv_string()
print("Respuesta del GC:", respuesta)

# Solicitud de renovación
solicitud_renovacion = {
    "operation": "renovacion",
    "book_code": "ISBN456",
    "user_id": "usuario02"
}
socket.send_string(json.dumps(solicitud_renovacion))
print("Enviado:", solicitud_renovacion)
respuesta = socket.recv_string()
print("Respuesta del GC:", respuesta)

socket.close()
contexto.term()
