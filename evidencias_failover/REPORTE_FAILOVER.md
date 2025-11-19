# Reporte de Demo de Failover

**Fecha:** 2025-11-18 22:34:53
**Sistema:** Biblioteca Distribuida - Proyecto Sistemas Distribuidos

---

## 1. Ejecución del Failover Real

### Condiciones Iniciales
- **Estado GA Pre-Failover:** `primary`
- **GA PID:** 1602103
- **Actores corriendo:** 9
- **Monitor activo:** Sí

### Evento de Falla
- **Timestamp caída GA:** 22:34:35.496
- **Método:** `kill -9 1602103` (simulación de crash abrupto)

### Detección y Conmutación
- **Timestamp conmutación:** 22:34:48.594
- **MTTD (Mean Time To Detect):** 13.097974110s
- **Estado GA Post-Failover:** `secondary`

---

## 2. Logs Generados

### Monitor de Failover (logs/monitor_failover.log)

**Eventos clave capturados:**
```
2025-11-19T03:34:37.013455Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-19T03:34:37.825579Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-19T03:34:38.515509Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-19T03:34:38.955436Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-19T03:34:39.328123Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-19T03:34:40.456898Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-19T03:34:42.021632Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-19T03:34:42.835394Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-19T03:34:43.524472Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-19T03:34:43.963640Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-19T03:34:44.338865Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-19T03:34:45.466309Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-19T03:34:47.030827Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-19T03:34:47.844432Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-19T03:34:48.533450Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-19T03:34:48.535271Z Estado GA actualizado a 'secondary'
2025-11-19T03:34:48.535568Z GA primario no responde, conmutando a secundario (tcp://10.43.102.248:6001)
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
  Procesado     : 2025-11-19T03:34:35.171818Z
  GA respuesta  : {'estado': 'error', 'mensaje': 'prestamo no encontrado (replay)'}
------------------------------------------------------------------------

------------------------------------------------------------------------
                          RENOVACIÓN PROCESADA                          
------------------------------------------------------------------------
  Operación     : renovacion
  Usuario       : 67
  Libro         : BOOK-987
```

### Actor Devolución
```
------------------------------------------------------------------------
  Operación   : devolucion
  Usuario     : 31
  Libro       : BOOK-360
  Recibido GC : 2025-11-19T03:34:32.811758Z
  Publicado   : 2025-11-19T03:34:32.811804Z
  Procesado   : 2025-11-19T03:34:34.792359Z
  GA respuesta: {'estado': 'ok', 'mensaje': 'devolucion aplicada (replay)'}
------------------------------------------------------------------------
```

### Actor Préstamo
```

```

**Interpretación:**
- Los actores continúan procesando mensajes del GC sin reinicio
- La reconexión al GA secundario es transparente (vía GC)
- No se observan errores de conexión sostenidos

---

## 4. Impacto en Clientes (Métricas)

Total: 460
OK: 460
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
El sistema presenta degradación transitoria durante la ventana de detección (~13.097974110s),
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

1. **Detección automática:** El monitor detectó la caída en ~13.097974110s
2. **Conmutación exitosa:** Estado cambió de `primary` a `secondary`
3. **Actores resilientes:** Continuaron operando sin reinicio
4. **Impacto medible:** 0
0 timeouts de 460 solicitudes (0
0%)
5. **Recuperación automática:** Sistema operativo con GA secundario post-failover

---

**Generado por:** `scripts/failover_demo.sh`
**Fecha:** 2025-11-18 22:34:53
