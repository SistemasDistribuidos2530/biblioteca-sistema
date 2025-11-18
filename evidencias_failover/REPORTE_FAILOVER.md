# Reporte de Demo de Failover

**Fecha:** 2025-11-18 13:41:14
**Sistema:** Biblioteca Distribuida - Proyecto Sistemas Distribuidos

---

## 1. Ejecución del Failover Real

### Condiciones Iniciales
- **Estado GA Pre-Failover:** `primary`
- **GA PID:** 981584
- **Actores corriendo:** 9
- **Monitor activo:** Sí

### Evento de Falla
- **Timestamp caída GA:** 13:40:54.692
- **Método:** `kill -9 981584` (simulación de crash abrupto)

### Detección y Conmutación
- **Timestamp conmutación:** 13:41:09.813
- **MTTD (Mean Time To Detect):** 15.120431050s
- **Estado GA Post-Failover:** `secondary`

---

## 2. Logs Generados

### Monitor de Failover (logs/monitor_failover.log)

**Eventos clave capturados:**
```
2025-11-18T18:40:57.304483Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-18T18:40:58.806906Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-18T18:41:02.313522Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-18T18:41:03.816782Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-18T18:41:07.325275Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-18T18:41:08.827429Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-18T18:41:08.828359Z Estado GA actualizado a 'secondary'
2025-11-18T18:41:08.828517Z GA primario no responde, conmutando a secundario (tcp://10.43.102.248:6001)
2025-11-18T18:40:58.207528Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-18T18:40:58.806906Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-18T18:40:59.709463Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-18T18:41:02.313522Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-18T18:41:03.214730Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-18T18:41:03.816782Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-18T18:41:04.716674Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-18T18:41:07.325275Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-18T18:41:08.223179Z Timeout/recv error esperando pong desde tcp://localhost:6000: Resource temporarily unavailable
2025-11-18T18:41:08.827429Z Timeout/recv error esperando pong desde tcp://127.0.0.1:6000: Resource temporarily unavailable
2025-11-18T18:41:08.828359Z Estado GA actualizado a 'secondary'
2025-11-18T18:41:08.828517Z GA primario no responde, conmutando a secundario (tcp://10.43.102.248:6001)
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
  Libro         : BOOK-560
  Recibido GC   : 2025-11-18T18:40:52.055347Z
  Publicado     : 2025-11-18T18:40:52.055396Z
  Nueva fecha   : 2025-12-02T18:40:54.172028Z
  Procesado     : 2025-11-18T18:40:54.198025Z
  GA respuesta  : {'estado': 'error', 'mensaje': 'prestamo no encontrado (replay)'}
------------------------------------------------------------------------

------------------------------------------------------------------------
                          RENOVACIÓN PROCESADA                          
```

### Actor Devolución
```

------------------------------------------------------------------------
                          DEVOLUCIÓN PROCESADA                          
------------------------------------------------------------------------
  Operación   : devolucion
  Usuario     : 26
  Libro       : BOOK-361
  Recibido GC : 2025-11-18T18:40:52.044117Z
  Publicado   : 2025-11-18T18:40:52.044176Z
  Procesado   : 2025-11-18T18:40:53.222168Z9Z
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

Total: 260
OK: 260
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
El sistema presenta degradación transitoria durante la ventana de detección (~15.120431050s),
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

1. **Detección automática:** El monitor detectó la caída en ~15.120431050s
2. **Conmutación exitosa:** Estado cambió de `primary` a `secondary`
3. **Actores resilientes:** Continuaron operando sin reinicio
4. **Impacto medible:** 0
0 timeouts de 260 solicitudes (0
0%)
5. **Recuperación automática:** Sistema operativo con GA secundario post-failover

---

**Generado por:** `scripts/failover_demo.sh`
**Fecha:** 2025-11-18 13:41:14
