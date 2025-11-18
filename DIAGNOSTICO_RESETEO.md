# 🔍 DIAGNÓSTICO Y RESETEO - Guía Rápida

## 🎯 Problema: Sistema queda en "secondary" aunque GA esté corriendo

**Síntoma:**
```
[12:58:05] ✗ Sistema NO está en estado 'primary' (actual: secondary)
```

---

## 🔧 SOLUCIÓN RÁPIDA (2 pasos)

### Paso 1: Diagnosticar el problema

```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema
bash scripts/diagnose_failover_state.sh
```

**Esto te dirá exactamente qué está mal:**
- Si el GA está en puerto 6000 o 6001
- Si se lanzó con GA_ROLE=primary o secondary
- Si el .env está configurado correctamente
- Si el monitor está corriendo
- Estado de ga_activo.txt

---

### Paso 2: Resetear a PRIMARY

```bash
bash scripts/reset_to_primary.sh
```

**Esto hace automáticamente:**
1. ✅ Detiene TODOS los procesos (stop_all.sh + kills forzados)
2. ✅ Limpia .pids y ga_activo.txt
3. ✅ Corrige .env → `GA_ROLE=primary`
4. ✅ Arranca el sistema con variables correctas
5. ✅ Espera 15s a que el monitor detecte el estado
6. ✅ Muestra verificación final

**Duración:** ~25 segundos

---

## 📊 Salida Esperada del Reseteo

```
╔════════════════════════════════════════════════════════════════════╗
║              RESETEO COMPLETO A ESTADO PRIMARY                     ║
╚════════════════════════════════════════════════════════════════════╝

[1/6] Deteniendo todos los procesos...
✓ Procesos detenidos

[2/6] Limpiando estado anterior...
✓ Estado limpiado

[3/6] Verificando configuración .env...
✓ GA_ROLE=primary configurado en .env
  Configuración actual:
    GA_ROLE=primary
    GA_PRIMARY_BIND=tcp://0.0.0.0:6000

[4/6] Arrancando sistema en modo PRIMARY...
== Iniciando SEDE 1 (Primary) ==
✓ Sistema iniciado

[5/6] Verificando componentes...
✓ GA corriendo (PID: XXXXX)
✓ GA escuchando en puerto 6000 (PRIMARY)
✓ GC corriendo
✓ N actores corriendo
✓ Monitor de failover corriendo

[6/6] Esperando a que el monitor detecte el estado PRIMARY...
...............
✓ Estado detectado: primary (después de 8s)

╔════════════════════════════════════════════════════════════════════╗
║                     VERIFICACIÓN FINAL                             ║
╚════════════════════════════════════════════════════════════════════╝

✓✓✓ ESTADO: primary

Puertos escuchando:
  0.0.0.0:5555
  0.0.0.0:5556
  0.0.0.0:6000

╔════════════════════════════════════════════════════════════════════╗
║                  RESETEO COMPLETADO                                ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## ✅ Verificación Post-Reseteo

```bash
# Debe decir "primary"
cat gc/ga_activo.txt

# Debe mostrar puerto 6000
ss -tnlp | grep 6000

# Debe mostrar GA_ROLE=primary
grep GA_ROLE= .env
```

---

## 🎬 Ahora Sí: Ejecutar Demo de Failover

```bash
bash scripts/failover_demo.sh
```

**Debería funcionar sin errores**

---

## 🐛 Causas Comunes del Problema "secondary"

### 1. `.env` tenía `GA_ROLE=secondary`
**Causa:** Copiado desde M2 o editado manualmente  
**Fix:** El script `reset_to_primary.sh` lo corrige automáticamente

### 2. GA se lanzó en puerto 6001 en lugar de 6000
**Causa:** Variable de entorno incorrecta al arrancar  
**Fix:** El script fuerza `export GA_ROLE=primary` antes de arrancar

### 3. Monitor no está corriendo
**Causa:** No se lanzó o crasheó  
**Fix:** `start_site1.sh` lo arranca; el reseteo también

### 4. `ga_activo.txt` quedó en "secondary" de ejecución anterior
**Causa:** No se limpió entre arranques  
**Fix:** El script lo elimina en la fase de limpieza

---

## 📋 Flujo Completo Recomendado

```bash
# 1. Diagnosticar
bash scripts/diagnose_failover_state.sh

# 2. Resetear (si el diagnóstico encontró problemas)
bash scripts/reset_to_primary.sh

# 3. Esperar 5 segundos adicionales
sleep 5

# 4. Verificar estado
cat gc/ga_activo.txt  # Debe decir "primary"

# 5. Ejecutar demo
bash scripts/failover_demo.sh
```

---

## 🔍 Comando de Diagnóstico Rápido

Para ver TODO el estado en un vistazo:

```bash
echo "=== Estado ==="
cat gc/ga_activo.txt 2>/dev/null || echo "no existe"

echo -e "\n=== .env ==="
grep GA_ROLE= .env 2>/dev/null || echo "no definido"

echo -e "\n=== Proceso GA ==="
pgrep -a -f ga/ga.py

echo -e "\n=== Puerto GA ==="
ss -tnlp | grep python3 | grep -E ':(6000|6001)'

echo -e "\n=== Monitor ==="
pgrep -a -f monitor_failover
```

---

## ⚠️ Si Después del Reseteo Sigue en "secondary"

1. **Ver logs del monitor:**
   ```bash
   tail -30 logs/monitor_failover.log
   ```

2. **Verificar que el GA responde a ping:**
   ```bash
   echo "ping" | nc localhost 6000
   # Debe responder "pong"
   ```

3. **Forzar manualmente el estado:**
   ```bash
   echo "primary" > gc/ga_activo.txt
   ```

4. **Reintentar la demo:**
   ```bash
   bash scripts/failover_demo.sh
   ```

---

## 📞 Scripts Creados

| Script | Función |
|--------|---------|
| `diagnose_failover_state.sh` | Diagnostica por qué está en "secondary" |
| `reset_to_primary.sh` | Resetea todo a estado PRIMARY limpio |
| `failover_demo.sh` | Demo automatizada de failover (ya existía) |

---

## ✅ Checklist Final

- [ ] Ejecuté `diagnose_failover_state.sh`
- [ ] Ejecuté `reset_to_primary.sh`
- [ ] Esperé 5-10 segundos
- [ ] `cat gc/ga_activo.txt` dice "primary"
- [ ] `ss -tnlp | grep 6000` muestra el puerto
- [ ] `failover_demo.sh` ejecuta sin errores

---

**Última actualización:** 18 noviembre 2025  
**Archivos creados:**
- `scripts/diagnose_failover_state.sh`
- `scripts/reset_to_primary.sh`
- `DIAGNOSTICO_RESETEO.md` (este archivo)

