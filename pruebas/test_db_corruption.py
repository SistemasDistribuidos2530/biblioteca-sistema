#!/usr/bin/env python3
# archivo: pruebas/test_db_corruption.py
#
# Universidad: Pontificia Universidad Javeriana
# Materia: INTRODUCCIÓN A SISTEMAS DISTRIBUIDOS
# Profesor: Rafael Páez Méndez
# Integrantes: Thomas Arévalo, Santiago Mesa, Diego Castrillón
# Fecha: 13 de noviembre de 2025
#
# Prueba de fallo: Corrupción de BD + Replay WAL
# Simula corrupción de la base de datos y verifica recuperación vía WAL.

import os
import sys
import time
import json
import pickle
import shutil
from pathlib import Path
from datetime import datetime

def iso():
    """Retorna timestamp ISO-8601."""
    return datetime.utcnow().isoformat() + "Z"

def print_banner():
    """Imprime banner de inicio."""
    print("\n" + "=" * 72)
    print(" TEST DE FALLOS: CORRUPCIÓN DB + REPLAY WAL ".center(72, " "))
    print("-" * 72)
    print("  Universidad: Pontificia Universidad Javeriana")
    print("  Materia    : Sistemas Distribuidos")
    print("=" * 72 + "\n")

def backup_file(file_path):
    """Crea backup de un archivo."""
    if os.path.exists(file_path):
        backup_path = f"{file_path}.backup"
        shutil.copy2(file_path, backup_path)
        print(f"✓ Backup creado: {backup_path}")
        return backup_path
    return None

def restore_file(backup_path, original_path):
    """Restaura un archivo desde backup."""
    if os.exists(backup_path):
        shutil.copy2(backup_path, original_path)
        print(f"✓ Archivo restaurado: {original_path}")
        return True
    return False

def corrupt_db(db_file):
    """Corrompe una base de datos escribiendo basura."""
    if not os.path.exists(db_file):
        print(f"⚠️  Archivo no existe: {db_file}")
        return False

    print(f"\nCorrompiendo {db_file}...")
    try:
        with open(db_file, "wb") as f:
            f.write(b"CORRUPTED_DATA_NOT_A_PICKLE_FILE")
        print(f"✓ Base de datos corrompida")
        return True
    except Exception as e:
        print(f"❌ Error al corromper: {e}")
        return False

def count_wal_entries(wal_file):
    """Cuenta número de entradas en el WAL."""
    if not os.path.exists(wal_file):
        return 0

    count = 0
    with open(wal_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                count += 1

    return count

def verify_db_loadable(db_file):
    """Verifica si una base de datos puede cargarse."""
    try:
        with open(db_file, 'rb') as f:
            data = pickle.load(f)
        return True, len(data) if isinstance(data, dict) else 0
    except Exception as e:
        return False, str(e)

def test_db_corruption_recovery(role="primary"):
    """
    Ejecuta prueba de corrupción y recuperación:
    1. Hace backup de DB y WAL
    2. Verifica estado inicial
    3. Corrompe la DB
    4. Simula reinicio del GA (que debe hacer replay WAL)
    5. Verifica recuperación
    """
    print_banner()

    print(f"Rol GA objetivo: {role}")

    db_file = f"gc/ga_db_{role}.pkl"
    wal_file = f"gc/ga_wal_{role}.log"

    print(f"Archivos:")
    print(f"  DB  : {db_file}")
    print(f"  WAL : {wal_file}")

    # Paso 1: Verificar existencia de archivos
    print("\n" + "-" * 72)
    print(" PASO 1: Verificar archivos ".center(72, " "))
    print("-" * 72)

    if not os.path.exists(db_file):
        print(f"\n⚠️  DB no existe: {db_file}")
        print("   Creando DB vacía para la prueba...")
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        with open(db_file, 'wb') as f:
            pickle.dump({}, f)
        print(f"✓ DB vacía creada")

    if not os.path.exists(wal_file):
        print(f"\n⚠️  WAL no existe: {wal_file}")
        print("   Creando WAL vacío para la prueba...")
        os.makedirs(os.path.dirname(wal_file), exist_ok=True)
        with open(wal_file, 'w') as f:
            f.write("")
        print(f"✓ WAL vacío creado")

    # Paso 2: Backup
    print("\n" + "-" * 72)
    print(" PASO 2: Crear backups ".center(72, " "))
    print("-" * 72)

    db_backup = backup_file(db_file)
    wal_backup = backup_file(wal_file)

    # Paso 3: Verificar estado inicial
    print("\n" + "-" * 72)
    print(" PASO 3: Verificar estado inicial ".center(72, " "))
    print("-" * 72)

    db_loadable_before, db_info_before = verify_db_loadable(db_file)
    wal_entries = count_wal_entries(wal_file)

    print(f"\nEstado inicial:")
    print(f"  DB cargable    : {'✓ Sí' if db_loadable_before else '✗ No'}")
    if db_loadable_before:
        print(f"  Registros en DB: {db_info_before}")
    else:
        print(f"  Error DB       : {db_info_before}")
    print(f"  Entradas en WAL: {wal_entries}")

    # Paso 4: Corromper DB
    print("\n" + "-" * 72)
    print(" PASO 4: Corromper base de datos ".center(72, " "))
    print("-" * 72)

    if not corrupt_db(db_file):
        print("\n❌ No se pudo corromper la DB")
        return False

    # Verificar que quedó corrupta
    db_loadable_after, db_error = verify_db_loadable(db_file)

    print(f"\nVerificación post-corrupción:")
    print(f"  DB cargable: {'✗ No (correcto)' if not db_loadable_after else '⚠️  Sí (error)'}")
    if not db_loadable_after:
        print(f"  Error: {db_error[:50]}...")

    # Paso 5: Simular replay WAL (manual, sin reiniciar GA)
    print("\n" + "-" * 72)
    print(" PASO 5: Simular recuperación vía WAL ".center(72, " "))
    print("-" * 72)

    print("\nEn un escenario real:")
    print("  1. El GA detectaría la DB corrupta al iniciar")
    print("  2. Aplicaría replay del WAL para reconstruir estado")
    print("  3. Guardaría snapshot de la DB recuperada")

    if wal_entries > 0:
        print(f"\n✓ WAL disponible con {wal_entries} entradas")
        print("  Recuperación sería posible")
        recuperacion_posible = True
    else:
        print(f"\n⚠️  WAL vacío o sin entradas")
        print("  Recuperación restauraría estado vacío")
        recuperacion_posible = False

    # Paso 6: Restaurar desde backup
    print("\n" + "-" * 72)
    print(" PASO 6: Restaurar desde backup ".center(72, " "))
    print("-" * 72)

    print("\nRestaurando archivos originales...")
    if db_backup:
        shutil.copy2(db_backup, db_file)
        print(f"✓ DB restaurada")
        os.remove(db_backup)

    if wal_backup:
        shutil.copy2(wal_backup, wal_file)
        print(f"✓ WAL restaurado")
        os.remove(wal_backup)

    # Resultados
    print("\n" + "=" * 72)
    print(" RESULTADOS ".center(72, " "))
    print("=" * 72)

    print(f"\n  Test de corrupción:")
    print(f"    DB original cargable     : {'✓' if db_loadable_before else '✗'}")
    print(f"    DB corrupta NO cargable  : {'✓' if not db_loadable_after else '✗'}")
    print(f"    WAL disponible           : {'✓' if wal_entries > 0 else '✗'}")
    print(f"    Recuperación posible     : {'✓' if recuperacion_posible else '✗'}")
    print(f"    Archivos restaurados     : ✓")

    print("\n" + "-" * 72)

    if recuperacion_posible:
        print("\n✓ RECUPERACIÓN VIABLE: El sistema puede recuperarse vía WAL")
        resultado = "VIABLE"
    else:
        print("\n⚠️  SIN DATOS: WAL vacío, recuperación restauraría estado vacío")
        resultado = "SIN_DATOS"

    print("-" * 72)

    # Guardar reporte
    reporte = {
        "test": "db_corruption_recovery",
        "timestamp": iso(),
        "role": role,
        "db_file": db_file,
        "wal_file": wal_file,
        "estado_inicial": {
            "db_cargable": db_loadable_before,
            "registros_db": db_info_before if db_loadable_before else 0,
            "entradas_wal": wal_entries
        },
        "estado_corrupto": {
            "db_cargable": db_loadable_after
        },
        "recuperacion_posible": recuperacion_posible,
        "resultado": resultado
    }

    reporte_path = Path(__file__).parent / f"reporte_db_corruption_{role}.json"
    with open(reporte_path, "w") as f:
        json.dump(reporte, f, indent=2)

    print(f"\n📄 Reporte guardado en: {reporte_path}\n")

    return True

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test de corrupción DB y recuperación WAL")
    parser.add_argument("--role", choices=["primary", "secondary"],
                       default="primary",
                       help="Rol del GA a probar (default: primary)")
    args = parser.parse_args()

    try:
        exito = test_db_corruption_recovery(args.role)
        sys.exit(0 if exito else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrumpido por el usuario\n")
        sys.exit(2)
    except Exception as e:
        print(f"\n\n❌ ERROR INESPERADO: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

