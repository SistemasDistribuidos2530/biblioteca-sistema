#!/usr/bin/env python3
# archivo: pruebas/test_actor_failure.py
#
# Universidad: Pontificia Universidad Javeriana
# Materia: INTRODUCCIÓN A SISTEMAS DISTRIBUIDOS
# Profesor: Rafael Páez Méndez
# Integrantes: Thomas Arévalo, Santiago Mesa, Diego Castrillón
# Fecha: 13 de noviembre de 2025
#
# Prueba de fallo: Caída de Actor
# Simula la caída de un actor durante procesamiento y mide impacto.

import os
import sys
import time
import signal
import json
import subprocess
from pathlib import Path
from datetime import datetime

try:
    import psutil
except ImportError:
    print("Instalando psutil...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

def iso():
    """Retorna timestamp ISO-8601."""
    return datetime.utcnow().isoformat() + "Z"

def print_banner():
    """Imprime banner de inicio."""
    print("\n" + "=" * 72)
    print(" TEST DE FALLOS: CAÍDA DE ACTOR ".center(72, " "))
    print("-" * 72)
    print("  Universidad: Pontificia Universidad Javeriana")
    print("  Materia    : Sistemas Distribuidos")
    print("=" * 72 + "\n")

def find_actor_process(actor_name):
    """
    Encuentra el PID del proceso de un actor por nombre.
    actor_name: 'renovacion', 'devolucion', 'prestamo'
    """
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and any(f'actor_{actor_name}.py' in arg for arg in cmdline):
                return proc.info['pid'], proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None, None

def kill_actor(actor_name):
    """Mata un actor específico."""
    print(f"\n[{iso()}] Buscando proceso actor_{actor_name}...")

    pid, proc = find_actor_process(actor_name)

    if pid is None:
        print(f"⚠️  No se encontró proceso para actor_{actor_name}.py")
        print("   Asegúrate de que el actor esté corriendo")
        return False

    print(f"✓ Proceso encontrado: PID {pid}")
    print(f"  Terminando actor_{actor_name} (PID {pid})...")

    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
            print(f"✓ Actor terminado exitosamente")
        except psutil.TimeoutExpired:
            print(f"⚠️  Timeout al esperar, forzando kill...")
            proc.kill()
            print(f"✓ Actor forzado a terminar")
        return True
    except Exception as e:
        print(f"❌ Error al terminar actor: {e}")
        return False

def check_actor_alive(actor_name):
    """Verifica si un actor está corriendo."""
    pid, _ = find_actor_process(actor_name)
    return pid is not None

def count_log_entries(log_file, before_ts, after_ts):
    """
    Cuenta entradas de log entre dos timestamps.
    Retorna número de líneas procesadas en ese intervalo.
    """
    if not os.path.exists(log_file):
        return 0

    count = 0
    with open(log_file, 'r') as f:
        for line in f:
            if before_ts in line or after_ts in line:
                continue
            # Contar líneas entre los timestamps
            count += 1

    return count

def test_actor_failure(actor_name="renovacion"):
    """
    Ejecuta prueba de caída de actor:
    1. Verifica que el actor esté corriendo
    2. Mata el actor
    3. Mide tiempo hasta detección (si hay monitoreo)
    4. Registra métricas de impacto
    """
    print_banner()

    print(f"Actor objetivo: actor_{actor_name}")
    print(f"Log esperado  : log_actor_{actor_name}.txt")

    # Verificar estado inicial
    print("\n" + "-" * 72)
    print(" PASO 1: Verificar estado inicial ".center(72, " "))
    print("-" * 72)

    if not check_actor_alive(actor_name):
        print(f"\n❌ ERROR: actor_{actor_name} no está corriendo")
        print("\nPara ejecutar este test:")
        print(f"  1. Iniciar el actor: python actores/actor_{actor_name}.py &")
        print(f"  2. Ejecutar este test nuevamente")
        return False

    print(f"✓ actor_{actor_name} está corriendo")

    # Timestamp antes de la caída
    ts_before = iso()
    time_before = time.time()

    # Matar el actor
    print("\n" + "-" * 72)
    print(" PASO 2: Simular caída del actor ".center(72, " "))
    print("-" * 72)

    if not kill_actor(actor_name):
        print("\n❌ No se pudo terminar el actor")
        return False

    time_killed = time.time()
    ts_killed = iso()

    # Esperar para observar detección
    print("\n" + "-" * 72)
    print(" PASO 3: Monitorear detección ".center(72, " "))
    print("-" * 72)

    print("\nEsperando 10 segundos para observar comportamiento del sistema...")
    for i in range(10):
        time.sleep(1)
        if (i + 1) % 2 == 0:
            alive = check_actor_alive(actor_name)
            status = "reiniciado" if alive else "caído"
            print(f"  {i + 1}s: actor está {status}")

    time_after = time.time()
    ts_after = iso()

    # Verificar si el actor se reinició automáticamente
    is_alive_after = check_actor_alive(actor_name)

    # Análisis de resultados
    print("\n" + "=" * 72)
    print(" RESULTADOS ".center(72, " "))
    print("=" * 72)

    duracion_caida = time_after - time_killed

    print(f"\n  Timestamp inicial : {ts_before}")
    print(f"  Timestamp caída   : {ts_killed}")
    print(f"  Timestamp final   : {ts_after}")
    print(f"  Duración caída    : {duracion_caida:.2f}s")

    print(f"\n  Estado del actor:")
    print(f"    Antes del test  : ✓ corriendo")
    print(f"    Después del test: {'✓ reiniciado' if is_alive_after else '✗ caído'}")

    # Verificar logs
    log_file = f"log_actor_{actor_name}.txt"
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()

            print(f"\n  Log del actor:")
            print(f"    Archivo         : {log_file}")
            print(f"    Líneas totales  : {len(lines)}")

            # Mostrar últimas líneas
            if lines:
                print(f"\n  Últimas 3 líneas del log:")
                for line in lines[-3:]:
                    print(f"    {line.rstrip()}")
        except Exception as e:
            print(f"  ⚠️  No se pudo leer el log: {e}")
    else:
        print(f"\n  ⚠️  Log no encontrado: {log_file}")

    # Evaluación
    print("\n" + "-" * 72)

    if is_alive_after:
        print("\n✓ RECUPERACIÓN AUTOMÁTICA: El actor se reinició")
        resultado = "RECUPERADO"
    else:
        print("\n⚠️  SIN RECUPERACIÓN: El actor permanece caído")
        print("   Se requiere intervención manual para reiniciar")
        resultado = "CAIDO"

    print("-" * 72)

    # Guardar reporte
    reporte = {
        "test": "actor_failure",
        "timestamp": iso(),
        "actor": actor_name,
        "duracion_caida_s": duracion_caida,
        "recuperacion_automatica": is_alive_after,
        "resultado": resultado,
        "timestamps": {
            "antes": ts_before,
            "caida": ts_killed,
            "despues": ts_after
        }
    }

    reporte_path = Path(__file__).parent / f"reporte_actor_failure_{actor_name}.json"
    with open(reporte_path, "w") as f:
        json.dump(reporte, f, indent=2)

    print(f"\n📄 Reporte guardado en: {reporte_path}\n")

    return True

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test de caída de actor")
    parser.add_argument("--actor", choices=["renovacion", "devolucion", "prestamo"],
                       default="renovacion",
                       help="Actor a probar (default: renovacion)")
    args = parser.parse_args()

    try:
        exito = test_actor_failure(args.actor)
        sys.exit(0 if exito else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrumpido por el usuario\n")
        sys.exit(2)
    except Exception as e:
        print(f"\n\n❌ ERROR INESPERADO: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

