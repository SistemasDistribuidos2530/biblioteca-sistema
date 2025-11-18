# 🚨 ERROR RESUELTO - Guía Rápida de Ejecución

## Problema Identificado

1. ✅ **Ruta incorrecta** → Ya corregida en el script
2. ⚠️ **Sistema en estado "secondary"** → GA primario no está arriba

---

## ✅ Solución: Ejecuta Esto Primero

### Paso 1: Reiniciar Sistema en M1

```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema

# Detener todo
bash scripts/stop_all.sh

# Esperar 2 segundos
sleep 2

# Arrancar limpio
bash scripts/start_site1.sh

# Verificar que está arriba
ss -tnlp | grep -E ':5555|:5556|:6000'
```

**Esperado:** 3 líneas LISTEN en puertos 5555, 5556, 6000

---

### Paso 2: Verificar Estado Primary

```bash
# Esperar ~10 segundos a que el monitor detecte el GA
sleep 10

# Verificar estado
cat gc/ga_activo.txt
```

**Debe decir:** `primary`

**Si dice "secondary":**
```bash
# Ver si el GA está corriendo
pgrep -f ga/ga.py

# Si NO está, arrancar de nuevo
bash scripts/start_site1.sh
```

---

### Paso 3: Ejecutar Demo de Failover

```bash
cd ~/ProyectoDistribuidos/biblioteca-sistema
bash scripts/failover_demo.sh
```

**Ahora debería funcionar sin errores**

---

## 🎯 Resumen del Fix Aplicado

### Cambios en `scripts/failover_demo.sh`:

1. ✅ Busca `biblioteca-clientes` en múltiples ubicaciones:
   - `../biblioteca-clientes`
   - `/home/estudiante/biblioteca-clientes`
   - `/home/estudiante/ProyectoDistribuidos/biblioteca-clientes`

2. ✅ Valida estado inicial = "primary" antes de empezar

3. ✅ Maneja caso sin carga de fondo (si no encuentra clientes)

4. ✅ Mensajes de error claros con instrucciones

---

## 📋 Checklist Pre-Ejecución

Antes de correr `failover_demo.sh`:

- [ ] GA primario corriendo: `pgrep -f ga/ga.py`
- [ ] Puertos escuchando: `ss -tnlp | grep 6000`
- [ ] Estado = primary: `cat gc/ga_activo.txt`
- [ ] Monitor corriendo: `pgrep -f monitor_failover`

**Si TODO está OK → ejecutar demo**

---

## 🔄 Si Falla de Nuevo

```bash
# Nuclear option: resetear todo
cd ~/ProyectoDistribuidos/biblioteca-sistema
pkill -f python3
rm -rf .pids/*
sleep 2
bash scripts/start_site1.sh
sleep 10
cat gc/ga_activo.txt  # Debe decir "primary"
bash scripts/failover_demo.sh
```

---

## ⚠️ Nota Importante

**La demo NO requiere M3 (clientes) para funcionar.**

- Si encuentra `biblioteca-clientes`, lanza carga de fondo
- Si NO lo encuentra, salta ese paso pero sigue funcionando
- Captura todas las evidencias de failover igual

**Recomendado:** Ejecutar desde M1 solamente

---

## 📞 Archivos Modificados (para commit)

```bash
git add scripts/failover_demo.sh
git commit -m "Fix: rutas de clientes y validación estado primary"
git push
```

---

**Estado:** ✅ Script corregido, listo para ejecutar
**Última actualización:** 18 noviembre 2025

