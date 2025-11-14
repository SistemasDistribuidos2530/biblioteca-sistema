# Pruebas de Fallos - Sistema de Biblioteca

**Universidad:** Pontificia Universidad Javeriana  
**Materia:** Sistemas Distribuidos  
**Integrantes:** Thomas Arévalo, Santiago Mesa, Diego Castrillón

---

## 📋 Descripción

Suite de pruebas automatizadas para validar el modelo de tolerancia a fallos del sistema distribuido de biblioteca.

---

## 🧪 Tests Disponibles

### 1. **test_actor_failure.py** - Caída de Actor
Simula la caída de un actor durante procesamiento y mide el impacto.

**Funcionalidad:**
1. Verifica que el actor esté corriendo
2. Mata el proceso del actor
3. Monitorea el sistema por 10 segundos
4. Verifica si hay recuperación automática

**Uso:**
```bash
# Actor de renovación (default)
python pruebas/test_actor_failure.py

# Actor específico
python pruebas/test_actor_failure.py --actor renovacion
python pruebas/test_actor_failure.py --actor devolucion
python pruebas/test_actor_failure.py --actor prestamo
```

**Métricas:**
- Duración de la caída
- Recuperación automática (sí/no)
- Estado del log

**Requisitos:**
- Actor debe estar corriendo antes del test
- Permisos para terminar procesos

---

### 2. **test_db_corruption.py** - Corrupción DB + Replay WAL
Simula corrupción de la base de datos y verifica recuperación vía WAL.

**Escenario:**
1. Crea backup de DB y WAL
2. Corrompe la base de datos
3. Verifica que no se pueda cargar
4. Evalúa si WAL permite recuperación
5. Restaura archivos originales

**Uso:**
```bash
# GA primario (default)
python pruebas/test_db_corruption.py

# GA específico
python pruebas/test_db_corruption.py --role primary
python pruebas/test_db_corruption.py --role secondary
```

**Métricas:**
- DB cargable antes/después
- Entradas disponibles en WAL
- Viabilidad de recuperación

**Nota:** Este test NO requiere que el GA esté corriendo (trabaja directamente con archivos).

---

### 3. **test_latency.py** - Latencia Artificial
Introduce delays artificiales cambiando timeouts y mide impacto.

**Configuraciones probadas:**
- Normal: 2000ms timeout
- Medio: 1000ms timeout
- Bajo: 500ms timeout
- Muy Bajo: 200ms timeout

**Métricas por configuración:**
- % de timeouts
- % de solicitudes OK
- Latencias (min, mean, p50, p95, max)

**Uso:**
```bash
# Default (20 solicitudes por test)
python pruebas/test_latency.py

# Personalizado
LATENCY_NUM=50 GC_ADDR=tcp://10.43.101.220:5555 python pruebas/test_latency.py
```

**Variables:**
- `LATENCY_NUM`: Solicitudes por test (default: 20)
- `GC_ADDR`: Dirección del GC (default: tcp://localhost:5555)

---

### 4. **test_failover.py** (Mejorado)
Simulador interactivo de fallos del GA.

**Opciones:**
1. Caer GA Primario (puerto 6000)
2. Caer GA Secundario (puerto 6001)
3. Corromper DB del Primario
4. Corromper DB del Secundario
5. Salir

**Uso:**
```bash
cd ga
python test_failover.py
```

**Funcionalidad:**
- Encuentra procesos por puerto
- Termina procesos ordenadamente
- Corrompe DBs para pruebas
- Modo interactivo

---

## 📊 Reportes Generados

Cada test genera un reporte JSON:
- `reporte_actor_failure_{actor}.json`
- `reporte_db_corruption_{role}.json`
- `reporte_latency.json`

---

## 🎯 Escenarios del Modelo de Fallos

### Fallas de Proceso
- ✅ **test_actor_failure.py**: Caída de actor de renovación/devolución/préstamo

### Fallas de Comunicación
- ✅ **test_latency.py**: Timeouts y delays en req/rep

### Fallas de Datos
- ✅ **test_db_corruption.py**: BD corrupta, WAL válido

### Fallas de Almacenamiento
- ✅ **test_db_corruption.py**: Indisponibilidad de BD primaria

---

## 🔧 Requisitos

```bash
# Dependencias
pip install psutil pyzmq

# Para test_actor_failure: actores deben estar corriendo
python actores/actor_renovacion.py &
python actores/actor_devolucion.py &

# Para test_latency: GC debe estar corriendo
python gc/gc.py &
```

---

## 📝 Ejemplo de Ejecución Completa

```bash
# 1. Preparar entorno
cd ~/biblioteca-sistema

# 2. Iniciar componentes necesarios
python gc/gc.py > logs/gc.log 2>&1 &
python actores/actor_renovacion.py > logs/actor_renov.log 2>&1 &
python actores/actor_devolucion.py > logs/actor_devol.log 2>&1 &

# 3. Ejecutar tests de fallos
python pruebas/test_actor_failure.py --actor renovacion
python pruebas/test_db_corruption.py --role primary
python pruebas/test_latency.py

# 4. Ver reportes
ls -lh pruebas/reporte_*.json
cat pruebas/reporte_actor_failure_renovacion.json
```

---

## 🚨 Advertencias

1. **test_actor_failure.py** mata procesos reales
2. **test_db_corruption.py** modifica archivos (hace backup/restore automático)
3. **test_latency.py** puede saturar temporalmente el GC
4. Ejecutar en ambiente de pruebas, NO en producción

---

## 📖 Interpretación de Resultados

### test_actor_failure.py

| Resultado | Significado |
|-----------|-------------|
| RECUPERADO | Actor se reinició automáticamente |
| CAIDO | Actor permanece caído, requiere intervención manual |

### test_db_corruption.py

| Resultado | Significado |
|-----------|-------------|
| VIABLE | WAL tiene entradas, recuperación es posible |
| SIN_DATOS | WAL vacío, recuperación restaura estado vacío |

### test_latency.py

- **Timeout óptimo**: Menor timeout sin producir fallos
- **Degradación**: Incremento de timeouts al reducir timeout configurado

---

## 🔗 Integración con FASE 2

Estos tests complementan las pruebas de seguridad (FASE 2):

**Seguridad (biblioteca-clientes/pruebas/):**
- Ataques: replay, corrupt, flood, injection

**Fallos (biblioteca-sistema/pruebas/):**
- Fallos: actor, db, latency, failover

---

## 📚 Referencias

Ver:
- `../docs/MODELO_FALLOS.md` - Modelo de fallos completo
- `../../ROADMAP.md` - Planificación del proyecto
- `../../PROGRESO_FASE3.md` - Progreso de implementación

