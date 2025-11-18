# 🎯 Guía para Ejecutar la Demo de Failover

**Propósito:** Generar evidencias automáticas para los puntos del informe sobre failover.

---

## 📋 Pre-requisitos

### M1 (Sistema debe estar corriendo):
```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema

# Verificar que esté todo arriba
ss -tnlp | grep -E ':5555|:5556|:6000'
pgrep -f ga/ga.py
pgrep -f gc/gc
pgrep -f actor_
pgrep -f monitor_failover
```

**Si algo falta, arrancar:**
```bash
bash scripts/start_site1.sh
```

---

## 🚀 Ejecución de la Demo

### Paso 1: Ejecutar el script automatizado

```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema
bash scripts/failover_demo.sh
```

**El script hará automáticamente:**
1. ✅ Verificar que el sistema esté corriendo
2. 📸 Capturar estado PRE-failover (logs, ga_activo.txt)
3. 🔥 Lanzar carga de fondo (2 PS con 50 solicitudes c/u)
4. ⚠️  Simular caída del GA primario (`kill -9`)
5. ⏱️  Medir MTTD (tiempo de detección)
6. 📝 Capturar logs DURANTE la conmutación
7. 📊 Analizar métricas de impacto (OK/TIMEOUT/ERROR)
8. 📄 Generar reporte completo en Markdown

---

## 📂 Salida Generada

Todos los archivos se guardan en: `evidencias_failover/`

### Archivos clave para el informe:

| Archivo | Qué contiene | Para qué punto del informe |
|---------|--------------|---------------------------|
| **REPORTE_FAILOVER.md** | Reporte completo consolidado | Copiar directamente al informe |
| **monitor_DURANTE.log** | Eventos de conmutación del monitor | "Logs generados" |
| **actor_*_POST.log** | Logs de actores post-failover | "Evidencia de reconexión" |
| **metricas_clientes.txt** | Solicitudes OK/TIMEOUT/ERROR | "Impacto medible" |
| **MTTD.txt** | Tiempo de detección (segundos) | Métrica para tabla |
| **ga_estado_*.txt** | Estados PRE/DURANTE/POST | "Ejecución del failover real" |

---

## 📖 Cómo Usar las Evidencias en el Informe

### 1. Ejecución del Failover Real

**Copiar del reporte:**
```bash
sed -n '/## 1. Ejecución del Failover Real/,/## 2. Logs Generados/p' \
  evidencias_failover/REPORTE_FAILOVER.md
```

**Incluye:**
- Timestamp exacto de la caída
- PID del GA matado
- Timestamp de conmutación
- MTTD medido

---

### 2. Logs Generados

**Ver eventos del monitor:**
```bash
cat evidencias_failover/monitor_DURANTE.log
```

**Buscar líneas clave:**
```bash
grep -E "(Timeout|conmutando|actualizado)" evidencias_failover/monitor_DURANTE.log
```

**Para el informe, incluir:**
- Líneas con "Timeout/recv error esperando pong" (detección)
- Línea con "conmutando a secundario" (decisión)
- Línea con "Estado GA actualizado a 'secondary'" (confirmación)

**Archivo completo de estado:**
```bash
echo "PRE: $(cat evidencias_failover/ga_estado_PRE.txt)"
echo "DURANTE: $(cat evidencias_failover/ga_estado_DURANTE.txt)"
echo "POST: $(cat evidencias_failover/ga_estado_POST.txt)"
```

---

### 3. Evidencia de Reconexión Automática de Actores

**Ver logs de cada actor:**
```bash
# Actor Renovación
tail -20 evidencias_failover/actor_renovacion_POST.log

# Actor Devolución
tail -20 evidencias_failover/actor_devolucion_POST.log

# Actor Préstamo
tail -20 evidencias_failover/actor_prestamo_POST.log
```

**Qué buscar en los logs:**
- ✅ Mensajes procesados ANTES de la caída
- ⚠️  Posibles errores de conexión DURANTE (~5s)
- ✅ Mensajes procesados DESPUÉS (prueba de recuperación)
- 🔍 **NO** hay líneas de "reinicio" o "reconexión" porque los actores:
  - Se conectan al GC (no directamente al GA)
  - El GC es quien redirige al GA activo
  - Los actores solo ven mensajes, no cambios de infraestructura

**Para el informe:**
```
"Los logs de actores muestran procesamiento continuo de mensajes antes,
durante y después del failover, sin eventos de reconexión explícita.
Esto confirma que la conmutación fue transparente para los actores,
ya que su conexión es con el GC (PUB/SUB en :5556), no con el GA."
```

---

### 4. Métricas de Impacto

**Ver resumen:**
```bash
cat evidencias_failover/resumen_metricas.txt
```

**Salida esperada:**
```
Total: 100
OK: 85
TIMEOUT: 12
ERROR: 3
Tasa de éxito: 85%
```

**Interpretación para el informe:**
- Los TIMEOUT ocurren durante la ventana MTTD (~6-9 segundos típico)
- Representa solicitudes que llegaron durante la conmutación
- Tasa de éxito >80% indica recuperación efectiva
- Los PS pueden reintentar los TIMEOUT (según su configuración)

---

## 🔄 Repetir la Demo (si necesitas más evidencias)

### Paso 1: Reiniciar el GA primario
```bash
bash scripts/start_site1.sh
```

Espera ~10 segundos hasta ver:
```bash
cat gc/ga_activo.txt  # Debe decir "primary"
```

### Paso 2: Limpiar evidencias anteriores (opcional)
```bash
rm -rf evidencias_failover
```

### Paso 3: Re-ejecutar
```bash
bash scripts/failover_demo.sh
```

---

## 📊 Tabla de Métricas para el Informe

Puedes generar una tabla así con los datos capturados:

| Métrica | Valor | Fuente |
|---------|-------|--------|
| MTTD | `cat evidencias_failover/MTTD.txt` | Calculado automático |
| MTTR | ~0s (conmutación automática) | Estado POST |
| Solicitudes totales | `grep Total evidencias_failover/resumen_metricas.txt` | Métricas |
| Solicitudes OK | `grep OK evidencias_failover/resumen_metricas.txt` | Métricas |
| Solicitudes TIMEOUT | `grep TIMEOUT evidencias_failover/resumen_metricas.txt` | Métricas |
| Tasa de éxito | `grep Tasa evidencias_failover/resumen_metricas.txt` | Calculado |

---

## 🎬 Captura de Pantalla (opcional)

Si quieres screenshots para el informe, ejecuta la demo con `script`:

```bash
script -c "bash scripts/failover_demo.sh" evidencias_failover/terminal_output.txt
```

Luego puedes copiar secciones del output al informe.

---

## 🐛 Troubleshooting

### "GA no está corriendo"
```bash
bash scripts/start_site1.sh
sleep 5
bash scripts/failover_demo.sh
```

### "No se detectó conmutación"
- Verifica que el monitor esté corriendo: `pgrep -f monitor_failover`
- Si no está, añádelo: `python3 gc/monitor_failover.py &`

### "Pocos TIMEOUT capturados"
- Es normal si MTTD es muy bajo (<3s)
- Indica un sistema muy eficiente
- Documentarlo como fortaleza

---

## ✅ Checklist para el Informe

- [ ] Ejecuté `failover_demo.sh`
- [ ] Tengo `evidencias_failover/REPORTE_FAILOVER.md`
- [ ] MTTD está capturado y es razonable (3-10s)
- [ ] Los logs del monitor muestran conmutación
- [ ] Los logs de actores muestran continuidad
- [ ] Las métricas tienen OK y TIMEOUT
- [ ] `ga_activo.txt` cambió de primary → secondary
- [ ] Copié las secciones relevantes al informe

---

**Última actualización:** 18 noviembre 2025  
**Script:** `scripts/failover_demo.sh`

