"""Campañas desde la hoja Calendario (tipo "campana", 2026-10-14).

Un bloque destacado en la portada y en el menú, con título, texto y botón de
pedido por WhatsApp, que aparece y desaparece solo según las fechas.
Pruebas estáticas (no hay Node ni Selenium en CI); la lógica de fechas se probó
además en navegador."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))
import aplicar_calendario as ac  # noqa: E402
import calendario  # noqa: E402

AGENDA = (ROOT / "assets" / "js" / "agenda.js").read_text(encoding="utf-8")
TPL_WEB = (ROOT / "web" / "templates" / "index.template.html").read_text(encoding="utf-8")
TPL_MENU = (ROOT / "templates" / "menu.template.html").read_text(encoding="utf-8")
CSS_WEB = (ROOT / "web" / "assets" / "css" / "site.css").read_text(encoding="utf-8")
CSS_MENU = (ROOT / "assets" / "css" / "menu.css").read_text(encoding="utf-8")


def _doc(*eventos):
    return {"version": 1, "zona_horaria": calendario.ZONA_HORARIA, "activo": True, "eventos": list(eventos)}


CAMPANA = {"id": "mama", "tipo": "campana", "desde": "2026-10-13", "hasta": "2026-10-18",
           "titulo": "Día de la Madre", "titulo_en": "Mother’s Day",
           "mensaje": "Domingo 18 de octubre.", "mensaje_en": "Sunday 18 October."}


class TestValidacion(unittest.TestCase):
    def test_campana_valida(self):
        self.assertEqual(calendario.validar(_doc(CAMPANA)), [])

    def test_el_titulo_es_obligatorio_y_el_mensaje_opcional(self):
        sin_titulo = {k: v for k, v in CAMPANA.items() if k not in ("titulo", "titulo_en")}
        self.assertTrue(calendario.validar(_doc(sin_titulo)))
        solo_titulo = {k: v for k, v in CAMPANA.items() if k not in ("mensaje", "mensaje_en")}
        self.assertEqual(calendario.validar(_doc(solo_titulo)), [])

    def test_titulo_de_hasta_40_caracteres_sin_html_ni_enlaces(self):
        self.assertEqual(calendario.validar(_doc(dict(CAMPANA, titulo="x" * 40))), [])
        self.assertTrue(calendario.validar(_doc(dict(CAMPANA, titulo="x" * 41))))
        self.assertTrue(calendario.validar(_doc(dict(CAMPANA, titulo="<b>Hola</b>"))))
        self.assertTrue(calendario.validar(_doc(dict(CAMPANA, titulo="Mirá https://x.com"))))
        self.assertTrue(calendario.validar(_doc(dict(CAMPANA, titulo_en=" con espacio"))))

    def test_campos_de_otros_tipos_no_valen_en_una_campana(self):
        self.assertTrue(calendario.validar(_doc(dict(CAMPANA, tema="encantada"))))
        self.assertTrue(calendario.validar(_doc(dict(CAMPANA, horario="09:00-14:00"))))

    def test_el_titulo_no_vale_en_otros_tipos(self):
        aviso = {"id": "a", "tipo": "aviso", "desde": "2026-10-20", "hasta": "2026-10-21", "mensaje": "Hola"}
        self.assertTrue(calendario.validar(_doc(dict(aviso, titulo="No"))))

    def test_se_embebe_con_titulo_y_mensaje_y_escapado(self):
        embebido = json.loads(calendario.json_embebido(_doc(CAMPANA)))
        ev = embebido["eventos"][0]
        self.assertEqual((ev["tipo"], ev["titulo"], ev["titulo_en"]), ("campana", "Día de la Madre", "Mother’s Day"))
        crudo = calendario.json_embebido(_doc(dict(CAMPANA, titulo="A & B")))
        self.assertNotIn("<", crudo)
        self.assertNotIn("&", crudo)

    def test_el_calendario_del_repo_trae_el_dia_de_la_madre_y_es_valido(self):
        doc = calendario.cargar()
        ids = {e["id"]: e for e in doc["eventos"]}
        self.assertIn("dia-de-la-madre-2026", ids)
        self.assertEqual(ids["dia-de-la-madre-2026"]["hasta"], "2026-10-18")


class TestHoja(unittest.TestCase):
    ENC = "id,tipo,tema,desde,hasta,prioridad,activo,horario,mensaje,mensaje_en,titulo,titulo_en,nota"

    def test_la_campana_se_carga_desde_la_hoja(self):
        doc, problemas = ac.parsear_csv(self.ENC + "\n"
                                        "mama,campana,,2026-10-13,2026-10-18,20,Sí,,Domingo 18,Sunday 18,Día de la Madre,Mother’s Day,\n")
        self.assertEqual(problemas, [])
        ev = doc["eventos"][0]
        self.assertEqual((ev["tipo"], ev["titulo"], ev["titulo_en"]), ("campana", "Día de la Madre", "Mother’s Day"))
        self.assertEqual(calendario.validar(doc), [])

    def test_una_hoja_sin_las_columnas_nuevas_sigue_andando(self):
        doc, problemas = ac.parsear_csv("tipo,desde,hasta,mensaje\naviso,2026-10-20,2026-10-21,Hola\n")
        self.assertEqual(problemas, [])

    def test_campana_sin_titulo_es_error_con_numero_de_fila(self):
        doc, problemas = ac.parsear_csv(self.ENC + "\nmama,campana,,2026-10-13,2026-10-18,,,,Hola,,,,\n")
        self.assertIsNone(doc)
        self.assertTrue(any("Fila 2" in p for p in problemas))
        self.assertFalse(any("Hola" in p for p in problemas), "no se reproduce el contenido de la celda")


class TestJsYPlantillas(unittest.TestCase):
    def test_agenda_identica_en_los_dos_sitios(self):
        self.assertEqual(AGENDA, (ROOT / "web" / "assets" / "js" / "agenda.js").read_text(encoding="utf-8"))

    def test_rellena_con_textcontent_y_solo_arma_enlaces_de_whatsapp(self):
        self.assertIn("nodo.textContent = texto", AGENDA)
        self.assertIn("indexOf('https://wa.me/') === 0", AGENDA)
        self.assertIn("encodeURIComponent('Hola Amelí! Quiero hacer un pedido: ' + c.tituloOriginal)", AGENDA)
        for prohibido in ("innerHTML", "eval(", "fetch(", "setAttribute(", ".style"):
            self.assertNotIn(prohibido, AGENDA)

    def test_textos_de_la_campana_en_los_cinco_idiomas(self):
        for bloque in ("pedir", "ahora"):
            m = re.search(bloque + r": \{(.*?)\n    \}", AGENDA, re.S)
            self.assertIsNotNone(m, bloque)
            for idioma in ("es", "en", "pt", "fr", "it"):
                self.assertRegex(m.group(1), idioma + r": '")

    def test_la_portada_y_el_menu_tienen_el_contenedor_oculto_con_el_boton_de_whatsapp(self):
        for nombre, tpl, patron in (("web", TPL_WEB, r"https://wa\.me/__WHATSAPP_E164__"),
                                    ("menú", TPL_MENU, r"https://wa\.me/__WSP_NUMBER__")):
            m = re.search(r'<section class="campana" id="campanaDia"[^>]*hidden>(.*?)</section>', tpl, re.S)
            self.assertIsNotNone(m, nombre)
            self.assertRegex(m.group(1), patron)
            for clase in ("campana-etiqueta", "campana-titulo", "campana-mensaje", "campana-cta-texto"):
                self.assertIn(clase, m.group(1), f"{nombre}: falta {clase}")
        self.assertIn("data-auto", re.search(r'<section class="campana"[^>]*>', TPL_WEB).group(0))

    def test_estilos_en_los_dos_sitios_y_oculto_por_defecto(self):
        for nombre, css in (("web", CSS_WEB), ("menú", CSS_MENU)):
            self.assertIn(".campana[hidden]{display:none}", css, nombre)
            self.assertIn("curvas-nivel.svg", css[css.index("CAMPAÑA vigente"):], nombre)
        self.assertNotRegex(CSS_WEB[CSS_WEB.index("CAMPAÑA vigente"):], r"inset:\s*0\s+-\d")
        self.assertNotRegex(CSS_MENU[CSS_MENU.index("CAMPAÑA vigente"):], r"inset:\s*0\s+-\d")


if __name__ == "__main__":
    unittest.main()
