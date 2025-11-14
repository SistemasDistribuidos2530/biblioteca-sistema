#!/usr/bin/env python3
# archivo: scripts/generate_db.py
#
# Universidad: Pontificia Universidad Javeriana
# Materia: INTRODUCCIÓN A SISTEMAS DISTRIBUIDOS
# Profesor: Rafael Páez Méndez
# Integrantes: Thomas Arévalo, Santiago Mesa, Diego Castrillón
# Fecha: 13 de noviembre de 2025
#
# Generador de base de datos inicial para el sistema.
# Crea DB primaria y secundaria con 1000 libros y distribución de préstamos.

import os
import sys
import pickle
import random
import argparse
from pathlib import Path
from datetime import datetime, timedelta

def iso():
    """Retorna timestamp ISO-8601."""
    return datetime.utcnow().isoformat() + "Z"

def print_banner():
    """Imprime banner de inicio."""
    print("\n" + "=" * 72)
    print(" GENERADOR DE BASE DE DATOS INICIAL ".center(72, " "))
    print("-" * 72)
    print("  Universidad: Pontificia Universidad Javeriana")
    print("  Materia    : Sistemas Distribuidos")
    print("=" * 72 + "\n")

# Datos de ejemplo para títulos de libros
CATEGORIAS = [
    "Ficción", "Ciencia", "Historia", "Tecnología", "Arte",
    "Filosofía", "Matemáticas", "Física", "Química", "Biología"
]

PREFIJOS = [
    "Introducción a", "Fundamentos de", "Teoría de", "Práctica de",
    "Manual de", "Guía de", "Compendio de", "Tratado de"
]

def generar_titulo(book_id):
    """Genera un título de libro pseudo-aleatorio pero reproducible."""
    random.seed(book_id)  # Reproducible

    categoria = random.choice(CATEGORIAS)
    prefijo = random.choice(PREFIJOS)

    if random.random() < 0.5:
        titulo = f"{prefijo} {categoria}"
    else:
        titulo = f"{categoria}: {random.choice(['Conceptos', 'Aplicaciones', 'Teoría', 'Práctica'])}"

    return titulo

def generar_db(num_libros, prestados_sede1, prestados_sede2, seed=None):
    """
    Genera base de datos con libros.

    Parámetros:
    - num_libros: Total de libros en el catálogo
    - prestados_sede1: Número de libros prestados en Sede 1
    - prestados_sede2: Número de libros prestados en Sede 2
    - seed: Semilla para reproducibilidad

    Estructura de cada libro:
    {
        "code": "BOOK-001",
        "title": "Título del libro",
        "available": 3,  # Copias disponibles
        "loans": {
            "user_id": {
                "due": "2025-12-01T00:00:00Z",
                "renovations": 0
            }
        }
    }
    """
    if seed is not None:
        random.seed(seed)

    db = {}

    # Generar todos los libros
    for i in range(1, num_libros + 1):
        book_code = f"BOOK-{i:03d}"
        titulo = generar_titulo(i)

        # Cada libro tiene entre 1 y 5 copias
        copias_totales = random.randint(1, 5)

        db[book_code] = {
            "code": book_code,
            "title": titulo,
            "available": copias_totales,
            "loans": {}
        }

    # Asignar préstamos a Sede 1
    libros_ids = list(range(1, num_libros + 1))
    random.shuffle(libros_ids)

    for i in range(min(prestados_sede1, num_libros)):
        book_id = libros_ids[i]
        book_code = f"BOOK-{book_id:03d}"

        # Usuario aleatorio (1-50 para Sede 1)
        user_id = random.randint(1, 50)

        # Fecha de vencimiento: 7-30 días desde hoy
        dias_hasta_venc = random.randint(7, 30)
        due_date = datetime.utcnow() + timedelta(days=dias_hasta_venc)

        # Número de renovaciones (0-2)
        renovaciones = random.randint(0, 2)

        # Reducir copias disponibles
        if db[book_code]["available"] > 0:
            db[book_code]["available"] -= 1

        # Registrar préstamo
        db[book_code]["loans"][str(user_id)] = {
            "due": due_date.isoformat() + "Z",
            "renovations": renovaciones
        }

    # Asignar préstamos a Sede 2
    for i in range(prestados_sede1, min(prestados_sede1 + prestados_sede2, num_libros)):
        book_id = libros_ids[i]
        book_code = f"BOOK-{book_id:03d}"

        # Usuario aleatorio (51-100 para Sede 2)
        user_id = random.randint(51, 100)

        dias_hasta_venc = random.randint(7, 30)
        due_date = datetime.utcnow() + timedelta(days=dias_hasta_venc)

        renovaciones = random.randint(0, 2)

        if db[book_code]["available"] > 0:
            db[book_code]["available"] -= 1

        db[book_code]["loans"][str(user_id)] = {
            "due": due_date.isoformat() + "Z",
            "renovations": renovaciones
        }

    return db

def guardar_db(db, output_path):
    """Guarda la base de datos en formato pickle."""
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "wb") as f:
        pickle.dump(db, f)

    print(f"✓ DB guardada: {output_path}")

def mostrar_estadisticas(db, nombre="DB"):
    """Muestra estadísticas de la base de datos."""
    total_libros = len(db)
    total_prestamos = sum(len(libro["loans"]) for libro in db.values())
    total_copias = sum(libro["available"] for libro in db.values())

    libros_con_prestamos = sum(1 for libro in db.values() if len(libro["loans"]) > 0)

    print(f"\n  {nombre}:")
    print(f"    Total de libros       : {total_libros}")
    print(f"    Libros con préstamos  : {libros_con_prestamos}")
    print(f"    Total de préstamos    : {total_prestamos}")
    print(f"    Copias disponibles    : {total_copias}")

def main():
    parser = argparse.ArgumentParser(description="Generador de BD inicial")
    parser.add_argument("--num-libros", type=int, default=1000,
                       help="Número total de libros (default: 1000)")
    parser.add_argument("--prestados-sede1", type=int, default=50,
                       help="Libros prestados en Sede 1 (default: 50)")
    parser.add_argument("--prestados-sede2", type=int, default=150,
                       help="Libros prestados en Sede 2 (default: 150)")
    parser.add_argument("--seed", type=int,
                       help="Semilla para reproducibilidad (opcional)")
    parser.add_argument("--output-dir", default="gc",
                       help="Directorio de salida (default: gc)")

    args = parser.parse_args()

    print_banner()

    print(f"Configuración:")
    print(f"  Total de libros       : {args.num_libros}")
    print(f"  Prestados Sede 1      : {args.prestados_sede1}")
    print(f"  Prestados Sede 2      : {args.prestados_sede2}")
    print(f"  Semilla               : {args.seed if args.seed else 'aleatoria'}")
    print(f"  Directorio salida     : {args.output_dir}")

    # Generar DB
    print(f"\n[{iso()}] Generando base de datos...")

    db = generar_db(
        args.num_libros,
        args.prestados_sede1,
        args.prestados_sede2,
        args.seed
    )

    # Mostrar estadísticas
    mostrar_estadisticas(db, "Base de Datos Generada")

    # Guardar DB primaria y secundaria (inicialmente idénticas)
    print(f"\n[{iso()}] Guardando archivos...")

    primary_path = os.path.join(args.output_dir, "ga_db_primary.pkl")
    secondary_path = os.path.join(args.output_dir, "ga_db_secondary.pkl")

    guardar_db(db, primary_path)
    guardar_db(db, secondary_path)

    # Inicializar WALs vacíos
    primary_wal = os.path.join(args.output_dir, "ga_wal_primary.log")
    secondary_wal = os.path.join(args.output_dir, "ga_wal_secondary.log")

    os.makedirs(args.output_dir, exist_ok=True)

    with open(primary_wal, "w") as f:
        f.write("")  # WAL vacío
    print(f"✓ WAL creado: {primary_wal}")

    with open(secondary_wal, "w") as f:
        f.write("")  # WAL vacío
    print(f"✓ WAL creado: {secondary_wal}")

    # Resumen
    print("\n" + "=" * 72)
    print(" GENERACIÓN COMPLETADA ".center(72, " "))
    print("=" * 72)

    print(f"\n  Archivos generados:")
    print(f"    {primary_path}")
    print(f"    {secondary_path}")
    print(f"    {primary_wal}")
    print(f"    {secondary_wal}")

    print(f"\n  Próximos pasos:")
    print(f"    1. Iniciar GA primario y secundario")
    print(f"    2. Enviar solicitudes al sistema")
    print(f"    3. Los WALs se llenarán con operaciones")

    print("\n" + "=" * 72 + "\n")

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrumpido por el usuario\n")
        sys.exit(2)
    except Exception as e:
        print(f"\n\n❌ ERROR INESPERADO: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

