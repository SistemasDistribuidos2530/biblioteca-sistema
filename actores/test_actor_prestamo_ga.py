#!/usr/bin/env python3
# Test de validación para actor_prestamo.py con ga_activo.txt
# Verifica que el actor lee correctamente el archivo y selecciona el GA apropiado.

import os
import sys
from pathlib import Path

# Agregar path para importar el actor
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def test_leer_ga_activo():
    """
    Prueba la función leer_ga_activo() del actor_prestamo.
    """
    from actores.actor_prestamo import leer_ga_activo, ga_addr_actual, GA_PRIMARY, GA_SECONDARY, FILE_GA_ACTIVO
    
    print("=" * 72)
    print(" TEST: actor_prestamo.py - Lectura de ga_activo.txt ".center(72))
    print("=" * 72)
    
    # Asegurar que existe el directorio gc/
    os.makedirs(os.path.dirname(FILE_GA_ACTIVO), exist_ok=True)
    
    # Test 1: Archivo no existe (debe retornar "primary")
    if os.path.exists(FILE_GA_ACTIVO):
        os.remove(FILE_GA_ACTIVO)
    
    resultado = leer_ga_activo()
    addr = ga_addr_actual()
    print(f"\nTest 1: Archivo no existe")
    print(f"  Resultado esperado: 'primary'")
    print(f"  Resultado obtenido: '{resultado}'")
    print(f"  Dirección GA      : {addr}")
    assert resultado == "primary", f"FALLO: esperaba 'primary', obtuvo '{resultado}'"
    assert addr == GA_PRIMARY, f"FALLO: esperaba {GA_PRIMARY}, obtuvo {addr}"
    print("PASS")
    
    # Test 2: Archivo contiene "primary"
    with open(FILE_GA_ACTIVO, "w") as f:
        f.write("primary")
    
    resultado = leer_ga_activo()
    addr = ga_addr_actual()
    print(f"\nTest 2: Archivo contiene 'primary'")
    print(f"  Resultado esperado: 'primary'")
    print(f"  Resultado obtenido: '{resultado}'")
    print(f"  Dirección GA      : {addr}")
    assert resultado == "primary", f"FALLO: esperaba 'primary', obtuvo '{resultado}'"
    assert addr == GA_PRIMARY, f"FALLO: esperaba {GA_PRIMARY}, obtuvo {addr}"
    print("PASS")
    
    # Test 3: Archivo contiene "secondary"
    with open(FILE_GA_ACTIVO, "w") as f:
        f.write("secondary")
    
    resultado = leer_ga_activo()
    addr = ga_addr_actual()
    print(f"\nTest 3: Archivo contiene 'secondary'")
    print(f"  Resultado esperado: 'secondary'")
    print(f"  Resultado obtenido: '{resultado}'")
    print(f"  Dirección GA      : {addr}")
    assert resultado == "secondary", f"FALLO: esperaba 'secondary', obtuvo '{resultado}'"
    assert addr == GA_SECONDARY, f"FALLO: esperaba {GA_SECONDARY}, obtuvo {addr}"
    print("PASS")
    
    # Test 4: Archivo contiene "SECONDARY" (mayúsculas)
    with open(FILE_GA_ACTIVO, "w") as f:
        f.write("SECONDARY")
    
    resultado = leer_ga_activo()
    addr = ga_addr_actual()
    print(f"\nTest 4: Archivo contiene 'SECONDARY' (mayúsculas)")
    print(f"  Resultado esperado: 'secondary'")
    print(f"  Resultado obtenido: '{resultado}'")
    print(f"  Dirección GA      : {addr}")
    assert resultado == "secondary", f"FALLO: esperaba 'secondary', obtuvo '{resultado}'"
    assert addr == GA_SECONDARY, f"FALLO: esperaba {GA_SECONDARY}, obtuvo {addr}"
    print("PASS")
    
    # Test 5: Archivo contiene valor inválido (debe retornar "primary")
    with open(FILE_GA_ACTIVO, "w") as f:
        f.write("invalid_value")
    
    resultado = leer_ga_activo()
    addr = ga_addr_actual()
    print(f"\nTest 5: Archivo contiene valor inválido")
    print(f"  Resultado esperado: 'primary' (fallback)")
    print(f"  Resultado obtenido: '{resultado}'")
    print(f"  Dirección GA      : {addr}")
    assert resultado == "primary", f"FALLO: esperaba 'primary', obtuvo '{resultado}'"
    assert addr == GA_PRIMARY, f"FALLO: esperaba {GA_PRIMARY}, obtuvo {addr}"
    print("PASS")
    
    # Test 6: Archivo contiene espacios en blanco
    with open(FILE_GA_ACTIVO, "w") as f:
        f.write("  secondary  \n")
    
    resultado = leer_ga_activo()
    addr = ga_addr_actual()
    print(f"\nTest 6: Archivo contiene espacios en blanco")
    print(f"  Resultado esperado: 'secondary'")
    print(f"  Resultado obtenido: '{resultado}'")
    print(f"  Dirección GA      : {addr}")
    assert resultado == "secondary", f"FALLO: esperaba 'secondary', obtuvo '{resultado}'"
    assert addr == GA_SECONDARY, f"FALLO: esperaba {GA_SECONDARY}, obtuvo {addr}"
    print("PASS")
    
    # Limpiar archivo de prueba
    if os.path.exists(FILE_GA_ACTIVO):
        os.remove(FILE_GA_ACTIVO)
    
    print("\n" + "=" * 72)
    print(" TODOS LOS TESTS PASARON ".center(72))
    print("=" * 72)
    print("\nactor_prestamo.py lee correctamente ga_activo.txt")
    print("Conmuta correctamente entre GA primary y secondary")
    print("Maneja casos edge (archivo no existe, valores inválidos, espacios)")
    print()

if __name__ == "__main__":
    try:
        test_leer_ga_activo()
    except AssertionError as e:
        print(f"\nTEST FALLIDO: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR INESPERADO: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

