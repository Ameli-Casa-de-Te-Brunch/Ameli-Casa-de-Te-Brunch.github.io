"""El menú y la portada comparten identidad visual (2026-10-13).

Pruebas estáticas (sin navegador): que las piezas compartidas existan y que el
menú siga siendo una herramienta de uso rápido (encabezado no fijo, sin SVG
suelto que agrande el área de scroll).
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLA = (RAIZ / "templates" / "menu.template.html").read_text(encoding="utf-8")
CSS = (RAIZ / "assets" / "css" / "menu.css").read_text(encoding="utf-8")
JS = (RAIZ / "assets" / "js" / "menu.js").read_text(encoding="utf-8")


class TestUnificacionMenu(unittest.TestCase):
    def test_boton_inicio_espejo_del_boton_menu_de_la_portada(self):
        self.assertIn('class="header-menu" id="homeLink" href="/"', PLANTILLA)
        m = re.search(r" inicio:\{([^}]*)\}", JS)
        self.assertIsNotNone(m, "falta UI.inicio")
        for idioma in ("es", "en", "pt", "fr", "it"):
            self.assertRegex(m.group(1), rf"{idioma}:'[^']+'")
        self.assertIn("$('homeLink').textContent=UI.inicio[lang]", JS)

    def test_orden_igual_a_la_portada_foto_y_despues_franja(self):
        self.assertLess(PLANTILLA.index('class="hero-foto"'), PLANTILLA.index('class="topbar-info"'))
        self.assertLess(PLANTILLA.index('class="topbar-info"'), PLANTILLA.index('class="hero-texto"'))

    def test_las_curvas_de_nivel_existen_y_se_usan_como_mascara(self):
        self.assertTrue((RAIZ / "assets" / "img" / "curvas-nivel.svg").is_file())
        self.assertIn("mask:url('../img/curvas-nivel.svg')", CSS)

    def test_las_bandas_a_todo_el_ancho_no_agrandan_el_scroll(self):
        """Una capa más ancha que la pantalla (inset negativo) en el celular amplía el
        viewport a ~3 veces el ancho: las bandas se hacen solo con box-shadow + clip-path."""
        bloque = CSS[CSS.index("UNIFICACIÓN CON LA PORTADA"):]
        self.assertNotRegex(bloque, r"inset:\s*0\s+-\d")
        self.assertNotIn("html{overflow-x", bloque.replace(" ", ""))

    def test_el_encabezado_del_menu_no_es_fijo_la_barra_de_categorias_si(self):
        bloque = CSS[CSS.index("UNIFICACIÓN CON LA PORTADA"):]
        topbar = re.search(r"\.topbar\{([^}]*)\}", bloque, re.S).group(1)
        self.assertNotIn("sticky", topbar)
        self.assertNotIn("fixed", topbar)
        self.assertRegex(CSS, r"\.navcat\{position:sticky;top:0")

    def test_boton_flotante_circular_con_texto_para_lectores_de_pantalla(self):
        self.assertIn('<span class="sr-only">WhatsApp</span>', PLANTILLA)
        self.assertRegex(CSS, r"\.wsp\{width:56px; height:56px;[^}]*border-radius:50%")


if __name__ == "__main__":
    unittest.main()
