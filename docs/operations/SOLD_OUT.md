# Marcar un producto agotado / con pocas unidades / de vuelta

## Quién puede hacerlo

Cualquier persona del personal con acceso a la hoja de Google Sheets de
disponibilidad (el link lo tiene el dueño). No hace falta saber de
computadoras ni tocar este repositorio, GitHub, ni Apps Script.

## Qué sistema se modifica

Solo la hoja de Google Sheets de disponibilidad. Nada del Excel maestro,
nada de este repositorio, nada de GitHub se toca a mano en este
procedimiento.

## Pasos exactos

1. Abrí la hoja de disponibilidad en el celular o la computadora.
2. Buscá la fila del producto por su **ID** (la misma sigla+número que
   tiene en el Excel maestro, ej. `TYT004`) o por su nombre de referencia.
3. En la columna **Disponibilidad**, escribí exactamente uno de estos
   textos (tal cual, con mayúsculas y sin errores de tipeo — cualquier
   otro texto se trata como dato inválido y no se publica):
   - *(vacío)* → disponible normal
   - `Disponible` → disponible normal (igual que vacío, más explícito)
   - `Agotado por hoy` → no se puede pedir hasta el reset de mañana
   - `Últimas porciones` → se puede pedir igual, solo avisa que queda poco
   - `No disponible temporalmente` → no se puede pedir hasta que alguien
     lo vuelva a marcar disponible a mano (no se resetea solo)
4. Guardá el cambio (Sheets guarda solo, no hay botón "guardar").
5. El Apps Script avisa a GitHub, y GitHub Actions reconstruye y publica
   el sitio automáticamente. El workflow en sí (build + deploy) tarda
   ~30-90 segundos -- pero eso **no** es lo mismo que "ya se ve en el
   sitio": GitHub Pages sirve detrás de una caché pública que puede
   seguir mostrando la versión anterior varios minutos más, incluso con
   el workflow ya terminado bien.

## Cómo verificar el resultado

1. Primero, en GitHub, pestaña **Actions**: confirmá que la corrida más
   reciente terminó en ✅ (eso confirma que el dato se aplicó, no que ya
   se ve).
2. Recién después, abrí `https://ameli-casa-de-te-brunch.github.io/` con
   un refresco forzado (Ctrl+Shift+R, o el equivalente en el celular). Si
   seguís viendo el estado viejo, probá desde otro dispositivo o red
   antes de asumir que algo falló -- puede ser solo la caché pública
   todavía sirviendo la versión anterior.

## Cuándo detenerse

- Si escribiste el texto y no estás seguro de haberlo tipeado exactamente
  como en la lista de arriba: revisalo antes de esperar nada — un texto
  que no coincide se trata como dato inválido.
- Si la corrida de Actions ya terminó en ✅ pero después de varios
  minutos (no segundos) y probando desde otro dispositivo/red el sitio
  sigue sin cambiar: no sigas reintentando cambios sueltos. Pasá a
  `OUTAGE.md`.

## Cómo volver atrás

Volvé a escribir el estado anterior en la misma celda (o dejala vacía si
antes estaba disponible). Mismos tiempos que arriba: el workflow corre en
~30-90 segundos, la visibilidad para el visitante puede tardar más por la
caché pública. No hace falta tocar nada de este repositorio para esto.

## Qué nunca copiar en capturas, logs o GitHub

- La URL de la hoja de disponibilidad (aunque sea "pública por diseño de
  Google", no hace falta difundirla).
- Nada de esto en realidad tiene secretos — este es el procedimiento más
  seguro de todos los de esta carpeta, justamente porque no toca
  credenciales.
