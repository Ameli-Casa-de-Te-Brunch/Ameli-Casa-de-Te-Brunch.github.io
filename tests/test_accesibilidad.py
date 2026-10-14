"""Accesibilidad (2026-10-14): reglas medidas en el navegador que no deben romperse.

Pruebas estáticas (no hay Node ni Selenium en CI)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL_WEB = (ROOT / "web" / "templates" / "index.template.html").read_text(encoding="utf-8")
TPL_MENU = (ROOT / "templates" / "menu.template.html").read_text(encoding="utf-8")
CSS_WEB = (ROOT / "web" / "assets" / "css" / "site.css").read_text(encoding="utf-8")
CSS_MENU = (ROOT / "assets" / "css" / "menu.css").read_text(encoding="utf-8")
MENU_JS = (ROOT / "assets" / "js" / "menu.js").read_text(encoding="utf-8")
SITE_JS = (ROOT / "web" / "assets" / "js" / "site.js").read_text(encoding="utf-8")


class TestMenuEstructura(unittest.TestCase):
    def test_enlace_para_saltar_es_lo_primero_del_body(self):
        m = re.search(r"<body>\s*<a class=\"skip-link\" id=\"skipLink\" href=\"#contenido-menu\">", TPL_MENU)
        self.assertIsNotNone(m)

    def test_un_solo_main_y_es_el_destino_del_salto(self):
        self.assertEqual(TPL_MENU.count("<main"), 1)
        self.assertIn('<main id="contenido-menu" tabindex="-1">', TPL_MENU)
        self.assertLess(TPL_MENU.index('<main id="contenido-menu"'), TPL_MENU.index('id="menu"'))
        self.assertLess(TPL_MENU.index('id="menu"'), TPL_MENU.index("</main>"))

    def test_el_texto_del_salto_esta_en_los_cinco_idiomas(self):
        m = re.search(r"saltar:\{([^}]*)\}", MENU_JS)
        self.assertIsNotNone(m)
        for lang in ("es", "en", "pt", "fr", "it"):
            self.assertRegex(m.group(1), lang + r":'[^']+'")
        self.assertIn("$('skipLink').textContent=UI.saltar[lang]", MENU_JS)

    def test_selector_de_idioma_sin_roles_listbox(self):
        self.assertNotIn('role="listbox"', TPL_MENU)
        self.assertNotIn('aria-haspopup="listbox"', TPL_MENU)
        self.assertNotIn('role="option"', MENU_JS)
        self.assertNotIn("aria-selected", MENU_JS)
        self.assertIn("aria-current", MENU_JS)
        self.assertIn('.langs-menu button[aria-current="true"]', CSS_MENU)

    def test_el_titulo_del_panel_de_navegacion_no_rompe_los_encabezados(self):
        self.assertNotIn('<h2 id="navTitle"', TPL_WEB)
        self.assertIn('<p id="navTitle" class="solo-lectores">', TPL_WEB)


class TestFocoYObjetivos(unittest.TestCase):
    def test_anillo_de_foco_claro_sobre_superficies_oscuras(self):
        for css in (CSS_MENU, CSS_WEB):
            bloque = css[css.index("ACCESIBILIDAD (2026-10-14)"):]
            self.assertIn("outline-color:var(--salvia)", bloque)
            self.assertIn(".barra-pedido:focus-visible", bloque)
        self.assertIn(".portada-hero a:focus-visible{outline-color:var(--blanco)}", CSS_WEB)

    def test_el_enlace_para_saltar_tiene_foco_visible(self):
        self.assertIn(".skip-link:focus-visible", CSS_MENU)
        self.assertIn(".skip-link:focus{transform:translateY(0)}", CSS_MENU)

    def test_objetivos_tactiles_de_44_px_en_el_menu(self):
        bloque = CSS_MENU[CSS_MENU.index("ACCESIBILIDAD (2026-10-14)"):]
        for regla in (".chip{min-height:44px}", ".navcat a{min-height:44px",
                      ".marca-top a{min-height:44px", ".buscador{min-height:48px}"):
            self.assertIn(regla, bloque)


class TestTextoAgrandado(unittest.TestCase):
    def test_el_menu_escribe_data_afs_donde_escribe_afs(self):
        self.assertEqual(MENU_JS.count("html.style.setProperty('--afs'"), MENU_JS.count("html.setAttribute('data-afs'"))
        self.assertGreaterEqual(MENU_JS.count("data-afs"), 2)

    def test_la_portada_escribe_y_borra_data_afs(self):
        self.assertIn("raiz.setAttribute('data-afs', String(estado.afs));", SITE_JS)
        self.assertIn("raiz.removeAttribute('data-afs');", SITE_JS)

    def test_el_menu_pasa_a_una_columna_y_los_precios_bajan_de_renglon(self):
        self.assertIn('html[data-afs="1.3"] .lista,html[data-afs="2"] .lista{grid-template-columns:1fr}', CSS_MENU)
        self.assertIn(".prod .precio{white-space:normal; overflow-wrap:anywhere}", CSS_MENU)

    def test_la_portada_saca_el_logotipo_del_centro_con_texto_grande(self):
        self.assertRegex(
            CSS_WEB,
            r'html\[data-estilo="capitulos"\]\[data-afs="2"\] \.logo-enlace\{position:static; transform:none\}',
        )
        self.assertRegex(
            CSS_WEB,
            r'\[data-afs="1\.3"\] \.site-header,\s*html\[data-estilo="capitulos"\]\[data-afs="2"\] \.site-header\{position:static\}',
        )


class TestMovimientoReducido(unittest.TestCase):
    def test_reducir_movimiento_conserva_fundidos_y_quita_el_movimiento(self):
        fundidos = "transition:opacity 150ms ease"
        for css in (CSS_MENU, CSS_WEB):
            self.assertEqual(len(re.findall(r"animation:none!important;\s*" + fundidos, css)), 2)
            self.assertNotRegex(css, r"\*\{transition:none!important;\s*animation:none!important\}")


class TestVersionDeEstilos(unittest.TestCase):
    def test_los_links_de_css_tienen_version(self):
        self.assertRegex(TPL_WEB, r"site\.css\?v=\d+-\d+")
        self.assertRegex(TPL_MENU, r"menu\.css\?v=\d+-\d+")


if __name__ == "__main__":
    unittest.main()
