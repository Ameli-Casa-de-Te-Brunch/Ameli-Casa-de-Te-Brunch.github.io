# Propuesta: cambios en los workflows de GitHub Actions

**Estado: propuesta, NO aplicada.** Ni `.github/workflows/deploy.yml` ni
`.github/workflows/test-rama.yml` fueron tocados. Este documento vive a
propósito FUERA de `.github/workflows/` -- GitHub escanea esa carpeta
entera en busca de workflows válidos, así que un archivo de propuesta
con estructura de workflow ahí adentro correría el riesgo de activarse
por error apenas se empujara la rama. Acá es solo texto/diff.

## `.github/workflows/deploy.yml`

Un solo paso del job `build` cambia -- todo lo demás (permisos,
triggers, el job `deploy`, la ruta que sube `upload-pages-artifact`)
queda idéntico:

```diff
-      - run: python build/render.py
+      # build_unificado.py corre build/render.py con los mismos
+      # argumentos de siempre (ver PROPUESTA_url_base_dominio_propio.md)
+      # y ADEMÁS genera la web institucional en la raíz de dist/ --
+      # ver build_unificado.py en la raíz del repo. No cambia nada de
+      # la validación/disponibilidad de los pasos anteriores.
+      - run: python build_unificado.py --production
       - uses: actions/upload-pages-artifact@56afc609e74202658d3ffba0e8f6dda462b719fa # v3
         with:
           path: dist
```

Nada más cambia en este archivo: `DISPONIBILIDAD_CSV_URL` se sigue
inyectando exactamente en el mismo paso de antes
(`Aplicar disponibilidad en vivo`), que sigue corriendo antes que este.

## `.github/workflows/test-rama.yml`

Mismo criterio -- reemplaza el render de prueba (nunca publicado, ver
comentario ya existente en el archivo) por el build unificado, para que
una rama también verifique que la web + el menú generan juntos sin
error antes de llegar a `main`:

```diff
-      - name: Render local (solo para probar que no rompe, nunca se publica)
-        run: python build/render.py
+      - name: Build unificado local (solo para probar que no rompe, nunca se publica)
+        run: python build_unificado.py
```

(Sin `--production` acá a propósito, igual que ya hacía el render
suelto -- este workflow nunca debe generar canonical/sitemap reales.)

También convendría agregar un paso antes que corra la suite de tests de
`web/` (`python -m unittest discover -s web/tests`), ya que hoy este
workflow solo corre `python -m unittest discover -s tests` (los tests
del menú). Sin ese agregado, un cambio que rompa `web/build_site.py`
pasaría esta verificación de rama sin que nadie se entere hasta que
falle `build_unificado.py` más abajo (que sí lo detectaría, pero sin el
detalle test por test).

```diff
       - name: Ejecutar pruebas automáticas
         run: python -m unittest discover -s tests -v
+      - name: Ejecutar pruebas automáticas de la web institucional
+        run: python -m unittest discover -s web/tests -v
```

## Por qué esto alcanza (y qué NO alcanza)

Estos dos diffs son la ÚNICA parte de la unificación que toca algo
"real" (los workflows que si se aplicaran correrían en GitHub Actions
de verdad). Todavía haría falta, antes de que esto funcione en
producción:

- Actualizar la celda de Sheets y aplicar el cambio de
  `build/extract_common.py` (ver `PROPUESTA_url_base_dominio_propio.md`)
  -- si no, el menú publicado seguiría anunciando el dominio viejo en
  su canonical/sitemap/JSON-LD, aunque ya sirva bien desde `/menu/`.
- Cargar el dominio propio en GitHub Pages (Settings → Pages → Custom
  domain) y confirmar el DNS -- fuera del alcance de este cierre
  técnico, requiere autorización aparte y no se toca acá.
- Revisar (Ignacio, no automatizado) que el certificado HTTPS de GitHub
  Pages para `amelicasadete.com.ar` esté emitido antes de anunciar la
  URL nueva públicamente.
