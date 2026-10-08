"""Pruebas del sistema de temas por calendario (2026-10-08): build/calendario.py,
data/calendario.json, assets/js/tema.js y assets/css/temas.css (menú y web).

Estáticas, mismo criterio que el resto del proyecto (no hay Selenium ni Node
en CI): se lee el código real y se verifican con expresiones regulares las
propiedades que garantizan que (1) un dato mal cargado no se publica, (2) fuera
de fechas el sitio es el diseño original y (3) el tema nunca pisa el
alto contraste, ni usa nada externo. La lógica de fechas de tema.js se probó
además en navegador (bordes de medianoche de Mendoza) al construirla."""
import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))
import calendario  # noqa: E402
import render  # noqa: E402

TEMA_JS_MENU = ROOT / "assets" / "js" / "tema.js"
TEMA_JS_WEB = ROOT / "web" / "assets" / "js" / "tema.js"
TEMAS_CSS = {"menú": ROOT / "assets" / "css" / "temas.css", "web": ROOT / "web" / "assets" / "css" / "temas.css"}
IMG_DIRS = {"menú": ROOT / "assets" / "img", "web": ROOT / "web" / "assets" / "img"}
TEMPLATES = {"menú": ROOT / "templates" / "menu.template.html", "web": ROOT / "web" / "templates" / "index.template.html"}


def _doc_valido():
    return {
        "version": 1, "zona_horaria": "America/Argentina/Mendoza", "activo": True,
        "eventos": [{"id": "encantada-2026", "tipo": "tema", "tema": "encantada",
                     "desde": "2026-10-19", "hasta": "2026-11-02", "prioridad": 10}],
    }


class TestCalendarioReal(unittest.TestCase):
    def test_el_calendario_del_repo_es_valido(self):
        doc = calendario.cargar()
        self.assertEqual(calendario.validar(doc), [])

    def test_cada_tema_conocido_tiene_css_en_los_dos_sitios(self):
        for tema in calendario.TEMAS_CONOCIDOS:
            for sitio, ruta in TEMAS_CSS.items():
                css = ruta.read_text(encoding="utf-8")
                self.assertIn(f'html[data-tema="{tema}"]', css, f"{sitio}: falta el CSS del tema {tema}")


class TestValidacion(unittest.TestCase):
    def _errores(self, mutar):
        doc = copy.deepcopy(_doc_valido())
        mutar(doc)
        return calendario.validar(doc)

    def test_valido_no_tiene_errores(self):
        self.assertEqual(calendario.validar(_doc_valido()), [])

    def test_no_es_objeto(self):
        self.assertTrue(calendario.validar([]))

    def test_version_zona_y_activo(self):
        self.assertTrue(self._errores(lambda d: d.update(version=2)))
        self.assertTrue(self._errores(lambda d: d.update(zona_horaria="UTC")))
        self.assertTrue(self._errores(lambda d: d.update(activo="si")))
        self.assertTrue(self._errores(lambda d: d.pop("activo")))

    def test_campo_extra_en_la_raiz(self):
        self.assertTrue(self._errores(lambda d: d.update(script="<x>")))

    def test_evento_con_campo_extra_o_faltante(self):
        self.assertTrue(self._errores(lambda d: d["eventos"][0].update(html="<b>")))
        self.assertTrue(self._errores(lambda d: d["eventos"][0].pop("hasta")))

    def test_tema_o_tipo_desconocido(self):
        self.assertTrue(self._errores(lambda d: d["eventos"][0].update(tema="halowen")))
        self.assertTrue(self._errores(lambda d: d["eventos"][0].update(tipo="cierre")))

    def test_fechas_invalidas(self):
        for malo in ("2026-13-01", "2026-02-30", "19/10/2026", "2026-1-1", "", None, 20261019):
            with self.subTest(malo=malo):
                self.assertTrue(self._errores(lambda d: d["eventos"][0].update(desde=malo)))

    def test_desde_posterior_a_hasta(self):
        self.assertTrue(self._errores(lambda d: d["eventos"][0].update(desde="2026-11-03")))

    def test_desde_igual_a_hasta_es_un_dia_valido(self):
        self.assertEqual(self._errores(lambda d: d["eventos"][0].update(desde="2026-10-31", hasta="2026-10-31")), [])

    def test_prioridad(self):
        for malo in (-1, 101, 1.5, "10", True):
            with self.subTest(malo=malo):
                self.assertTrue(self._errores(lambda d: d["eventos"][0].update(prioridad=malo)))

    def test_id_repetido_o_invalido(self):
        def repetir(d):
            d["eventos"].append(dict(d["eventos"][0]))
        self.assertTrue(self._errores(repetir))
        self.assertTrue(self._errores(lambda d: d["eventos"][0].update(id="Con Espacios")))

    def test_demasiados_eventos(self):
        def inflar(d):
            d["eventos"] = [dict(d["eventos"][0], id=f"e{i}") for i in range(calendario.MAX_EVENTOS + 1)]
        self.assertTrue(self._errores(inflar))

    def test_cargar_levanta_valueerror_con_json_roto_o_inexistente(self):
        with self.assertRaises(ValueError):
            calendario.cargar(ROOT / "data" / "no-existe.json")


class TestJsonEmbebido(unittest.TestCase):
    def test_es_json_valido_y_trae_temas_y_eventos(self):
        salida = json.loads(calendario.json_embebido(_doc_valido()))
        self.assertTrue(salida["activo"])
        self.assertEqual(salida["temas"], list(calendario.TEMAS_CONOCIDOS))
        self.assertEqual(salida["eventos"][0]["desde"], "2026-10-19")

    def test_nunca_contiene_caracteres_que_cierren_el_script(self):
        doc = _doc_valido()
        doc["eventos"][0]["tema"] = "</script><img src=x onerror=alert(1)>& "
        texto = calendario.json_embebido(doc)
        for peligroso in ("<", ">", "&", " ", " "):
            self.assertNotIn(peligroso, texto)
        self.assertIn("</script>", json.loads(texto)["eventos"][0]["tema"])  # el dato se conserva, solo escapado

    def test_prioridad_ausente_se_embebe_como_cero(self):
        doc = _doc_valido()
        del doc["eventos"][0]["prioridad"]
        self.assertEqual(json.loads(calendario.json_embebido(doc))["eventos"][0]["prioridad"], 0)

    def test_interruptor_apagado_se_embebe_apagado(self):
        doc = _doc_valido()
        doc["activo"] = False
        self.assertFalse(json.loads(calendario.json_embebido(doc))["activo"])


class TestTemaJs(unittest.TestCase):
    def setUp(self):
        self.js = TEMA_JS_MENU.read_text(encoding="utf-8")

    def test_identico_en_menu_y_web(self):
        self.assertEqual(self.js, TEMA_JS_WEB.read_text(encoding="utf-8"),
                         "tema.js se desalineó entre assets/js y web/assets/js")

    def test_sin_red_ni_ejecucion_dinamica(self):
        for prohibido in ("fetch(", "XMLHttpRequest", "eval(", "new Function", "innerHTML",
                          "document.write", "localStorage", "sessionStorage", "document.cookie"):
            self.assertNotIn(prohibido, self.js)

    def test_solo_pone_el_atributo_data_tema(self):
        self.assertEqual(re.findall(r"setAttribute\('([^']+)'", self.js), ["data-tema"])
        self.assertNotIn(".style", self.js)

    def test_interruptor_general_y_previsualizacion(self):
        self.assertIn("cal.activo !== true", self.js)
        self.assertIn("'ninguno'", self.js)
        self.assertIn("cal.temas.indexOf(pedido) !== -1", self.js)  # solo temas con CSS real

    def test_usa_la_zona_de_mendoza_con_respaldo_utc_menos_3(self):
        self.assertIn("timeZone: cal.zona", self.js)
        self.assertIn("3 * 3600 * 1000", self.js)

    def test_desempate_por_prioridad_y_despues_por_desde_mas_reciente(self):
        self.assertIn("ev.prioridad > mejor.prioridad", self.js)
        self.assertIn("ev.desde > mejor.desde", self.js)

    def test_fechas_inclusivas(self):
        self.assertIn("hoy < ev.desde || hoy > ev.hasta", self.js)


def _selectores_de_primer_nivel(css: str):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"@keyframes[^{]+\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)
    for selectores, _cuerpo in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        for sel in selectores.split(","):
            if sel.strip():
                yield sel.strip()


class TestTemasCss(unittest.TestCase):
    def test_todas_las_reglas_cuelgan_de_html_data_tema(self):
        for sitio, ruta in TEMAS_CSS.items():
            sels = list(_selectores_de_primer_nivel(ruta.read_text(encoding="utf-8")))
            self.assertTrue(sels, f"{sitio}: no se encontraron reglas")
            for sel in sels:
                self.assertTrue(sel.startswith('html[data-tema="'),
                                f"{sitio}: la regla '{sel}' se aplicaría fuera de un tema")

    def test_ninguna_regla_se_aplica_en_alto_contraste(self):
        for sitio, ruta in TEMAS_CSS.items():
            for sel in _selectores_de_primer_nivel(ruta.read_text(encoding="utf-8")):
                self.assertIn(':not([data-contraste="alto"])', sel, f"{sitio}: '{sel}' pisaría el alto contraste")

    def test_solo_imagenes_propias_y_existentes_sin_urls_externas_ni_data(self):
        for sitio, ruta in TEMAS_CSS.items():
            css = ruta.read_text(encoding="utf-8")
            css_sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
            self.assertNotRegex(css_sin_comentarios, r"https?:|//|data:|@import")
            urls = re.findall(r'url\("([^"]+)"\)', css_sin_comentarios)
            self.assertTrue(urls)
            for url in urls:
                self.assertRegex(url, r"^\.\./img/tema-[a-z0-9-]+\.svg$")
                self.assertTrue((IMG_DIRS[sitio] / Path(url).name).exists(), f"{sitio}: falta {url}")

    def test_el_menu_no_tiene_animaciones(self):
        css = TEMAS_CSS["menú"].read_text(encoding="utf-8")
        sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        self.assertNotIn("animation", sin_comentarios)
        self.assertNotIn("@keyframes", sin_comentarios)

    def test_la_animacion_de_la_web_usa_solo_transform(self):
        css = TEMAS_CSS["web"].read_text(encoding="utf-8")
        keyframes = re.findall(r"@keyframes\s+[\w-]+\s*\{(.*?)\}\s*\}", css, flags=re.S)
        self.assertTrue(keyframes)
        for cuerpo in keyframes:
            propiedades = set(re.findall(r"([\w-]+)\s*:", cuerpo))
            self.assertEqual(propiedades, {"transform"})

    def test_el_menu_no_oscurece_el_fondo_de_lectura(self):
        css = TEMAS_CSS["menú"].read_text(encoding="utf-8")
        self.assertNotRegex(css, r"--blanco\s*:\s*#[0-4]")
        self.assertNotRegex(css, r"--crema\s*:\s*#[0-4]")


class TestIntegracionEnTemplates(unittest.TestCase):
    def test_los_dos_templates_tienen_el_bloque_de_datos_antes_del_script(self):
        for sitio, ruta in TEMPLATES.items():
            html = ruta.read_text(encoding="utf-8")
            head = html.split("</head>")[0]
            datos = head.find('<script type="application/json" id="ameli-calendario">__CALENDARIO_JSON__</script>')
            script = head.find('<script src="assets/js/tema.js')
            css = head.find('href="assets/css/temas.css')
            self.assertGreater(datos, 0, f"{sitio}: falta el bloque de datos en el head")
            self.assertGreater(script, datos, f"{sitio}: tema.js tiene que ir después de los datos")
            self.assertGreater(css, 0, f"{sitio}: falta temas.css")
            self.assertNotIn("defer", head[script:script + 80], f"{sitio}: tema.js no debe llevar defer")

    def test_temas_css_se_carga_despues_del_css_principal(self):
        for sitio, principal in (("menú", "assets/css/menu.css"), ("web", "assets/css/site.css")):
            head = TEMPLATES[sitio].read_text(encoding="utf-8").split("</head>")[0]
            self.assertLess(head.find(principal), head.find("assets/css/temas.css"))

    def test_el_menu_renderizado_embebe_el_calendario_y_mantiene_la_csp_estricta(self):
        data = json.loads((ROOT / "data" / "menu.json").read_text(encoding="utf-8"))
        html = render.render(data, TEMPLATES["menú"].read_text(encoding="utf-8"))
        self.assertNotIn("__CALENDARIO_JSON__", html)
        m = re.search(r'<script type="application/json" id="ameli-calendario">(.*?)</script>', html, re.S)
        self.assertIsNotNone(m)
        self.assertEqual(json.loads(m.group(1))["temas"], list(calendario.TEMAS_CONOCIDOS))
        csp = re.search(r'Content-Security-Policy" content="([^"]+)"', html).group(1)
        self.assertNotIn("unsafe-inline", csp)
        self.assertNotIn("unsafe-eval", csp)
        self.assertIn("style-src 'self'", csp)
        self.assertIn("img-src 'self'", csp)
        self.assertIn("connect-src 'none'", csp)


if __name__ == "__main__":
    unittest.main()
