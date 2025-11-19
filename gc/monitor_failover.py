#!/usr/bin/env python3
# archivo: gc/monitor_failover.py
#
# Monitor de failover para GA primario/secundario.
# - Envía "ping" al GA primario cada 2 segundos (REQ/REP).
# - Si el primario falla 3 pings consecutivos escribe "secondary" en gc/ga_activo.txt.
# - Si el primario vuelve a responder escribe "primary" en gc/ga_activo.txt.
# - Registra cambios en consola y en logs/monitor_failover.log con timestamps ISO.
#
# Uso:
#   python gc/monitor_failover.py

import zmq
import time
import os
import signal
import sys
import logging
from datetime import datetime

# ---------- Configuración desde entorno ----------
# Direcciones del GA primario (M1) y secundario (M2)
# Por defecto: primary en M1 (10.43.101.220:6000), secondary local o en M2
GA_PRIMARY_ADDR = os.getenv("GA_PRIMARY_ADDR", "tcp://10.43.101.220:6000")
GA_SECONDARY_ADDR = os.getenv("GA_SECONDARY_ADDR", "tcp://localhost:6001")
FILE_STATUS = "gc/ga_activo.txt"
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "monitor_failover.log")

# ---------- Parámetros del monitor ----------
PING_INTERVAL = 2.0           # segundos entre pings
FAILURE_THRESHOLD = 3         # fallos consecutivos para conmutar
REQ_TIMEOUT_MS = 1500         # timeout recv/send en ms para socket REQ

# ---------- Estado global ----------
running = True

# ---------- Utilidades ----------
def iso():
    """Timestamp ISO-8601 (UTC) con sufijo Z."""
    return datetime.utcnow().isoformat() + "Z"

def ensure_dirs():
    """Crear directorios necesarios (gc y logs)."""
    os.makedirs(os.path.dirname(FILE_STATUS) or ".", exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

def atomic_write(path, text):
    """Escribe texto en path de forma (prácticamente) atómica."""
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)

def read_status_file():
    """Lee el contenido actual del archivo de estado si existe."""
    try:
        with open(FILE_STATUS, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None
    except Exception:
        return None

def write_status_if_changed(status, logger):
    """
    Escribe 'primary' o 'secondary' en FILE_STATUS solo si cambió.
    Loggea el cambio con timestamp ISO.
    """
    current = read_status_file()
    if current == status:
        return False
    try:
        atomic_write(FILE_STATUS, status)
    except Exception as e:
        logger.error(f"{iso()} Error escribiendo {FILE_STATUS}: {e}")
        return False
    logger.info(f"{iso()} Estado GA actualizado a '{status}'")
    # También print corto en consola para visibilidad inmediata.
    print(f"[{iso()}] Estado GA actualizado a '{status}'")
    return True

# ---------- Logging ----------
def setup_logger():
    """Configura logger con salida a consola y archivo."""
    logger = logging.getLogger("monitor_failover")
    logger.setLevel(logging.INFO)

    # Evitar duplicar handlers si se importa/reinicia.
    if logger.handlers:
        return logger

    # Formato simple. Incluimos timestamp manualmente en los mensajes
    # para que coincida con el formato requerido en el enunciado.
    formatter = logging.Formatter("%(message)s")

    # File handler
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Console handler (stderr)
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

# ---------- Señales ----------
def handle_signal(sig, frame):
    global running
    print(f"\n[{iso()}] Señal recibida ({sig}). Deteniendo monitor...\n")
    running = False

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

# ---------- Lógica principal ----------

def _primary_candidates():
    # Construir lista de direcciones candidatas para el ping primario (manejo IPv4/IPv6)
    addrs = []
    addrs.append(GA_PRIMARY_ADDR)
    try:
        # Si host es localhost, añadir 127.0.0.1:port
        if GA_PRIMARY_ADDR.startswith("tcp://"):
            hostport = GA_PRIMARY_ADDR[len("tcp://"):]
            host, port = hostport.rsplit(":", 1)
            if host in ("localhost", "127.0.0.1"):
                addrs.append(f"tcp://127.0.0.1:{port}")
                addrs.append(f"tcp://localhost:{port}")
    except Exception:
        pass
    # Quitar duplicados preservando orden
    seen = set(); uniq = []
    for a in addrs:
        if a not in seen:
            uniq.append(a); seen.add(a)
    return uniq

def ping_primary_once(logger):
    """
    Intenta enviar 'ping' al GA primario y recibir 'pong'.
    Retorna True si recibió 'pong', False en caso contrario.
    Intenta también un fallback a 127.0.0.1 si la dirección es localhost.
    """
    ctx = zmq.Context.instance()
    for addr in _primary_candidates():
        sock = None
        try:
            sock = ctx.socket(zmq.REQ)
            sock.setsockopt(zmq.RCVTIMEO, REQ_TIMEOUT_MS)
            sock.setsockopt(zmq.SNDTIMEO, REQ_TIMEOUT_MS)
            sock.connect(addr)
            logger.info(f"{iso()} Intentando ping a {addr}")
            try:
                sock.send_string("ping")
            except zmq.ZMQError as e:
                logger.error(f"{iso()} Error enviando ping a {addr}: {e}")
                continue
            try:
                reply = sock.recv_string()
            except zmq.ZMQError as e:
                logger.warning(f"{iso()} Timeout/recv error esperando pong desde {addr}: {e}")
                continue
            if isinstance(reply, str) and reply.strip().lower() == "pong":
                logger.info(f"{iso()} Pong recibido desde {addr}")
                return True
            else:
                logger.warning(f"{iso()} Respuesta inesperada desde {addr}: {reply!r}")
        except Exception as e:
            logger.error(f"{iso()} Excepción en ping a {addr}: {e}")
        finally:
            if sock is not None:
                try:
                    sock.close(linger=0)
                except Exception:
                    pass
    return False

def main():
    ensure_dirs()
    logger = setup_logger()

    # Log de configuración efectiva para diagnóstico
    logger.info(f"{iso()} Monitor iniciado con GA_PRIMARY_ADDR={GA_PRIMARY_ADDR} GA_SECONDARY_ADDR={GA_SECONDARY_ADDR} FILE_STATUS={FILE_STATUS}")
    print(f"[{iso()}] Monitor: PRIMARY={GA_PRIMARY_ADDR} SECONDARY={GA_SECONDARY_ADDR} status_file={FILE_STATUS}")

    # Estado interno para detección de fallos/recuperación
    consecutive_failures = 0
    currently_primary = None  # None al inicio para forzar escritura inicial

    # Inicial: intentar marcar primary si responde, sino secondary
    try:
        ok = ping_primary_once(logger)
        if ok:
            # Forzar escritura inicial siempre (aunque current sea None)
            try:
                atomic_write(FILE_STATUS, "primary")
                logger.info(f"{iso()} Estado GA actualizado a 'primary'")
                print(f"[{iso()}] Estado GA actualizado a 'primary'")
            except Exception as e:
                logger.error(f"{iso()} Error escribiendo estado inicial: {e}")
            currently_primary = True
            logger.info(f"{iso()} GA primario activo ({GA_PRIMARY_ADDR})")
            print(f"[{iso()}] GA primario activo ({GA_PRIMARY_ADDR})")
        else:
            try:
                atomic_write(FILE_STATUS, "secondary")
                logger.info(f"{iso()} Estado GA actualizado a 'secondary'")
                print(f"[{iso()}] Estado GA actualizado a 'secondary'")
            except Exception as e:
                logger.error(f"{iso()} Error escribiendo estado inicial: {e}")
            currently_primary = False
            logger.info(f"{iso()} GA primario no responde. Usando secundario ({GA_SECONDARY_ADDR})")
            print(f"[{iso()}] GA primario no responde. Usando secundario ({GA_SECONDARY_ADDR})")
            consecutive_failures = FAILURE_THRESHOLD  # estado de fallo
    except Exception as e:
        logger.error(f"{iso()} Error inicial comprobando primario: {e}")
        try:
            atomic_write(FILE_STATUS, "secondary")
        except Exception:
            pass
        currently_primary = False
        consecutive_failures = FAILURE_THRESHOLD

    # Bucle principal
    while running:
        try:
            ok = ping_primary_once(logger)
            if ok:
                # Se recibió pong
                if not currently_primary:
                    # Si estábamos en secundario, restauramos a primary
                    write_status_if_changed("primary", logger)
                    logger.info(f"{iso()} GA primario restaurado, regresando a modo normal")
                    print(f"[{iso()}] GA primario restaurado, regresando a modo normal")
                    currently_primary = True
                # reset conteo de fallos
                consecutive_failures = 0
            else:
                # Fallo en este intento
                consecutive_failures += 1
                logger.debug(f"{iso()} Fallo ping primario (conteo={consecutive_failures})")
                if consecutive_failures >= FAILURE_THRESHOLD and currently_primary:
                    # Conmutar a secundario
                    write_status_if_changed("secondary", logger)
                    logger.info(f"{iso()} GA primario no responde, conmutando a secundario ({GA_SECONDARY_ADDR})")
                    print(f"[{iso()}] GA primario no responde, conmutando a secundario ({GA_SECONDARY_ADDR})")
                    currently_primary = False

            # Esperar intervalo antes del siguiente ping, pero permitir salida rápida
            slept = 0.0
            while running and slept < PING_INTERVAL:
                time.sleep(0.1)
                slept += 0.1

        except Exception as e:
            # Capturar excepciones inesperadas y continuar el loop
            logger.error(f"{iso()} Excepción en loop principal: {e}")
            # pequeño retardo para evitar spin rápido en caso de error repetido
            time.sleep(0.5)

    # Salida ordenada
    logger.info(f"{iso()} Monitor detenido.")
    print(f"[{iso()}] Monitor detenido.")

if __name__ == "__main__":
    main()