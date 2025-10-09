#!/usr/bin/env python3
# archivo: gc/ps_prueba.py
#
# Universidad: Pontificia Universidad Javeriana
# Materia: INTRODUCCIÓN A SISTEMAS DISTRIBUIDOS
# Profesor: Rafael Páez Méndez
# Integrantes: Thomas Arévalo, Santiago Mesa, Diego Castrillón
# Fecha: 8 de octubre de 2025
#
# Qué hace:
#   Cliente PS de PRUEBA LOCAL que envía dos solicitudes al GC por REQ/REP:
#     - DEVOLUCIÓN
#     - RENOVACIÓN
#   Imprime en consola bloques legibles con lo enviado y lo respondido.
#
# Uso:
#   python gc/ps_prueba.py

import zmq
import json

# ---------- Configuración ----------
# Dirección local del GC (M1: GC y ps_prueba en el mismo host).
DIRECCION_GC = "tcp://127.0.0.1:5555"

def banner():
    # Encabezado legible de inicio.
    print("\n" + "=" * 72)
    print(" PS DE PRUEBA — REQ/REP contra GC ".center(72, " "))
    print("-" * 72)
    print(f"  Conectando a: {DIRECCION_GC}")
    print("=" * 72 + "\n")

def print_bloque_envio(nombre, payload):
    # Muestra lo que se envía, en varias líneas.
    print("-" * 72)
    print(f" ENVÍO: {nombre} ".center(72, " "))
    print("-" * 72)
    print(f"  operation : {payload.get('operation')}")
    print(f"  book_code : {payload.get('book_code')}")
    print(f"  user_id   : {payload.get('user_id')}")
    print("-" * 72 + "\n")

def print_bloque_respuesta(raw):
    # Intenta formatear la respuesta como JSON; si falla, imprime raw.
    print("-" * 72)
    print(" RESPUESTA DEL GC ".center(72, " "))
    print("-" * 72)
    try:
        data = json.loads(raw)
        print(f"  estado : {data.get('estado')}")
        print(f"  mensaje: {data.get('mensaje')}")
        info = data.get("info") or {}
        if info:
            print("  info   :")
            for k, v in info.items():
                print(f"    - {k}: {v}")
        print(f"  ts     : {data.get('ts')}")
    except Exception:
        print(f"  (raw)  : {raw}")
    print("-" * 72 + "\n")

def main():
    # Crea contexto y socket REQ; conecta al GC local.
    contexto = zmq.Context()
    socket = contexto.socket(zmq.REQ)
    socket.connect(DIRECCION_GC)

    banner()

    # Solicitud de DEVOLUCIÓN (ejemplo)
    solicitud_devolucion = {
        "operation": "devolucion",
        "book_code": "ISBN123",
        "user_id": "usuario01",
    }
    print_bloque_envio("DEVOLUCIÓN", solicitud_devolucion)
    socket.send_string(json.dumps(solicitud_devolucion))
    respuesta = socket.recv_string()
    print_bloque_respuesta(respuesta)

    # Solicitud de RENOVACIÓN (ejemplo)
    solicitud_renovacion = {
        "operation": "renovacion",
        "book_code": "ISBN456",
        "user_id": "usuario02",
    }
    print_bloque_envio("RENOVACIÓN", solicitud_renovacion)
    socket.send_string(json.dumps(solicitud_renovacion))
    respuesta = socket.recv_string()
    print_bloque_respuesta(respuesta)

    # Cierre ordenado
    socket.close()
    contexto.term()
    print("PS de prueba: finalizado.\n")

if __name__ == "__main__":
    main()
