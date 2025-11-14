#!/usr/bin/env python3
# 
# Gestor Administrador (GA) simple:
# - REQ/REP para atender solicitudes de actores/monitor ("ping" -> "pong")
# - Persistencia via pickle (db file)
# - WAL (jsonlines) + replay al inicio
# - Si role==primary -> envía replicación asíncrona (PUSH) a secondary
# - Si role==secondary -> escucha replicación (PULL) y aplica
#
# Config via env:
#  GA_ROLE (primary|secondary) default primary
#  GA_BIND (REQ/REP bind)   default tcp://0.0.0.0:6000
#  GA_DB_FILE               default gc/ga_db_{role}.pkl
#  GA_WAL_FILE              default gc/ga_wal_{role}.log
#  GA_REPL_PUSH_ADDR        (si primary) default tcp://localhost:7001
#  GA_REPL_PULL_BIND        (si secondary) default tcp://0.0.0.0:7001
#
import os
import sys
import json
import zmq
import time
import signal
import pickle
from datetime import datetime

# ----------------- Configuración por defecto (se pueden override con env) -----------------
ROLE = os.getenv("GA_ROLE", "primary").lower()   # 'primary' or 'secondary'
# Determinar bind según rol: primary usa 6000, secondary usa 6001
if ROLE == "secondary":
    GA_BIND = os.getenv("GA_SECONDARY_BIND", os.getenv("GA_BIND", "tcp://0.0.0.0:6001"))
else:
    GA_BIND = os.getenv("GA_PRIMARY_BIND", os.getenv("GA_BIND", "tcp://0.0.0.0:6000"))
DB_FILE = os.getenv("GA_DB_FILE", f"gc/ga_db_{ROLE}.pkl")
WAL_FILE = os.getenv("GA_WAL_FILE", f"gc/ga_wal_{ROLE}.log")
REPL_PUSH_ADDR = os.getenv("GA_REPL_PUSH_ADDR", "tcp://localhost:7001")   # uso en primary
REPL_PULL_BIND = os.getenv("GA_REPL_PULL_BIND", "tcp://0.0.0.0:7001")     # uso en secondary
REQ_TIMEOUT_MS = int(os.getenv("GA_REQ_TIMEOUT_MS", "5000"))

# ----------------- Helpers -----------------
def iso():
    return datetime.utcnow().isoformat() + "Z"

def ensure_dirs():
    os.makedirs(os.path.dirname(DB_FILE) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(WAL_FILE) or ".", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

def atomic_append(path, text):
    # append text + newline and fsync to ensure durability for WAL
    with open(path, "a", encoding="utf-8") as f:
        f.write(text + "\n")
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass

def load_db():
    try:
        with open(DB_FILE, "rb") as f:
            db = pickle.load(f)
            print(f"[{iso()}] DB cargada desde {DB_FILE} ({len(db)} libros)")
            return db
    except FileNotFoundError:
        print(f"[{iso()}] No existe DB, inicializando vacía ({DB_FILE})")
        return {}
    except Exception as e:
        print(f"[{iso()}] Error cargando DB: {e}", file=sys.stderr)
        return {}

def save_db(db):
    tmp = DB_FILE + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(db, f)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    os.replace(tmp, DB_FILE)

# ----------------- WAL replay -----------------
def apply_op_to_db(db, op):
    """
    op: dict with fields at least:
    - operacion: 'prestamo'|'renovacion'|'devolucion'
- book_code, user_id, (nueva_fecha) ...
    This function mutates db in place. DB schema (simple):
        db[book_code] = {
        "code": book_code,
        "title": ... optional,
        "available": int,
        "loans": { user_id: {"due": iso_ts, "renovaciones": n } }
        }
    """
    oper = op.get("operacion")
    code = op.get("book_code")
    user = str(op.get("user_id")) if op.get("user_id") is not None else None

    # ensure book record
    if code not in db:
        # create a minimal record (if WAL contains operations for nonexistent items)
        db[code] = {"code": code, "title": op.get("title", ""), "available": 0, "loans": {}}

    record = db[code]

    if oper == "prestamo":
        # create loan entry if available
        if record.get("available", 0) > 0:
            record["available"] = record.get("available", 0) - 1
            # set due date
            due = op.get("due") or op.get("nueva_fecha") or op.get("recv_ts") or iso()
            record["loans"][user] = {"due": due, "renovaciones": 0}
            return {"estado": "ok", "mensaje": "prestamo aplicado (replay)"}
        else:
            # if replay and not available, still keep consistency: mark as failed
            return {"estado": "error", "mensaje": "no hay ejemplares (replay)"}

    elif oper == "renovacion":
        loan = record.get("loans", {}).get(user)
        if not loan:
            return {"estado": "error", "mensaje": "prestamo no encontrado (replay)"}
        renov = loan.get("renovaciones", 0)
        if renov >= 2:
            return {"estado": "error", "mensaje": "max renovaciones (replay)"}
        # set nueva fecha if provided
        nueva = op.get("nueva_fecha") or iso()
        loan["due"] = nueva
        loan["renovaciones"] = renov + 1
        return {"estado": "ok", "mensaje": "renovacion aplicada (replay)", "nueva_fecha": nueva}

    elif oper == "devolucion":
        # remove loan if existed, increment available
        loan = record.get("loans", {}).pop(user, None)
        record["available"] = record.get("available", 0) + 1
        return {"estado": "ok", "mensaje": "devolucion aplicada (replay)"}

    else:
        return {"estado": "error", "mensaje": f"operacion desconocida en replay: {oper}"}

def replay_wal(db):
    if not os.path.exists(WAL_FILE):
        print(f"[{iso()}] WAL no existe ({WAL_FILE}) — nada que reproducir")
        return
    print(f"[{iso()}] Reproduciendo WAL desde {WAL_FILE} ...")
    applied = 0
    with open(WAL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                # 'entry' expected to have 'op' field or be op directly; support both
                op = entry.get("op") if isinstance(entry, dict) and "op" in entry else entry
                apply_op_to_db(db, op)
                applied += 1
            except Exception as e:
                print(f"[{iso()}] Error replay linea WAL: {e} | linea: {line}", file=sys.stderr)
    print(f"[{iso()}] WAL replay finalizado. Operaciones aplicadas: {applied}")

# ----------------- GA main -----------------
running = True
def handle_signal(sig, frame):
    global running
    print(f"\n[{iso()}] Señal recibida ({sig}). Deteniendo GA...\n")
    running = False

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

def main():
    ensure_dirs()
    print("\n" + "="*72)
    print(" GESTOR ADMINISTRADOR (GA) ".center(72))
    print("-"*72)
    print(f" Role        : {ROLE}")
    print(f" REQ/REP bind: {GA_BIND}")
    print(f" DB file     : {DB_FILE}")
    print(f" WAL file    : {WAL_FILE}")
    if ROLE == "primary":
        print(f" Replicacion -> PUSH to: {REPL_PUSH_ADDR}")
    else:
        print(f" Replicacion PULL bind : {REPL_PULL_BIND}")
    print("="*72 + "\n")

    # ZMQ sockets
    ctx = zmq.Context.instance()
    rep = ctx.socket(zmq.REP)
    rep.bind(GA_BIND)

    # replication sockets
    repl_push = None
    repl_pull = None
    if ROLE == "primary":
        repl_push = ctx.socket(zmq.PUSH)
        # connect to secondary's pull (may fail now, but will retry on send)
        try:
            repl_push.connect(REPL_PUSH_ADDR)
        except Exception:
            print(f"[{iso()}] Aviso: no se pudo conectar a {REPL_PUSH_ADDR} (se reintentará en cada envío)")

    else:
        repl_pull = ctx.socket(zmq.PULL)
        repl_pull.bind(REPL_PULL_BIND)

    # DB + WAL replay
    db = load_db()
    replay_wal(db)
    # after replay, persist current db snapshot
    save_db(db)

    # poller: REP + (si secondary) PULL
    poller = zmq.Poller()
    poller.register(rep, zmq.POLLIN)
    if repl_pull:
        poller.register(repl_pull, zmq.POLLIN)

    # auxiliar: apply and persist (with WAL)
    def process_and_persist(op_payload):
        # 1) write wal line (op)
        wal_entry = {"ts": iso(), "op": op_payload}
        try:
            atomic_append(WAL_FILE, json.dumps(wal_entry))
        except Exception as e:
            print(f"[{iso()}] ERROR escribiendo WAL: {e}", file=sys.stderr)
            return {"estado":"error","mensaje":"error_wal","detalle":str(e)}

        # 2) apply to local db
        res = apply_op_to_db(db, op_payload)
        # 3) persist snapshot (pickle)
        try:
            save_db(db)
        except Exception as e:
            print(f"[{iso()}] ERROR guardando DB: {e}", file=sys.stderr)

        return res

    # main loop
    while running:
        try:
            events = dict(poller.poll(500))
            # --------------- replication messages (secondary) ---------------
            if repl_pull and repl_pull in events:
                try:
                    raw = repl_pull.recv_string(flags=zmq.NOBLOCK)
                    try:
                        payload = json.loads(raw)
                    except Exception:
                        print(f"[{iso()}] Replicacion: payload no JSON: {raw}", file=sys.stderr)
                        continue
                    # apply op directly (we also write to WAL and save DB)
                    print(f"[{iso()}] Replicacion recibida: {payload.get('op', payload)}")
                    # payload expected to be wal_entry or op; normalize
                    op = payload.get("op") if isinstance(payload, dict) and "op" in payload else payload
                    # write WAL and apply
                    res = process_and_persist(op)
                    # no reply expected for replication
                except zmq.Again:
                    pass
                except Exception as e:
                    print(f"[{iso()}] Error procesando replicacion: {e}", file=sys.stderr)

            # --------------- requests (actors / monitor) ---------------
            if rep in events:
                raw = rep.recv_string()
                # ping from monitor
                if isinstance(raw, str) and raw.strip().lower() == "ping":
                    rep.send_string("pong")
                    continue

                # otherwise expect JSON payload for operation
                try:
                    payload = json.loads(raw)
                except Exception:
                    # malformed -> error reply
                    rep.send_string(json.dumps({"estado":"error","mensaje":"payload no JSON"}))
                    continue

                oper = payload.get("operacion")
                # basic validation
                if not oper:
                    rep.send_string(json.dumps({"estado":"error","mensaje":"operacion faltante"}))
                    continue

                # Si primary -> aplicar localmente y replicar asíncronamente
                if ROLE == "primary":
                    # process + persist locally (WAL + pickle)
                    result = process_and_persist(payload)
                    # intentar enviar replicacion asíncrona al secondary (no bloqueante)
                    try:
                        if repl_push:
                            # envia la misma estructura de WAL para que el secundario escriba su WAL y aplique
                            wal_entry = {"ts": iso(), "op": payload}
                            repl_push.send_string(json.dumps(wal_entry), flags=0)
                    except Exception as e:
                        # no fatal; informativo en logs
                        print(f"[{iso()}] Aviso: fallo al enviar replicacion: {e}", file=sys.stderr)
                    # enviar respuesta al actor (result como JSON)
                    rep.send_string(json.dumps(result))
                    continue

                # Si secondary -> se asume que actua cuando primario no está (monitor lo marca en gc/ga_activo.txt)
                # Podemos aplicar la operación localmente (será eventualmente la nueva fuente) y no replicar.
                else:
                    result = process_and_persist(payload)
                    rep.send_string(json.dumps(result))
                    continue

        except zmq.ZMQError as e:
            # errores ZMQ -> log y continue
            print(f"[{iso()}] ZMQError en loop: {e}", file=sys.stderr)
            time.sleep(0.1)
        except Exception as e:
            print(f"[{iso()}] ERROR inesperado en loop: {e}", file=sys.stderr)
            time.sleep(0.1)

    # cierre ordenado
    try:
        rep.close(linger=0)
        if repl_push: repl_push.close(linger=0)
        if repl_pull: repl_pull.close(linger=0)
        ctx.term()
    except Exception:
        pass

    print(f"[{iso()}] GA detenido correctamente.")

if __name__ == "__main__":
    main()
