# Reporte de Demo de Failover

**Fecha:** 2025-11-19 18:25:18
**Sistema:** Biblioteca Distribuida - Proyecto Sistemas Distribuidos

---

## 1. Ejecución del Failover Real

### Condiciones Iniciales
- **Estado GA Pre-Failover:** `primary`
- **GA PID:** 2565113
- **Actores corriendo:** 9
- **Monitor activo:** Sí

### Evento de Falla
- **Timestamp caída GA:** 18:25:00.062
- **Método:** `kill -9 2565113` (simulación de crash abrupto)

### Detección y Conmutación
- **Timestamp conmutación:** 18:25:13.142
- **MTTD (Mean Time To Detect):** 13.079659764s
- **Estado GA Post-Failover:** `secondary`

---

## 2. Logs Generados

### Monitor de Failover (logs/monitor_failover.log)

**Eventos clave capturados:**
```
2025-11-19T23:25:02.898574Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-19T23:25:04.401585Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-19T23:25:07.911460Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-19T23:25:09.413852Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-19T23:25:12.919441Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
```

**Archivo completo:** `evidencias_failover/monitor_DURANTE.log`

### Estado del Sistema (gc/ga_activo.txt)

- **PRE:** `primary`
- **DURANTE:** `secondary`
- **POST:** `secondary`

---

## 3. Evidencia de Reconexión Automática de Actores

### Actor Renovación
```
  Operación     : renovacion
  Usuario       : 35
  Libro         : BOOK-34
  Recibido GC   : 2025-11-19T23:24:57.429214Z
  Publicado     : 2025-11-19T23:24:57.429285Z
  Nueva fecha   : 2025-12-03T23:24:59.274751Z
  Procesado     : 2025-11-19T23:24:59.319714Z
  GA respuesta  : {'estado': 'error', 'mensaje': 'prestamo no encontrado (replay)'}
------------------------------------------------------------------------
```

### Actor Devolución
```
------------------------------------------------------------------------
  Operación   : devolucion
  Usuario     : 52
  Libro       : BOOK-653
  Recibido GC : 2025-11-19T23:24:57.428759Z
  Publicado   : 2025-11-19T23:24:57.428830Z
  Procesado   : 2025-11-19T23:24:59.398811Z
  GA respuesta: {'estado': 'ok', 'mensaje': 'devolucion aplicada (replay)'}
------------------------------------------------------------------------
```

### Actor Préstamo
```

========================================================================
                ACTOR DE PRÉSTAMO — SUSCRIPCIÓN PUB/SUB                 
------------------------------------------------------------------------
  Tópico        : Prestamo
  Dirección PUB : tcp://127.0.0.1:5556
  Log           : log_actor_prestamo.txt
  GA activo     : secondary -> tcp://localhost:6001
========================================================================
```

**Interpretación:**
- Los actores continúan procesando mensajes del GC sin reinicio
- La reconexión al GA secundario es transparente (vía GC)
- No se observan errores de conexión sostenidos

---

## 4. Impacto en Clientes (Métricas)

Total: 560
OK: 560
TIMEOUT: 0
0
ERROR: 0
0
Tasa de éxito: 100.00%

**Ventana de degradación:**
- Solicitudes con TIMEOUT durante MTTD: 0
0
- Recuperación automática tras conmutación: Sí

**Conclusión:**
El sistema presenta degradación transitoria durante la ventana de detección (~13.079659764s),
pero recupera operación normal al conmutar al GA secundario.

---

## 5. Archivos de Evidencia Generados

```
- actor_devolucion_DURANTE.log
- actor_devolucion_POST.log
- actor_devolucion_PRE.log
- actor_prestamo_DURANTE.log
- actor_prestamo_POST.log
- actor_prestamo_PRE.log
- actor_renovacion_DURANTE.log
- actor_renovacion_POST.log
- actor_renovacion_PRE.log
- carga_durante_failover.log
- ga_estado_DURANTE.txt
- ga_estado_POST.txt
- ga_estado_PRE.txt
- metricas_clientes.txt
- monitor_DURANTE.log
- monitor_POST.log
- monitor_PRE.log
- MTTD.txt
- REPORTE_FAILOVER.md
- resumen_metricas.txt
- timestamp_caida.txt
- timestamp_conmutacion.txt
```

**Ubicación:** `/home/estudiante/ProyectoDistribuidos/biblioteca-sistema/evidencias_failover`

---

## 6. Conclusiones

1. **Detección automática:** El monitor detectó la caída en ~13.079659764s
2. **Conmutación exitosa:** Estado cambió de `primary` a `secondary`
3. **Actores resilientes:** Continuaron operando sin reinicio
4. **Impacto medible:** 0
0 timeouts de 560 solicitudes (0
0%)
5. **Recuperación automática:** Sistema operativo con GA secundario post-failover

---

**Generado por:** `scripts/failover_demo.sh`
**Fecha:** 2025-11-19 18:25:18
