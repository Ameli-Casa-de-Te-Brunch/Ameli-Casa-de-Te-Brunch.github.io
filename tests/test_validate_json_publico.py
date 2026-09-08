"""Pruebas de build/validate_json_publico.py: estructura, campos públicos,
IDs, categorías, disponibilidad, URLs/handles, marcadores sin reemplazar --
y una corrida contra el data/menu.json real committeado, que tiene que dar
cero errores (si esto falla, algo en el JSON público real está roto).
Solo biblioteca estándar."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
import validate_json_publico as vjp  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MENU_JSON_REAL = ROOT / "data" / "menu.json"


def _doc_valido():
    return {
        "cats": [{"cod": "BEB", "orden": 1, "nom": {
            "es": "Bebidas", "en": "Drinks", "pt": "Bebidas", "fr": "Boissons", "it": "Bevande",
        }}],
        "prods": [{
            "id": "BEB001", "cat": "BEB", "orden": 1, "dest": False,
            "n": {"es": "Café", "en": "Coffee", "pt": "Café", "fr": "Café", "it": "Caffè"},
            "d": {"es": "d", "en": "d", "pt": "d", "fr": "d", "it": "d"},
            "m": [], "b": [], "img": None,
        }],
        # "ars" ya viene formateado como string de display (ver
        # extract_common.formatear_precio()) -- nunca un número crudo.
        "precios": {"BEB001": {"ars": "$ 1.000"}},
        "config": {
            "moneda": "ARS", "whatsapp": "5492604106653", "instagram": "ameli.casadete",
            "direccion": "Malargüe, Mendoza, Argentina",
            "url_base": "https://ameli-casa-de-te-brunch.github.io",
            "tripadvisor": None, "google_resenas": None,
        },
    }


class TestDocumentoValido(unittest.TestCase):
    def test_documento_minimo_valido_no_tiene_errores(self):
        errors, _warnings = vjp.validate_menu_json(_doc_valido())
        self.assertEqual(errors, [])


class TestCamposYTipos(unittest.TestCase):
    def test_campo_no_publico_en_producto_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["_fila"] = 12
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("campo(s) no público" in e for e in errors), errors)
        # el nombre de la clave desconocida nunca se reproduce en el mensaje
        self.assertFalse(any("_fila" in e for e in errors), errors)

    def test_campo_interno_en_config_es_error(self):
        doc = _doc_valido()
        doc["config"]["disponibilidad_csv_url"] = "https://docs.google.com/x"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("'config' tiene" in e for e in errors), errors)
        self.assertFalse(any("disponibilidad_csv_url" in e for e in errors), errors)

    def test_falta_clave_de_primer_nivel(self):
        doc = _doc_valido()
        del doc["precios"]
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("precios" in e for e in errors))

    def test_campo_raiz_desconocido_es_error(self):
        """Antes de esta corrección, un campo extra en la raíz (ej.
        'backoffice') pasaba sin ningún error -- allowlist real ahora. El
        nombre de la clave nunca se reproduce en el mensaje."""
        doc = _doc_valido()
        doc["backoffice"] = {"costos": "no deberían estar acá"}
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("clave(s) de primer nivel no permitida" in e for e in errors), errors)
        self.assertFalse(any("backoffice" in e for e in errors), errors)

    def test_campo_desconocido_en_categoria_es_error(self):
        """Antes de esta corrección, 'nota_interna' en una categoría
        pasaba sin ningún error. El nombre de la clave nunca se reproduce."""
        doc = _doc_valido()
        doc["cats"][0]["nota_interna"] = "esto es interno"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("campo(s) no permitido" in e for e in errors), errors)
        self.assertFalse(any("nota_interna" in e for e in errors), errors)

    def test_campo_desconocido_en_precio_es_error(self):
        doc = _doc_valido()
        doc["precios"]["BEB001"]["costo_interno"] = 100
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("campo(s) no permitido" in e for e in errors), errors)
        self.assertFalse(any("costo_interno" in e for e in errors), errors)

    def test_tipo_incorrecto_de_id(self):
        doc = _doc_valido()
        doc["prods"][0]["id"] = 12345
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("'id'" in e for e in errors), errors)

    def test_tipo_incorrecto_de_orden(self):
        doc = _doc_valido()
        doc["prods"][0]["orden"] = "primero"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("orden" in e for e in errors), errors)

    def test_tipo_incorrecto_de_dest(self):
        doc = _doc_valido()
        doc["prods"][0]["dest"] = "sí"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("dest" in e for e in errors), errors)

    def test_tipo_incorrecto_de_img(self):
        doc = _doc_valido()
        doc["prods"][0]["img"] = 42
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("img" in e for e in errors), errors)

    def test_tipo_incorrecto_de_precio_ars(self):
        """'ars' ya viene formateado como string de display (ver
        extract_common.formatear_precio()) -- un número crudo, no un
        string, es el tipo incorrecto acá."""
        doc = _doc_valido()
        doc["precios"]["BEB001"]["ars"] = 1000
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("ars" in e for e in errors), errors)

    def test_traduccion_faltante_es_error_no_aviso(self):
        """El maestro ya exige los 5 idiomas (ver validate.py) -- acá tiene
        que ser tan error como allá, no un aviso que no bloquea."""
        doc = _doc_valido()
        del doc["prods"][0]["n"]["it"]
        errors, warnings = vjp.validate_menu_json(doc)
        self.assertTrue(any("n.it" in e for e in errors), errors)
        self.assertFalse(any("n.it" in w for w in warnings))


class TestIdsYReferencias(unittest.TestCase):
    def test_id_duplicado(self):
        doc = _doc_valido()
        doc["prods"].append(dict(doc["prods"][0]))
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("duplicado" in e for e in errors))

    def test_categoria_inexistente(self):
        doc = _doc_valido()
        doc["prods"][0]["cat"] = "ZZZ"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("no existe entre las categorías" in e for e in errors), errors)

    def test_precio_huerfano(self):
        doc = _doc_valido()
        doc["precios"]["NOEXISTE"] = {"ars": 1}
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("huérfana" in e for e in errors))


class TestDisponibilidad(unittest.TestCase):
    def test_codigo_valido_no_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["disp"] = "agotado"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertEqual(errors, [])

    def test_codigo_invalido_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["disp"] = "en_camino"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("código de disponibilidad no reconocido" in e for e in errors), errors)
        self.assertFalse(any("en_camino" in e for e in errors), errors)


class TestConfigValidacion(unittest.TestCase):
    def test_whatsapp_invalido(self):
        doc = _doc_valido()
        doc["config"]["whatsapp"] = "123"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("whatsapp" in e for e in errors))

    def test_instagram_invalido(self):
        doc = _doc_valido()
        doc["config"]["instagram"] = "<script>"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("instagram" in e for e in errors))

    def test_url_base_dominio_no_permitido(self):
        doc = _doc_valido()
        doc["config"]["url_base"] = "https://ejemplo-no-permitido.com"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("url_base" in e for e in errors))


class TestMarcadoresSinReemplazar(unittest.TestCase):
    def test_marcador_suelto_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["n"]["es"] = "__ALGO__"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("marcador(es) de plantilla" in e for e in errors), errors)
        # el marcador en sí (que podría llevar pegado cualquier texto del
        # maestro) nunca se reproduce en el mensaje
        self.assertFalse(any("__ALGO__" in e for e in errors), errors)

    def test_marcador_con_digitos_se_detecta(self):
        """Antes de esta corrección, el patrón __[A-Z_]+__ no reconocía
        dígitos -- __ALGO2__ o __ALGO_123__ pasaban sin detectarse."""
        doc = _doc_valido()
        doc["prods"][0]["n"]["es"] = "__ALGO2__"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("marcador(es) de plantilla" in e for e in errors), errors)
        self.assertFalse(any("__ALGO2__" in e for e in errors), errors)

        doc2 = _doc_valido()
        doc2["prods"][0]["d"]["es"] = "texto __ALGO_123__ mezclado"
        errors2, _ = vjp.validate_menu_json(doc2)
        self.assertTrue(any("marcador(es) de plantilla" in e for e in errors2), errors2)
        self.assertFalse(any("__ALGO_123__" in e for e in errors2), errors2)


class TestEntradaNoValida(unittest.TestCase):
    """JSON inválido o raíz no-objeto: error limpio, nunca un traceback."""

    def test_raiz_no_es_objeto(self):
        errors, warnings = vjp.validate_menu_json(["esto", "es", "una", "lista"])
        self.assertEqual(warnings, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("no es un objeto", errors[0])

    def test_raiz_string(self):
        errors, _ = vjp.validate_menu_json("no soy un objeto")
        self.assertEqual(len(errors), 1)

    def test_main_con_json_invalido_sale_con_codigo_1_sin_traceback(self):
        import subprocess
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write("{ esto no es json válido ][")
            ruta = f.name
        try:
            import os
            env = dict(os.environ, PYTHONIOENCODING="utf-8")
            resultado = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parent.parent / "build" / "validate_json_publico.py"), ruta],
                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
            )
        finally:
            Path(ruta).unlink()
        self.assertEqual(resultado.returncode, 1)
        self.assertNotIn("Traceback", resultado.stdout + resultado.stderr)
        self.assertIn("[ERROR]", resultado.stdout)

    def test_main_con_raiz_no_objeto_sale_con_codigo_1(self):
        import subprocess
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write('["no", "soy", "un", "objeto"]')
            ruta = f.name
        try:
            import os
            env = dict(os.environ, PYTHONIOENCODING="utf-8")
            resultado = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parent.parent / "build" / "validate_json_publico.py"), ruta],
                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
            )
        finally:
            Path(ruta).unlink()
        self.assertEqual(resultado.returncode, 1)
        self.assertNotIn("Traceback", resultado.stdout + resultado.stderr)


class TestCamposInternosYEnumeraciones(unittest.TestCase):
    """Casos exactos comprobados independientemente que antes pasaban sin
    error -- uno por uno, tal como se reportaron."""

    def test_cat_nom_interno_es_error(self):
        doc = _doc_valido()
        doc["cats"][0]["nom"]["interno"] = "secreto"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("idioma(s) no permitido" in e for e in errors), errors)
        self.assertFalse(any("interno" in e for e in errors), errors)

    def test_prod_n_costo_interno_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["n"]["costo_interno"] = "secreto"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("idioma(s) no permitido" in e for e in errors), errors)
        self.assertFalse(any("costo_interno" in e for e in errors), errors)

    def test_categoria_sin_nom_en_es_error(self):
        doc = _doc_valido()
        del doc["cats"][0]["nom"]["en"]
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("nom.en" in e for e in errors), errors)

    def test_badge_desconocido_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["b"] = ["valor-que-no-existe"]
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("'b'" in e and "no reconocido" in e for e in errors), errors)
        self.assertFalse(any("valor-que-no-existe" in e for e in errors), errors)

    def test_momento_desconocido_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["m"] = ["valor-que-no-existe"]
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("'m'" in e and "no reconocido" in e for e in errors), errors)
        self.assertFalse(any("valor-que-no-existe" in e for e in errors), errors)

    def test_momento_dulce_es_valido(self):
        """'dulce' es un chip real de menu.js (CHIPS[0]), no un error."""
        doc = _doc_valido()
        doc["prods"][0]["m"] = ["dulce"]
        errors, _ = vjp.validate_menu_json(doc)
        self.assertEqual(errors, [])

    def test_alerg_clave_privada_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["alerg"] = {"nota_privada": True}
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("'alerg'" in e and "no reconocida" in e for e in errors), errors)
        self.assertFalse(any("nota_privada" in e for e in errors), errors)

    def test_alerg_clave_valida_con_tipo_incorrecto_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["alerg"] = {"veg": "sí"}
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("alerg.veg" in e for e in errors), errors)

    def test_leche_valor_desconocido_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["leche"] = ["secreto"]
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("'leche'" in e and "no reconocido" in e for e in errors), errors)
        self.assertFalse(any("secreto" in e for e in errors), errors)

    def test_leche_duplicada_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["leche"] = ["veg", "veg"]
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("duplicado" in e for e in errors), errors)

    def test_whatsapp_numerico_es_error(self):
        """Un número JSON no debe aceptarse silenciosamente aunque, como
        string, coincidiría con la regex de 8-15 dígitos."""
        doc = _doc_valido()
        doc["config"]["whatsapp"] = 12345678
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("whatsapp" in e and "string" in e for e in errors), errors)

    def test_alt_idioma_no_permitido_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["alt"] = {"es": "una foto", "klingon": "texto"}
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("'alt'" in e and "idioma(s) no permitido" in e for e in errors), errors)
        self.assertFalse(any("klingon" in e for e in errors), errors)

    def test_alt_ausente_no_es_error(self):
        """alt es opcional: menu.js cae al nombre del producto si falta
        (ver altProducto() en assets/js/menu.js)."""
        doc = _doc_valido()
        self.assertNotIn("alt", doc["prods"][0])
        errors, _ = vjp.validate_menu_json(doc)
        self.assertEqual(errors, [])


class TestImagenRuta(unittest.TestCase):
    def test_ruta_relativa_bajo_assets_img_es_valida(self):
        doc = _doc_valido()
        doc["prods"][0]["img"] = "assets/img/tyt004.webp"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertEqual(errors, [])

    def test_url_externa_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["img"] = "https://ejemplo-externo.com/foto.jpg"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("'img'" in e for e in errors), errors)

    def test_protocolo_relativo_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["img"] = "//ejemplo-externo.com/foto.jpg"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("'img'" in e for e in errors), errors)

    def test_data_uri_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["img"] = "data:image/png;base64,AAAA"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("'img'" in e for e in errors), errors)

    def test_javascript_uri_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["img"] = "javascript:alert(1)"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("'img'" in e for e in errors), errors)

    def test_ruta_absoluta_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["img"] = "/etc/passwd"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("'img'" in e for e in errors), errors)

    def test_traversal_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["img"] = "assets/img/../../secretos/x.jpg"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("'img'" in e for e in errors), errors)

    def test_fuera_de_assets_img_es_error(self):
        doc = _doc_valido()
        doc["prods"][0]["img"] = "assets/otra-cosa/x.jpg"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("'img'" in e for e in errors), errors)


SENTINEL = "SECRETO_NO_DEBE_APARECER_123"


class TestSentinelNuncaSeReproduce(unittest.TestCase):
    """El centinela SECRETO_NO_DEBE_APARECER_123 nunca debe aparecer en la
    lista de errores/avisos de validate_menu_json(), sin importar en qué
    campo se lo inyecte -- cubre disponibilidad, momentos, badges, leche,
    alérgenos, Instagram, WhatsApp, URLs, claves desconocidas (en todos los
    niveles) e IDs no validados. Una prueba final corre main() como
    subproceso real y revisa que tampoco aparezca en stdout/stderr."""

    def _sin_centinela(self, doc):
        errors, warnings = vjp.validate_menu_json(doc)
        combinado = " ".join(errors) + " ".join(warnings)
        self.assertNotIn(SENTINEL, combinado, errors + warnings)
        return errors

    def test_disponibilidad(self):
        doc = _doc_valido()
        doc["prods"][0]["disp"] = SENTINEL
        self.assertTrue(self._sin_centinela(doc))

    def test_momentos(self):
        doc = _doc_valido()
        doc["prods"][0]["m"] = [SENTINEL]
        self.assertTrue(self._sin_centinela(doc))

    def test_badges(self):
        doc = _doc_valido()
        doc["prods"][0]["b"] = [SENTINEL]
        self.assertTrue(self._sin_centinela(doc))

    def test_leche(self):
        doc = _doc_valido()
        doc["prods"][0]["leche"] = [SENTINEL]
        self.assertTrue(self._sin_centinela(doc))

    def test_alergenos_clave(self):
        doc = _doc_valido()
        doc["prods"][0]["alerg"] = {SENTINEL: True}
        self.assertTrue(self._sin_centinela(doc))

    def test_instagram(self):
        doc = _doc_valido()
        # el centinela solo (letras/números/guion bajo) matchea el regex de
        # handle válido -- se le agrega un caracter no permitido para
        # forzar el camino de error y probar igual que no se reproduce.
        doc["config"]["instagram"] = SENTINEL + "!"
        errors = self._sin_centinela(doc)
        self.assertTrue(errors)

    def test_whatsapp(self):
        doc = _doc_valido()
        doc["config"]["whatsapp"] = SENTINEL
        self.assertTrue(self._sin_centinela(doc))

    def test_urls(self):
        doc = _doc_valido()
        doc["config"]["url_base"] = f"https://ameli-casa-de-te-brunch.github.io/?x={SENTINEL}"
        doc["config"]["tripadvisor"] = f"https://sitio-no-permitido.com/{SENTINEL}"
        doc["config"]["google_resenas"] = f"https://otro-no-permitido.com/{SENTINEL}"
        self.assertTrue(self._sin_centinela(doc))

    def test_claves_desconocidas_raiz(self):
        doc = _doc_valido()
        doc[SENTINEL] = True
        self.assertTrue(self._sin_centinela(doc))

    def test_claves_desconocidas_categoria(self):
        doc = _doc_valido()
        doc["cats"][0][SENTINEL] = True
        self.assertTrue(self._sin_centinela(doc))

    def test_claves_desconocidas_producto(self):
        doc = _doc_valido()
        doc["prods"][0][SENTINEL] = True
        self.assertTrue(self._sin_centinela(doc))

    def test_claves_desconocidas_precio(self):
        doc = _doc_valido()
        doc["precios"]["BEB001"][SENTINEL] = True
        self.assertTrue(self._sin_centinela(doc))

    def test_claves_desconocidas_config(self):
        doc = _doc_valido()
        doc["config"][SENTINEL] = True
        self.assertTrue(self._sin_centinela(doc))

    def test_claves_desconocidas_alt(self):
        doc = _doc_valido()
        doc["prods"][0]["alt"] = {SENTINEL: "texto"}
        self.assertTrue(self._sin_centinela(doc))

    def test_ids_no_validados_producto(self):
        doc = _doc_valido()
        doc["prods"][0]["id"] = SENTINEL
        self.assertTrue(self._sin_centinela(doc))

    def test_ids_no_validados_categoria(self):
        doc = _doc_valido()
        doc["cats"][0]["cod"] = SENTINEL
        doc["prods"][0]["cat"] = SENTINEL
        self.assertTrue(self._sin_centinela(doc))

    def test_ids_no_validados_precio_huerfano(self):
        doc = _doc_valido()
        doc["precios"][SENTINEL] = {"ars": "$ 1"}
        self.assertTrue(self._sin_centinela(doc))

    def test_marcador_de_plantilla_con_centinela(self):
        doc = _doc_valido()
        doc["prods"][0]["n"]["es"] = f"__{SENTINEL}__"
        self.assertTrue(self._sin_centinela(doc))

    def test_main_subproceso_no_imprime_el_centinela(self):
        """Corrida real de main() (subproceso, no solo la función pura) con
        el centinela en varios campos a la vez -- ni stdout ni stderr
        pueden mostrarlo, y tampoco puede haber traceback."""
        import os
        import subprocess
        import tempfile

        doc = _doc_valido()
        doc["prods"][0]["m"] = [SENTINEL]
        doc["prods"][0]["alerg"] = {SENTINEL: True}
        doc["config"]["instagram"] = SENTINEL
        doc[SENTINEL] = True

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False)
            ruta = f.name
        try:
            env = dict(os.environ, PYTHONIOENCODING="utf-8")
            resultado = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parent.parent / "build" / "validate_json_publico.py"), ruta],
                capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
            )
        finally:
            Path(ruta).unlink()

        self.assertEqual(resultado.returncode, 1)
        self.assertNotIn(SENTINEL, resultado.stdout)
        self.assertNotIn(SENTINEL, resultado.stderr)
        self.assertNotIn("Traceback", resultado.stdout + resultado.stderr)


class TestEnumeracionesNuncaLevantanTypeError(unittest.TestCase):
    """Un elemento no-string, no hasheable o de tipo mixto en m/b/leche (o
    un valor no-string en 'disp') nunca debe levantar TypeError al armar
    un set() o al ordenar -- tiene que convertirse en un error controlado."""

    def _validar_sin_excepcion(self, doc):
        try:
            errors, _warnings = vjp.validate_menu_json(doc)
        except Exception as e:
            self.fail(f"validate_menu_json levantó {type(e).__name__}: {e}")
        return errors

    def test_m_con_objeto_anidado(self):
        doc = _doc_valido()
        doc["prods"][0]["m"] = [{"a": 1}]
        errors = self._validar_sin_excepcion(doc)
        self.assertTrue(any("'m'" in e for e in errors), errors)

    def test_m_con_lista_anidada(self):
        doc = _doc_valido()
        doc["prods"][0]["m"] = [[1, 2]]
        errors = self._validar_sin_excepcion(doc)
        self.assertTrue(any("'m'" in e for e in errors), errors)

    def test_m_con_numero_y_null_mixtos(self):
        doc = _doc_valido()
        doc["prods"][0]["m"] = [5, None, True]
        errors = self._validar_sin_excepcion(doc)
        self.assertTrue(any("'m'" in e for e in errors), errors)

    def test_b_con_objeto_anidado(self):
        doc = _doc_valido()
        doc["prods"][0]["b"] = [{"a": 1}]
        errors = self._validar_sin_excepcion(doc)
        self.assertTrue(any("'b'" in e for e in errors), errors)

    def test_leche_con_tipos_mixtos(self):
        doc = _doc_valido()
        doc["prods"][0]["leche"] = [None, 5, {"a": 1}, ["x"]]
        errors = self._validar_sin_excepcion(doc)
        self.assertTrue(any("'leche'" in e for e in errors), errors)

    def test_disp_objeto_no_levanta_typeerror(self):
        doc = _doc_valido()
        doc["prods"][0]["disp"] = {"a": 1}
        errors = self._validar_sin_excepcion(doc)
        self.assertTrue(any("disponibilidad" in e for e in errors), errors)

    def test_disp_lista_no_levanta_typeerror(self):
        doc = _doc_valido()
        doc["prods"][0]["disp"] = [1, 2]
        errors = self._validar_sin_excepcion(doc)
        self.assertTrue(any("disponibilidad" in e for e in errors), errors)

    def test_disp_numero_no_levanta_typeerror(self):
        doc = _doc_valido()
        doc["prods"][0]["disp"] = 12345
        errors = self._validar_sin_excepcion(doc)
        self.assertTrue(any("disponibilidad" in e for e in errors), errors)


class TestJsonPublicoReal(unittest.TestCase):
    """El JSON público committeado hoy tiene que pasar este validador con
    cero errores -- si esto falla, algo real está roto, no la prueba."""

    def test_menu_json_real_sin_errores(self):
        if not MENU_JSON_REAL.exists():
            self.skipTest(f"no existe {MENU_JSON_REAL} en este checkout")
        data = json.loads(MENU_JSON_REAL.read_text(encoding="utf-8"))
        errors, _warnings = vjp.validate_menu_json(data)
        self.assertEqual(errors, [], f"data/menu.json real tiene errores: {errors}")


if __name__ == "__main__":
    unittest.main()
