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
        "cats": [{"cod": "BEB", "orden": 1, "nom": {"es": "Bebidas"}}],
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
        self.assertTrue(any("_fila" in e for e in errors))

    def test_campo_interno_en_config_es_error(self):
        doc = _doc_valido()
        doc["config"]["disponibilidad_csv_url"] = "https://docs.google.com/x"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("disponibilidad_csv_url" in e for e in errors))

    def test_falta_clave_de_primer_nivel(self):
        doc = _doc_valido()
        del doc["precios"]
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("precios" in e for e in errors))

    def test_campo_raiz_desconocido_es_error(self):
        """Antes de esta corrección, un campo extra en la raíz (ej.
        'backoffice') pasaba sin ningún error -- allowlist real ahora."""
        doc = _doc_valido()
        doc["backoffice"] = {"costos": "no deberían estar acá"}
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("backoffice" in e for e in errors), errors)

    def test_campo_desconocido_en_categoria_es_error(self):
        """Antes de esta corrección, 'nota_interna' en una categoría
        pasaba sin ningún error."""
        doc = _doc_valido()
        doc["cats"][0]["nota_interna"] = "esto es interno"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("nota_interna" in e for e in errors), errors)

    def test_campo_desconocido_en_precio_es_error(self):
        doc = _doc_valido()
        doc["precios"]["BEB001"]["costo_interno"] = 100
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("costo_interno" in e for e in errors), errors)

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
        self.assertTrue(any("ZZZ" in e for e in errors))

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
        self.assertTrue(any("en_camino" in e for e in errors))


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
        self.assertTrue(any("__ALGO__" in e for e in errors))

    def test_marcador_con_digitos_se_detecta(self):
        """Antes de esta corrección, el patrón __[A-Z_]+__ no reconocía
        dígitos -- __ALGO2__ o __ALGO_123__ pasaban sin detectarse."""
        doc = _doc_valido()
        doc["prods"][0]["n"]["es"] = "__ALGO2__"
        errors, _ = vjp.validate_menu_json(doc)
        self.assertTrue(any("__ALGO2__" in e for e in errors), errors)

        doc2 = _doc_valido()
        doc2["prods"][0]["d"]["es"] = "texto __ALGO_123__ mezclado"
        errors2, _ = vjp.validate_menu_json(doc2)
        self.assertTrue(any("__ALGO_123__" in e for e in errors2), errors2)


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
