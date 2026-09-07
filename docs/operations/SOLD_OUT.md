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
5. Esperá 30 a 90 segundos: el Apps Script avisa a GitHub, y GitHub
   Actions reconstruye y publica el sitio automáticamente.

## Cómo verificar el resultado

Abrí `https://ameli-casa-de-te-brunch.github.io/` en el celular (refrescá
la página, no uses una pestaña vieja) y confirmá que el producto muestra
el estado esperado.

## Cuándo detenerse

- Si escribiste el texto y no estás seguro de haberlo tipeado exactamente
  como en la lista de arriba: revisalo antes de esperar los 30-90
  segundos — un texto que no coincide se trata como dato inválido.
- Si después de 2-3 minutos el sitio no cambió: no sigas reintentando
  cambios sueltos. Pasá a `OUTAGE.md`.

## Cómo volver atrás

Volvé a escribir el estado anterior en la misma celda (o dejala vacía si
antes estaba disponible) y esperá de nuevo los 30-90 segundos. No hace
falta tocar nada de este repositorio para esto.

## Qué nunca copiar en capturas, logs o GitHub

- La URL de la hoja de disponibilidad (aunque sea "pública por diseño de
  Google", no hace falta difundirla).
- Nada de esto en realidad tiene secretos — este es el procedimiento más
  seguro de todos los de esta carpeta, justamente porque no toca
  credenciales.
