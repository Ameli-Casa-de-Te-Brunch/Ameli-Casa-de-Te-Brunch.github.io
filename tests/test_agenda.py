"""Pruebas de los cierres, horarios especiales y avisos del calendario
(2026-10-12): tipos nuevos en build/calendario.py, columnas nuevas de la hoja
(build/aplicar_calendario.py), assets/js/agenda.js y su integración en el
cartel "Abierto/Cerrado" del menú y en el aviso del día de los dos sitios.

Estáticas (no hay Node ni Selenium en CI); la lógica de fechas y la selección
de eventos se probaron además en navegador, con fechas simuladas."""
import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))
import aplicar_calendario as ac  # noqa: E402
import calendario  # noqa: E402
import render  # noqa: E402

AGENDA_MENU = ROOT / "assets" / "js" / "agenda.js"
AGENDA_WEB = ROOT / "web" / "assets" / "js" / "agenda.js"
MENU_JS = ROOT / "assets" / "js" / "menu.js"
MENU_CSS = ROOT / "assets" / "css" / "menu.css"
SITE_CSS = ROOT / "web" / "assets" / "css" / "site.css"
TEMPLATES = {"menú": ROOT / "templates" / "menu.template.html", "web": ROOT / "web" / "templates" / "index.template.html"}


def _doc(*eventos):
    return {"version": 1, "zona_horaria": calendario.ZONA_HORARIA, "activo": True, "eventos": list(eventos)}


CIERRE = {"id": "navidad", "tipo": "cierre", "desde": "2026-12-25", "hasta": "2026-12-25"}
ESPECIAL = {"id": "nochebuena", "tipo": "horario_especial", "desde": "2026-12-24", "hasta": "2026-12-24",
            "horario": "09:00-14:00"}
AVISO = {"id": "sin-medialunas", "tipo": "aviso", "desde": "2026-10-20", "hasta": "2026-10-21",
         "mensaje": "Hoy no hay medialunas", "mensaje_en": "No croissants today"}


class TestTiposNuevos(unittest.TestCase):
    def test_los_tres_tipos_validos(self):
        self.assertEqual(calendario.validar(_doc(CIERRE, ESPECIAL, AVISO)), [])

    def test_cierre_con_mensaje_opcional(self):
        self.assertEqual(calendario.validar(_doc(dict(CIERRE, mensaje="Cerrado por feriado"))), [])

    def test_obligatorios_por_tipo(self):
        sin_horario = {k: v for k, v in ESPECIAL.items() if k != "horario"}
        sin_mensaje = {k: v for k, v in AVISO.items() if k not in ("mensaje", "mensaje_en")}
        self.assertTrue(calendario.validar(_doc(sin_horario)))
        self.assertTrue(calendario.validar(_doc(sin_mensaje)))

    def test_campos_que_no_corresponden_al_tipo_son_error(self):
        self.assertTrue(calendario.validar(_doc(dict(CIERRE, tema="encantada"))))
        self.assertTrue(calendario.validar(_doc(dict(CIERRE, horario="09:00-14:00"))))
        self.assertTrue(calendario.validar(_doc(dict(AVISO, horario="09:00-14:00"))))
        self.assertTrue(calendario.validar(_doc({"id": "t", "tipo": "tema", "tema": "encantada",
                                                  "desde": "2026-10-19", "hasta": "2026-11-02", "mensaje": "x"})))

    def test_tipo_desconocido(self):
        self.assertTrue(calendario.validar(_doc(dict(CIERRE, tipo="vacaciones"))))

    def test_horarios_validos(self):
        casos = {
            "09:00-14:00": [[9, 0, 14, 0]],
            "9:00-13:00;17:30-21:00": [[9, 0, 13, 0], [17, 30, 21, 0]],
            "08:00 - 12:00 ; 14:00 - 18:00 ; 19:00-23:59": [[8, 0, 12, 0], [14, 0, 18, 0], [19, 0, 23, 59]],
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(calendario.franjas_de_horario(texto), esperado)

    def test_horarios_invalidos(self):
        for texto in ("", "cerrado", "14:00-10:00", "10:00-10:00", "10:00-14:00; 13:00-18:00",
                      "25:00-26:00", "10:60-12:00", "10-14", "10:00-14:00; 15:00-16:00; 17:00-18:00; 19:00-20:00",
                      "18:00-21:00; 09:00-13:00", None, 1000):
            with self.subTest(texto=texto):
                self.assertIsNone(calendario.franjas_de_horario(texto))

    def test_mensajes_validos_e_invalidos(self):
        self.assertTrue(calendario.mensaje_valido("Hoy cerramos a las 17 hs ¡gracias!"))
        for malo in ("", " ", " con espacio al inicio", "con espacio al final ", "a" * 141, "<b>hola</b>",
                     "mirá http://ejemplo.com", "entrá a WWW.ejemplo.com", "dos\nlíneas", "tab\taqui", None, 5):
            with self.subTest(malo=malo):
                self.assertFalse(calendario.mensaje_valido(malo))

    def test_mensaje_de_140_caracteres_es_el_limite_valido(self):
        self.assertTrue(calendario.mensaje_valido("a" * 140))

    def test_json_embebido_trae_franjas_y_mensajes_y_los_escapa(self):
        doc = _doc(ESPECIAL, dict(AVISO, mensaje="Tortas & café", mensaje_en="Cakes & coffee"))
        texto = calendario.json_embebido(doc)
        for peligroso in ("<", ">", "&"):
            self.assertNotIn(peligroso, texto)
        datos = json.loads(texto)
        especial = next(e for e in datos["eventos"] if e["tipo"] == "horario_especial")
        self.assertEqual(especial["franjas"], [[9, 0, 14, 0]])
        self.assertNotIn("horario", especial)  # el texto crudo no viaja: solo las franjas ya validadas
        aviso = next(e for e in datos["eventos"] if e["tipo"] == "aviso")
        self.assertEqual(aviso["mensaje"], "Tortas & café")
        self.assertNotIn("tema", aviso)


class TestHojaConTiposNuevos(unittest.TestCase):
    ENC = "id,tipo,tema,desde,hasta,prioridad,activo,horario,mensaje,mensaje_en,nota"

    def _filas(self, *filas):
        return "\n".join((self.ENC,) + filas) + "\n"

    def test_los_tres_tipos_desde_la_hoja(self):
        doc, problemas = ac.parsear_csv(self._filas(
            "navidad,cierre,,2026-12-25,2026-12-25,,,,,,feriado",
            "nochebuena,horario especial,,2026-12-24,2026-12-24,5,Sí,09:00-14:00,Cerramos temprano,We close early,",
            ',aviso,,2026-10-20,2026-10-21,,,,"Hoy no hay medialunas, perdón",,'))
        self.assertEqual(problemas, [])
        self.assertEqual([e["tipo"] for e in doc["eventos"]], ["cierre", "horario_especial", "aviso"])
        self.assertEqual(doc["eventos"][1]["horario"], "09:00-14:00")
        self.assertEqual(doc["eventos"][2]["mensaje"], "Hoy no hay medialunas, perdón")
        self.assertEqual(calendario.validar(doc), [])

    def test_sin_columna_tema_ni_las_nuevas_sigue_andando(self):
        doc, problemas = ac.parsear_csv("tipo,desde,hasta,mensaje\naviso,2026-10-20,2026-10-21,Hola\n")
        self.assertEqual(problemas, [])
        self.assertEqual(doc["eventos"][0]["mensaje"], "Hola")

    def test_errores_con_numero_de_fila_y_sin_reproducir_la_celda(self):
        secreto = "TEXTO SECRETO http://x.com"
        _, problemas = ac.parsear_csv(self._filas(f",aviso,,2026-10-20,2026-10-21,,,,{secreto},,"))
        self.assertTrue(problemas)
        self.assertTrue(problemas[0].startswith("Fila 2:"))
        self.assertNotIn("SECRETO", " ".join(problemas))
        _, problemas = ac.parsear_csv(self._filas(",horario_especial,,2026-10-20,2026-10-21,,,25:00-26:00,,,"))
        self.assertTrue(problemas)
        self.assertNotIn("25:00", " ".join(problemas))

    def test_un_tema_en_una_fila_de_cierre_es_error_no_se_ignora(self):
        doc, problemas = ac.parsear_csv(self._filas(",cierre,encantada,2026-12-25,2026-12-25,,,,,,"))
        self.assertIsNone(doc)
        self.assertTrue(problemas)

    def test_horario_especial_sin_horario(self):
        doc, problemas = ac.parsear_csv(self._filas(",horario_especial,,2026-12-24,2026-12-24,,,,,,"))
        self.assertIsNone(doc)
        self.assertTrue(problemas)


class TestAgendaJs(unittest.TestCase):
    def setUp(self):
        self.js = AGENDA_MENU.read_text(encoding="utf-8")

    def test_identico_en_menu_y_web(self):
        self.assertEqual(self.js, AGENDA_WEB.read_text(encoding="utf-8"),
                         "agenda.js se desalineó entre assets/js y web/assets/js")

    def test_sin_red_html_ni_ejecucion_dinamica(self):
        for prohibido in ("fetch(", "XMLHttpRequest", "eval(", "new Function", "innerHTML", "outerHTML",
                          "insertAdjacentHTML", "document.write", "localStorage", "sessionStorage", "document.cookie",
                          ".style", "setAttribute("):
            self.assertNotIn(prohibido, self.js)

    def test_los_mensajes_se_escriben_con_textcontent(self):
        self.assertIn("p.textContent = t.texto", self.js)
        self.assertIn("cont.textContent = ''", self.js)

    def test_cierre_le_gana_a_horario_especial_y_se_elige_por_prioridad_y_luego_desde(self):
        self.assertIn("var especial = cierre ? null : elegir(activos('horario_especial', fecha))", self.js)
        self.assertIn("a.prioridad !== b.prioridad", self.js)
        self.assertIn("a.desde < b.desde", self.js)

    def test_fechas_inclusivas_en_mendoza(self):
        self.assertIn("hoy >= ev.desde && hoy <= ev.hasta", self.js)
        self.assertIn("timeZone: zona", self.js)
        self.assertIn("3 * 3600 * 1000", self.js)

    def test_maximo_tres_textos_y_ingles_con_respaldo(self):
        self.assertIn("salida.slice(0, 3)", self.js)
        self.assertIn("lang === 'en' && ev.mensaje_en", self.js)

    def test_textos_automaticos_en_los_cinco_idiomas(self):
        for bloque in ("cierre", "especial"):
            m = re.search(bloque + r": \{(.*?)\n    \}", self.js, re.S)
            self.assertIsNotNone(m, bloque)
            for idioma in ("es", "en", "pt", "fr", "it"):
                self.assertRegex(m.group(1), idioma + r": '")

    def test_no_depende_de_la_clave_activo_de_los_temas(self):
        self.assertNotIn("cal.activo", self.js)

    def test_solo_pinta_sola_en_contenedores_marcados_data_auto(self):
        self.assertIn("hasAttribute('data-auto')", self.js)


class TestIntegracion(unittest.TestCase):
    def test_menu_js_usa_el_calendario_para_el_estado(self):
        js = MENU_JS.read_text(encoding="utf-8")
        cuerpo = re.search(r"function estadoNegocio\(\)\{(.*?)\r?\n\}", js, re.S).group(1)
        self.assertIn("window.AmeliAgenda.hoy()", cuerpo)
        self.assertIn("ag.cierre", cuerpo)
        self.assertIn("cierreHoy:true", cuerpo)
        self.assertIn("ag.franjas", cuerpo)
        self.assertIn("HORARIO[dia]", cuerpo)  # sin evento, el horario habitual de siempre
        self.assertIn("est.cierreHoy", js)
        self.assertIn("UI.cerradoHoy[lang]", js)
        self.assertIn("window.AmeliAgenda.pintar(lang)", js)

    def test_cerrado_hoy_esta_traducido_a_los_cinco_idiomas(self):
        js = MENU_JS.read_text(encoding="utf-8")
        linea = re.search(r"cerradoHoy:\{([^\n]*)\}", js).group(1)
        for idioma in ("es", "en", "pt", "fr", "it"):
            self.assertIn(idioma + ":'", linea)

    def test_templates_cargan_agenda_js_en_el_head_despues_del_calendario(self):
        for sitio, ruta in TEMPLATES.items():
            head = ruta.read_text(encoding="utf-8").split("</head>")[0]
            datos = head.find('id="ameli-calendario"')
            script = head.find('<script src="assets/js/agenda.js')
            self.assertGreater(script, datos, sitio)
            self.assertNotIn("defer", head[script:script + 80], sitio)

    def test_contenedor_del_aviso_en_los_dos_templates(self):
        for sitio, ruta in TEMPLATES.items():
            html = ruta.read_text(encoding="utf-8")
            self.assertEqual(html.count('id="avisoDia"'), 1, sitio)
            self.assertRegex(html, r'<div class="aviso-dia" id="avisoDia"[^>]*role="status" hidden></div>')
        self.assertIn("data-auto", TEMPLATES["web"].read_text(encoding="utf-8"))
        self.assertNotIn("data-auto", TEMPLATES["menú"].read_text(encoding="utf-8"))  # el menú lo pinta menu.js

    def test_estilos_del_aviso_en_los_dos_sitios(self):
        for css in (MENU_CSS, SITE_CSS):
            texto = css.read_text(encoding="utf-8")
            self.assertIn(".aviso-dia[hidden]{display:none}", texto)
            self.assertIn(".aviso-dia p.cierre", texto)

    def test_el_menu_renderizado_conserva_la_csp_y_el_calendario_con_los_tipos_nuevos(self):
        data = json.loads((ROOT / "data" / "menu.json").read_text(encoding="utf-8"))
        html = render.render(data, TEMPLATES["menú"].read_text(encoding="utf-8"))
        self.assertNotIn("__CALENDARIO_JSON__", html)
        csp = re.search(r'Content-Security-Policy" content="([^"]+)"', html).group(1)
        self.assertNotIn("unsafe-inline", csp)
        self.assertIn("connect-src 'none'", csp)


class TestCalendarioDelRepoSigueValido(unittest.TestCase):
    def test_valido(self):
        self.assertEqual(calendario.validar(calendario.cargar()), [])

    def test_copia_profunda_de_un_doc_con_todos_los_tipos_pasa_el_embebido(self):
        doc = copy.deepcopy(_doc(CIERRE, ESPECIAL, AVISO))
        self.assertTrue(json.loads(calendario.json_embebido(doc))["eventos"])


if __name__ == "__main__":
    unittest.main()
