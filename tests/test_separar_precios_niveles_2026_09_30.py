"""Pruebas de assets/js/menu.js y assets/css/menu.css para la separación
de precios en niveles (2026-09-30, a pedido de Ignacio: "diferenciación
entre chico-grande, vaso-jarra... ponerlos por separado").

Estáticas, mismo criterio que tests/test_auditoria_tecnica_2026_09_30.py:
no hay Selenium/Playwright en este proyecto -- se lee el JS/CSS real y se
verifican con expresiones regulares las propiedades estructurales que
hacen que el render en el navegador sea correcto. La lógica de datos
(niveles_precio) ya tiene su propia cobertura en tests/test_extract_common.py
y tests/test_validate_json_publico.py -- esto solo cubre el consumo del
lado del navegador."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MENU_JS = ROOT / "assets" / "js" / "menu.js"
MENU_CSS = ROOT / "assets" / "css" / "menu.css"


class TestTextoPrecioConNiveles(unittest.TestCase):
    def setUp(self):
        self.js = MENU_JS.read_text(encoding="utf-8")
        match = re.search(r"function textoPrecio\(entry\)\{(.*?)\n\}", self.js, re.S)
        self.assertIsNotNone(match, "no se encontró textoPrecio()")
        self.cuerpo = match.group(1)

    def test_revisa_entry_niveles_antes_del_string_unico(self):
        self.assertIn("entry.niveles", self.cuerpo)

    def test_cada_nivel_se_envuelve_en_precio_nivel(self):
        self.assertIn("precio-nivel", self.cuerpo)

    def test_usa_la_etiqueta_de_cada_nivel_no_un_texto_fijo(self):
        self.assertIn("n.etiqueta", self.cuerpo)

    def test_extrasprecio_helper_existe_y_se_reusa(self):
        """extrasPrecio() evita duplicar la lógica de usd/eur/brl entre el
        camino con niveles y el string único de siempre."""
        self.assertIn("function extrasPrecio(o)", self.js)
        self.assertIn("extrasPrecio(entry)", self.js)
        self.assertIn("extrasPrecio(n)", self.js)

    def test_sin_niveles_sigue_devolviendo_el_string_unico_de_siempre(self):
        """La rama sin 'niveles' (la mayoría de los productos, con un solo
        precio) no debe tocarse: mismo esc(entry.ars) que antes de este
        cambio. El bloque if(entry.niveles){...} usa esc(n.ars), no
        esc(entry.ars) -- así que esta cadena solo puede venir de la rama
        de precio único, sin necesidad de aislarla con más precisión."""
        self.assertIn("esc(entry.ars)", self.cuerpo)


class TestPrecioNivelEnCss(unittest.TestCase):
    def setUp(self):
        self.css = MENU_CSS.read_text(encoding="utf-8")

    def test_precio_nivel_es_block_para_apilarse_en_dos_lineas(self):
        match = re.search(r"\.precio-nivel\{([^}]*)\}", self.css)
        self.assertIsNotNone(match, "no se encontró la regla .precio-nivel")
        self.assertIn("display:block", match.group(1).replace(" ", ""))
