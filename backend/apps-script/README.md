# Backend de "me gusta" — Google Apps Script

Guarda los votos en una Google Sheet propia. Esos mismos números se pueden
después pegar a mano en `12_Estadísticas` del maestro para alimentar la
ingeniería de menú (hoja `09`).

## 1. Crear la planilla

1. Andá a [sheets.google.com](https://sheets.google.com) → hoja en blanco.
2. Nombrala como quieras (ej. "Amelí — Votos del menú"). No hace falta crear
   ninguna pestaña a mano: el script crea la pestaña `Votos` sola la primera
   vez que corre.

## 2. Pegar el script

1. En la planilla: **Extensiones → Apps Script**.
2. Borrá el contenido de `Code.gs` que trae por defecto y pegá el contenido
   de [`Code.gs`](Code.gs) de este repo.
3. Guardá (ícono de disco o `Ctrl+S`).

## 3. Publicar como Web App

1. Arriba a la derecha: **Implementar → Nueva implementación**.
2. Tipo: **Aplicación web**.
3. Configuración:
   - **Ejecutar como:** Yo (tu cuenta)
   - **Quién tiene acceso:** Cualquier usuario
4. **Implementar**. Google va a pedir autorizar permisos la primera vez — es
   tu propio script accediendo a tu propia planilla, es seguro aceptar.
5. Copiá la **URL de la aplicación web** que te da (termina en `/exec`).

## 4. Conectar la URL al sitio

Esa URL **no se sube al repo** (por eso `config.js` está en `.gitignore`).
Se carga de dos formas, según dónde estés:

**En producción (GitHub Actions):**
1. En el repo de GitHub → **Settings → Secrets and variables → Actions → New
   repository secret**.
2. Nombre: `VOTOS_ENDPOINT`. Valor: la URL que copiaste en el paso 3.
3. Listo — el workflow ya está preparado para generar `dist/config.js` con
   ese valor en cada deploy (ver `.github/workflows/deploy.yml`).

**En tu máquina, para probar en local:**
1. Copiá `templates/config.example.js` como `config.js` en la raíz del repo
   (o donde indique `build.py`).
2. Pegá la misma URL en `votosEndpoint`.
3. Corré `python build.py` — `config.js` se copia junto al `index.html`.

## 5. Si necesitás re-desplegar (cambiaste el código del script)

Cada vez que edites `Code.gs` en el editor de Apps Script tenés que hacer
**Implementar → Administrar implementaciones → ✎ (editar) → Nueva versión →
Implementar** para que el cambio se refleje en la URL ya publicada (si solo
guardás, la Web App sigue sirviendo la versión vieja).

## Notas

- No hay datos personales: solo se guarda `producto_id` y un contador. No
  hace falta aviso de cookies.
- El "1 voto por dispositivo" se controla en el navegador (`localStorage`),
  no en el servidor — alguien podría votar de nuevo borrando el storage o
  desde otro dispositivo. Para un contador de "me gusta" de un menú esto es
  una fricción razonable, no un sistema de autenticación.
- Cuotas gratuitas de Apps Script son generosas para el tráfico de un menú de
  un local (miles de ejecuciones por día); si algún día se queda corto, migrar
  a Supabase es la alternativa documentada en el prompt original.
