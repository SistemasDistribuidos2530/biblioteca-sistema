# 📚 Sistema Biblioteca Distribuido - Lado Sistema

**Universidad:** Pontificia Universidad Javeriana  
**Materia:** Sistemas Distribuidos  
**Profesor:** Rafael Páez Méndez  
**Equipo:** Thomas Arévalo, Santiago Mesa, Diego Castrillón  
**Entrega:** 2 (14 noviembre 2025)

---

## 🎯 Descripción

Implementación del **lado servidor** del sistema de biblioteca distribuido:

- **GA (Gestor Administrador)**: Base de datos con replicación primary/secondary y failover automático
- **GC (Gestor de Carga)**: Servidor REQ/REP + PUB/SUB para distribuir solicitudes
- **Actores**: Procesadores asíncronos para renovación, devolución y préstamo
- **Monitor Failover**: Detecta caída del GA primary y conmuta a secondary

---

## 🖥️ Máquinas del Sistema

| Máquina | Rol | IP | Puertos | Componentes |
|---------|-----|-----|---------|-------------|
| **M1 (Thomas)** | Sede 1 Primary | 10.43.101.220 | 5555, 5556, 6000 | GA Primary + GC + Actores + Monitor |
| **M2 (Santiago)** | Sede 2 Secondary | 10.43.102.248 | 5555, 5556, 6001 | GA Secondary + GC + Actores |

---

## 🚀 Inicio Rápido

### Opción 1: Scripts Automáticos (Recomendado)

```bash
# M1 (Primary)
cd ~/biblioteca-sistema
bash scripts/start_site1.sh
ss -tnlp | grep -E ':5555|:5556|:6000'

# M2 (Secondary)
cd ~/biblioteca-sistema
sed -i 's/GA_ROLE=primary/GA_ROLE=secondary/' .env
bash scripts/start_site2.sh
ss -tnlp | grep -E ':5555|:5556|:6001'
```

### Opción 2: Manual

Ver **[INICIO_RAPIDO.md](./INICIO_RAPIDO.md)** → Sección "Inicio Manual"

### Detener

```bash
bash scripts/stop_all.sh
```

---

## 📁 Estructura

```
biblioteca-sistema/
├── ga/                    # Gestor Administrador
│   ├── ga.py             # BD con replicación y WAL
│   └── monitor_failover.py
├── gc/                    # Gestor de Carga
│   ├── gc.py             # Versión serial (legacy)
│   ├── gc_multihilo.py   # Versión multihilo (actual)
│   └── monitor_failover.py
├── actores/              # Procesadores asíncronos
│   ├── actor_renovacion.py
│   ├── actor_devolucion.py
│   └── actor_prestamo.py
├── scripts/              # Scripts de automatización
│   ├── start_site1.sh   # Arranque M1
│   ├── start_site2.sh   # Arranque M2
│   ├── stop_all.sh      # Detener todos
│   └── generate_db.py   # Generar BD inicial
├── pruebas/              # Tests de fallos
│   ├── test_actor_failure.py
│   ├── test_db_corruption.py
│   └── test_latency.py
├── .env.example          # Plantilla configuración
├── requirements.txt
├── README.md            # Este archivo
├── INICIO_RAPIDO.md     # Guía de inicio rápido
└── PASO_A_PASO_MULTI_MAQUINA.md  # Guía detallada 3 PCs
```

---

## ⚙️ Configuración

### Variables Clave (.env)

```bash
# Rol (cambiar a secondary en M2)
GA_ROLE=primary

# Puertos GC
GC_REP_BIND=tcp://0.0.0.0:5555
GC_PUB_BIND=tcp://0.0.0.0:5556

# Puertos GA
GA_PRIMARY_BIND=tcp://0.0.0.0:6000
GA_SECONDARY_BIND=tcp://0.0.0.0:6001

# Replicación
GA_REPL_PUSH_ADDR=tcp://10.43.102.248:7001
GA_REPL_PULL_BIND=tcp://0.0.0.0:7001
```

---

## 🔍 Verificación

### Ver procesos corriendo

```bash
pgrep -f python3
cat .pids/*.pid
```

### Ver logs en tiempo real

```bash
tail -f logs/ga_primary.log
tail -f logs/gc_multihilo.log
tail -f logs/actor_renovacion.log
```

### Verificar puertos

```bash
ss -tnlp | grep python
```

---

## 🧪 Pruebas de Failover

### Simular caída GA Primary (M1)

```bash
# Ver PID del GA
pgrep -f ga/ga.py

# Simular caída
pkill -f ga/ga.py

# Verificar conmutación
sleep 5
cat gc/ga_activo.txt  # Debe decir: secondary
```

### Verificar continuidad (M3 - Clientes)

```bash
# Sistema debe seguir respondiendo desde secondary
python3 pruebas/multi_ps.py --num-ps 2 --requests-per-ps 10
grep -c 'status=OK' ps_logs.txt  # > 0 indica éxito
```

---

## 🆚 Cambios desde Entrega 1

| Aspecto | Entrega 1 | Entrega 2 |
|---------|-----------|-----------|
| **Arranque** | 5-7 terminales manuales | 1 script por sede |
| **Logs** | Mezclados en pantalla | Archivos separados (`logs/`) |
| **PIDs** | Manual (ps aux) | Rastreados (`.pids/*.pid`) |
| **Detener** | Ctrl+C en cada terminal | `bash scripts/stop_all.sh` |
| **Failover** | ❌ No implementado | ✅ GA Secondary automático |
| **Replicación** | ❌ No | ✅ WAL + Push asíncrono |
| **Multi-sede** | ❌ 1 sede | ✅ 2 sedes coordinadas |

---

## 📚 Documentación Completa

**[INICIO_RAPIDO.md](./INICIO_RAPIDO.md)** - Guía completa de inicio (automático y manual)

---

## 🔗 Repositorio Relacionado

**Lado Clientes:** https://github.com/SistemasDistribuidos2530/biblioteca-clientes

---

## 📞 Contacto

- Thomas Arévalo - M1 (10.43.101.220)
- Santiago Mesa - M2 (10.43.102.248)
- Diego Castrillón - M3 (10.43.102.38)

---

**Última actualización:** 14 noviembre 2025

