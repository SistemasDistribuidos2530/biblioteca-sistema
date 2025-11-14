#!/usr/bin/env python3
# archivo: pruebas/test_latency.py
#
# Universidad: Pontificia Universidad Javeriana
# Materia: INTRODUCCIÓN A SISTEMAS DISTRIBUIDOS
# Profesor: Rafael Páez Méndez
# Integrantes: Thomas Arévalo, Santiago Mesa, Diego Castrillón
# Fecha: 13 de noviembre de 2025
#
# Prueba de fallo: Latencia Artificial
# Introduce delays artificiales y mide impacto en el sistema.

import os
import sys
import time
import zmq
import json
from pathlib import Path
from datetime import datetime

# Añadir path para importar módulos del PS
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "biblioteca-clientes" / "ps"))

try:
    from schema import make_request
except ImportError:
    print("⚠️  No se pudo importar schema. Usando payload simple.")
    make_request = None

# Configuración
GC_ADDR = os.getenv("GC_ADDR", "tcp://localhost:5555")
NUM_REQUESTS = int(os.getenv("LATENCY_NUM", "20"))

def iso():
    """Retorna timestamp ISO-8601."""
    return datetime.utcnow().isoformat() + "Z"

def print_banner():
    """Imprime banner de inicio."""
    print("\n" + "=" * 72)
    print(" TEST DE FALLOS: LATENCIA ARTIFICIAL ".center(72, " "))
    print("-" * 72)
    print("  Universidad: Pontificia Universidad Javeriana")
    print("  Materia    : Sistemas Distribuidos")
    print("=" * 72 + "\n")

def send_request_with_timeout(ctx, payload, timeout_ms):
    """Envía una solicitud con timeout específico."""
    sock = ctx.socket(zmq.REQ)
    sock.setsockopt(zmq.RCVTIMEO, timeout_ms)
    sock.setsockopt(zmq.SNDTIMEO, timeout_ms)

    start = time.time()
    estado = "ERROR"

    try:
        sock.connect(GC_ADDR)
        payload_str = json.dumps(payload) if isinstance(payload, dict) else payload
        sock.send_string(payload_str)

        try:
            respuesta = sock.recv_string()
            try:
                resp_obj = json.loads(respuesta)
                estado = resp_obj.get("estado", resp_obj.get("status", "UNKNOWN"))
                if estado.upper() in ("OK", "OKAY"):
                    estado = "OK"
            except:
                estado = "OK" if respuesta else "ERROR"
        except zmq.ZMQError:
            estado = "TIMEOUT"
    except Exception:
        estado = "ERROR"
    finally:
        sock.close(linger=0)

    end = time.time()
    latencia = end - start

    return estado, latencia

def test_with_timeout(ctx, timeout_ms, num_requests=NUM_REQUESTS):
    """
    Ejecuta N solicitudes con un timeout específico.
    Retorna métricas de la prueba.
    """
    print(f"\n  Ejecutando {num_requests} solicitudes con timeout={timeout_ms}ms...")

    resultados = []

    for i in range(num_requests):
        # Generar payload
        if make_request:
            payload = make_request("RENOVACION", i % 100 + 1, i % 10 + 1)
        else:
            payload = {
                "operation": "renovacion",
                "book_code": f"BOOK-{i % 100 + 1}",
                "user_id": i % 10 + 1
            }

        estado, latencia = send_request_with_timeout(ctx, payload, timeout_ms)
        resultados.append({"estado": estado, "latencia_s": latencia})

        if (i + 1) % 5 == 0:
            print(f"    Progreso: {i + 1}/{num_requests}")

    # Calcular métricas
    ok = sum(1 for r in resultados if r["estado"] == "OK")
    timeouts = sum(1 for r in resultados if r["estado"] == "TIMEOUT")
    errores = sum(1 for r in resultados if r["estado"] == "ERROR")

    latencias = [r["latencia_s"] for r in resultados if r["estado"] == "OK"]

    if latencias:
        lat_min = min(latencias)
        lat_max = max(latencias)
        lat_mean = sum(latencias) / len(latencias)
        latencias_sorted = sorted(latencias)
        lat_p50 = latencias_sorted[len(latencias_sorted) // 2]
        lat_p95 = latencias_sorted[int(len(latencias_sorted) * 0.95)] if len(latencias_sorted) > 20 else lat_max
    else:
        lat_min = lat_max = lat_mean = lat_p50 = lat_p95 = 0

    return {
        "timeout_ms": timeout_ms,
        "total": len(resultados),
        "ok": ok,
        "timeouts": timeouts,
        "errores": errores,
        "latencia_min_s": lat_min,
        "latencia_mean_s": lat_mean,
        "latencia_p50_s": lat_p50,
        "latencia_p95_s": lat_p95,
        "latencia_max_s": lat_max
    }

def test_latency_impact():
    """
    Ejecuta pruebas con diferentes timeouts para medir impacto de latencia:
    1. Timeout normal (2000ms)
    2. Timeout bajo (500ms)
    3. Timeout muy bajo (200ms)
    """
    print_banner()

    print(f"GC Target       : {GC_ADDR}")
    print(f"Solicitudes/test: {NUM_REQUESTS}")

    ctx = zmq.Context()

    # Configuraciones de timeout a probar
    timeouts = [
        (2000, "Normal"),
        (1000, "Medio"),
        (500, "Bajo"),
        (200, "Muy Bajo")
    ]

    resultados_tests = []

    for timeout_ms, descripcion in timeouts:
        print("\n" + "=" * 72)
        print(f" TEST: Timeout {descripcion} ({timeout_ms}ms) ".center(72, " "))
        print("=" * 72)

        metricas = test_with_timeout(ctx, timeout_ms, NUM_REQUESTS)
        resultados_tests.append((descripcion, metricas))

        print(f"\n  Resultados:")
        print(f"    OK       : {metricas['ok']} ({metricas['ok']/metricas['total']*100:.1f}%)")
        print(f"    TIMEOUT  : {metricas['timeouts']} ({metricas['timeouts']/metricas['total']*100:.1f}%)")
        print(f"    ERROR    : {metricas['errores']}")

        if metricas['ok'] > 0:
            print(f"\n  Latencias (solo OK):")
            print(f"    Mín   : {metricas['latencia_min_s']:.3f}s")
            print(f"    Media : {metricas['latencia_mean_s']:.3f}s")
            print(f"    p50   : {metricas['latencia_p50_s']:.3f}s")
            print(f"    p95   : {metricas['latencia_p95_s']:.3f}s")
            print(f"    Máx   : {metricas['latencia_max_s']:.3f}s")

    # Comparación
    print("\n" + "=" * 72)
    print(" COMPARACIÓN DE TIMEOUTS ".center(72, " "))
    print("=" * 72)

    print(f"\n{'Timeout':<15} {'OK%':<10} {'Timeout%':<12} {'Lat Media':<12}")
    print("-" * 72)

    for desc, metricas in resultados_tests:
        timeout_str = f"{metricas['timeout_ms']}ms ({desc})"
        ok_pct = metricas['ok'] / metricas['total'] * 100
        to_pct = metricas['timeouts'] / metricas['total'] * 100
        lat_mean = metricas['latencia_mean_s']

        print(f"{timeout_str:<15} {ok_pct:<10.1f} {to_pct:<12.1f} {lat_mean:<12.3f}")

    # Análisis
    print("\n" + "-" * 72)
    print(" ANÁLISIS ".center(72, " "))
    print("-" * 72)

    # Encontrar el timeout más bajo con 100% OK
    timeout_optimo = None
    for desc, metricas in reversed(resultados_tests):
        if metricas['timeouts'] == 0:
            timeout_optimo = (desc, metricas['timeout_ms'])
            break

    if timeout_optimo:
        print(f"\n✓ Timeout óptimo: {timeout_optimo[1]}ms ({timeout_optimo[0]})")
        print(f"  Sin timeouts en las pruebas")
    else:
        print(f"\n⚠️  Todos los timeouts producen fallos")
        print(f"  El sistema es más lento que los timeouts probados")

    # Detectar degradación
    normal_metricas = resultados_tests[0][1]
    bajo_metricas = resultados_tests[-1][1]

    degradacion_timeouts = bajo_metricas['timeouts'] - normal_metricas['timeouts']

    if degradacion_timeouts > 0:
        print(f"\n⚠️  DEGRADACIÓN DETECTADA:")
        print(f"  Timeouts adicionales con timeout bajo: {degradacion_timeouts}")
        print(f"  El sistema es sensible a timeouts bajos")
    else:
        print(f"\n✓ SIN DEGRADACIÓN:")
        print(f"  El sistema maneja bien diferentes timeouts")

    print("\n" + "-" * 72)

    # Guardar reporte
    reporte = {
        "test": "latencia_artificial",
        "timestamp": iso(),
        "gc_addr": GC_ADDR,
        "solicitudes_por_test": NUM_REQUESTS,
        "tests": [
            {
                "descripcion": desc,
                "metricas": metricas
            }
            for desc, metricas in resultados_tests
        ],
        "timeout_optimo": {
            "descripcion": timeout_optimo[0] if timeout_optimo else None,
            "timeout_ms": timeout_optimo[1] if timeout_optimo else None
        } if timeout_optimo else None,
        "degradacion_timeouts": degradacion_timeouts
    }

    reporte_path = Path(__file__).parent / "reporte_latency.json"
    with open(reporte_path, "w") as f:
        json.dump(reporte, f, indent=2)

    print(f"\n📄 Reporte guardado en: {reporte_path}\n")

    ctx.term()

    return True

if __name__ == "__main__":
    try:
        exito = test_latency_impact()
        sys.exit(0 if exito else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrumpido por el usuario\n")
        sys.exit(2)
    except Exception as e:
        print(f"\n\n❌ ERROR INESPERADO: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

