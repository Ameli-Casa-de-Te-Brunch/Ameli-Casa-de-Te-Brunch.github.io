"""Diseño combinado (Amelí + capítulos): reglas que no deben romperse (2026-10-14).

Todo el diseño cuelga de html[data-estilo="capitulos"]: sin ese atributo el sitio
vuelve al diseño anterior. Pruebas estáticas (no hay Node ni Selenium en CI)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL_WEB = (ROOT / "web" / "templates" / "index.template.html").read_text(encoding="utf-8")
TPL_MENU = (ROOT / "templates" / "menu.template.html").read_text(encoding="utf-8")
CSS_WEB = (ROOT / "web" / "assets" / "css" / "site.css").read_text(encoding="utf-8")
CSS_MENU = (ROOT / "assets" / "css" / "menu.css").read_text(encoding="utf-8")
MENU_JS = (ROOT / "assets" / "js" / "menu.js").read_text(encoding="utf-8")


def _bloque(css):
    return css[css.index('DISEÑO COMBINADO "capítulos"'):]


BLOQUES = {"web": _bloque(CSS_WEB), "menú": _bloque(CSS_MENU)}


class TestAtributoYPiezasDecorativas(unittest.TestCase):
    def test_el_atributo_esta_en_los_dos_html(self):
        for nombre, tpl in (("web", TPL_WEB), ("menú", TPL_MENU)):
            self.assertIn('<html lang="es" data-estilo="capitulos">', tpl, nombre)

    def test_las_leyendas_son_decorativas_para_lectores_de_pantalla(self):
        for nombre, tpl in (("web", TPL_WEB), ("menú", TPL_MENU)):
            self.assertNotIn('class="cinta"', tpl, nombre)  # la cinta se sacó (2026-10-31)
            for m in re.findall(r'<p class="sticker[^"]*"([^>]*)>', tpl):
                self.assertIn('aria-hidden="true"', m, nombre)
            self.assertGreaterEqual(tpl.count('class="sticker '), 1, nombre)

    def test_sin_el_atributo_las_piezas_nuevas_estan_ocultas(self):
        for nombre, bloque in BLOQUES.items():
            self.assertIn(".barra-pedido,.sticker{display:none}", bloque, nombre)

    def test_las_dos_paginas_tienen_barra_de_pedido_de_whatsapp(self):
        self.assertRegex(TPL_WEB, r'<a class="barra-pedido" href="https://wa\.me/__WHATSAPP_E164__"')
        self.assertRegex(TPL_MENU, r'<a class="barra-pedido" id="barraPedido" href="https://wa\.me/__WSP_NUMBER__')
        # el botón de WhatsApp del menú vive dentro del bloque opcional: sin número no hay barra
        bloques = re.findall(r"<!--WSP_START-->(.*?)<!--WSP_END-->", TPL_MENU, re.S)
        self.assertTrue(any('class="barra-pedido"' in x for x in bloques))

    def test_la_portada_no_afirma_retiro_en_el_local_hasta_confirmarlo(self):
        self.assertNotIn("retiralo", TPL_WEB.lower())
        self.assertNotIn("retiralo", TPL_MENU.lower())


class TestBarraDePedidoEnCincoIdiomas(unittest.TestCase):
    def test_textos_en_los_cinco_idiomas_y_se_escriben_con_textcontent(self):
        m = re.search(r" barraPedido:\{(.*?)\},\n", MENU_JS)
        self.assertIsNotNone(m, "falta UI.barraPedido")
        for idioma in ("es", "en", "pt", "fr", "it"):
            self.assertRegex(m.group(1), idioma + r":'[^']+'")
        self.assertIn("$('barraPedido').textContent=UI.barraPedido[lang]", MENU_JS)
        # si el menú se arma sin número de WhatsApp, no hay barra y el script no falla
        self.assertIn("if($('barraPedido'))", MENU_JS)


class TestCssDelDisenoCombinado(unittest.TestCase):
    def test_los_hover_solo_valen_con_mouse(self):
        for nombre, bloque in BLOQUES.items():
            for linea in bloque.splitlines():
                if ":hover" in linea:
                    self.assertIn("@media (hover:hover) and (pointer:fine)", linea,
                                  f"{nombre}: hover sin compuerta -> {linea.strip()[:80]}")

    def test_sin_capas_mas_anchas_que_la_pantalla_ni_transition_all(self):
        for nombre, bloque in BLOQUES.items():
            self.assertNotRegex(bloque, r"inset:\s*0\s+-\d", nombre)
            self.assertNotIn("transition:all", bloque.replace(" ", ""), nombre)

    def test_la_leyenda_sobre_la_foto_tiene_fondo_suficiente_para_el_contraste(self):
        for nombre, bloque in BLOQUES.items():
            m = re.search(r"\.sticker\{[^}]*background:rgba\(20,27,17,(\.\d+)\)", bloque, re.S)
            self.assertIsNotNone(m, nombre)
            self.assertGreaterEqual(float(m.group(1)), 0.62, f"{nombre}: fondo de la leyenda demasiado transparente")

    def test_se_detiene_todo_con_reducir_movimiento(self):
        for nombre, css in (("web", CSS_WEB), ("menú", CSS_MENU)):
            self.assertNotIn("cinta", css, nombre)
            self.assertIn('html[data-movimiento="reducido"] *{', css.replace("\n", ""), nombre)
            self.assertIn("prefers-reduced-motion", css, nombre)

    def test_las_alturas_fijas_salen_de_variables_no_de_numeros_sueltos(self):
        self.assertNotIn("118px", BLOQUES["web"])
        self.assertIn("var(--alto-encabezado)", BLOQUES["web"])
        self.assertIn("var(--alto-barra)", BLOQUES["web"])
        self.assertIn("var(--alto-barra)", BLOQUES["menú"])

    def test_en_320_px_el_logotipo_no_pisa_los_controles(self):
        """Medido en el navegador a 320 px: centrado, el logotipo pisaba Aa (portada) y el idioma (menú)."""
        self.assertRegex(BLOQUES["web"], r"@media \(max-width:359px\)\{[^@]*\.logo-enlace\{position:static; transform:none\}")
        self.assertRegex(BLOQUES["menú"], r"@media \(max-width:359px\)\{[^}]*\.marca-top\{position:static; transform:none\}")

    def test_los_titulos_grandes_se_reparten_sin_palabra_huerfana(self):
        self.assertIn("text-wrap:balance", BLOQUES["web"])
        self.assertIn("text-wrap:balance", BLOQUES["menú"])

    def test_las_llaves_del_bloque_estan_balanceadas(self):
        """Una llave de más o de menos en un @media anida o rompe las reglas que siguen (pasó una vez mientras se movía un bloque)."""
        for nombre, bloque in BLOQUES.items():
            self.assertEqual(bloque.count("{"), bloque.count("}"), nombre)

    def test_la_barra_de_pedido_no_tapa_el_final_de_la_pagina(self):
        self.assertIn("body{padding-bottom:calc(var(--alto-barra)", BLOQUES["web"].replace("\n", " "))
        self.assertIn("footer{padding-bottom:calc(60px", BLOQUES["menú"])


if __name__ == "__main__":
    unittest.main()
