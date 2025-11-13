#!/usr/bin/env python3
# test_failover.py
#
# Script para simular fallos del Gestor Administrador (GA)
# - Mata el proceso del GA primario o secundario
# - Limpia base de datos para probar replay WAL

import os
import signal
import time
import psutil  # pip install psutil

def kill_by_port(port):
    """Encuentra y termina procesos que usan un puerto."""
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port:
                    print(f"Terminando proceso {proc.pid} ({proc.name()}) en puerto {port}")
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        proc.kill()
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    print(f"No se encontró proceso usando el puerto {port}")
    return False

def corrupt_db(role):
    """Borra o daña la base de datos del GA."""
    db_file = f"gc/ga_db_{role}.pkl"
    wal_file = f"gc/ga_wal_{role}.log"

    if os.path.exists(db_file):
        print(f"Corrompiendo base de datos: {db_file}")
        with open(db_file, "wb") as f:
            f.write(b"notapickle")
    else:
        print(f"{db_file} no existe, nada que dañar")

    if os.path.exists(wal_file):
        print(f"WAL disponible ({wal_file}), debería permitir recuperación")

def simulate_failover():
    print("\n=== Simulador de fallo del Gestor ===")
    print("1. Caer GA Primario (puerto 6000)")
    print("2. Caer GA Secundario (puerto 6001)")
    print("3. Corromper DB del Primario")
    print("4. Corromper DB del Secundario")
    print("5. Salir")

    while True:
        opt = input("\nSelecciona opción: ")
        if opt == "1":
            kill_by_port(6000)
        elif opt == "2":
            kill_by_port(6001)
        elif opt == "3":
            corrupt_db("primary")
        elif opt == "4":
            corrupt_db("secondary")
        elif opt == "5":
            print("Saliendo del simulador")
            break
        else:
            print("❌ Opción inválida")

if __name__ == "__main__":
    simulate_failover()
