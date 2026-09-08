"""Pruebas de build.py (el orquestador local extract -> validate -> render):

- que "--dry-run --disponibilidad-estricta" invoque de verdad la
  validación estricta de disponibilidad en vivo (antes salía sin
  intentarla);
- que una falla estricta (con o sin --dry-run) no deje ningún output
  tocado: ni data/menu.json, ni dist/index.html, ni nada más;
- que una validación exitosa permita continuar y escribir los outputs;
- que data/menu.json persistido nunca incorpore la disponibilidad
  efímera aplicada en memoria para el render.

Todo con dobles (unittest.mock): nunca se usa un Excel real, nunca se
hace una descarga real ni se toca la hoja de disponibilidad real."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
import build  # noqa: E402
import aplicar_disponibilidad as ad  # noqa: E402


def _data_fake():
    """Forma mínima pero realista de lo que extract.extract() devuelve --
    suficiente para que extract.datos_publicos() (la función REAL, no un
    doble) la proyecte sin romperse."""
    return {
        "cats": [{"cod": "BEB", "orden": 1, "nom": {"es": "Bebidas"}}],
        "prods": [{"id": "BEB001", "cat": "BEB", "orden": 1, "n": {"es": "Café"}}],
        "precios": {"BEB001": {"ars": "$ 1.000"}},
        "config": {
            "disponibilidad_csv_url": "https://docs.google.com/fake-no-se-usa",
            "url_base": "https://ameli-casa-de-te-brunch.github.io",
        },
    }


class _ArgsFake:
    def __init__(self, dry_run, disponibilidad_estricta, template, out, publicar=False):
        self.dry_run = dry_run
        self.disponibilidad_estricta = disponibilidad_estricta
        self.publicar = publicar
        self.template = template
        self.out = out


class TestDryRunInvocaValidacionReal(unittest.TestCase):
    def test_dry_run_estricto_invoca_la_validacion_real(self):
        data = _data_fake()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            args = _ArgsFake(dry_run=True, disponibilidad_estricta=True,
                              template=tmp / "no-se-lee.html", out=tmp / "dist" / "index.html")
            with patch.object(build.extract, "extract", return_value=data), \
                 patch.object(build.validate, "validate", return_value=([], [])), \
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods", return_value=0) as mock_aplicar:
                build.ejecutar(args, Path("fake.xlsx"))

            mock_aplicar.assert_called_once()
            _, kwargs = mock_aplicar.call_args
            self.assertTrue(kwargs.get("estricto") is True or mock_aplicar.call_args[0][-1] is True,
                             "el dry-run estricto tiene que invocar aplicar_a_prods con estricto=True")
            # dry-run real: nada de esto se llegó a crear
            self.assertFalse((tmp / "dist").exists())

    def test_dry_run_no_estricto_no_exige_estricto_true(self):
        data = _data_fake()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            args = _ArgsFake(dry_run=True, disponibilidad_estricta=False,
                              template=tmp / "no-se-lee.html", out=tmp / "dist" / "index.html")
            with patch.object(build.extract, "extract", return_value=data), \
                 patch.object(build.validate, "validate", return_value=([], [])), \
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods", return_value=-1) as mock_aplicar:
                build.ejecutar(args, Path("fake.xlsx"))

            mock_aplicar.assert_called_once()
            _, kwargs = mock_aplicar.call_args
            self.assertFalse(kwargs.get("estricto", mock_aplicar.call_args[0][-1]))


class TestFalloEstrictoNoTocaNada(unittest.TestCase):
    def _correr_y_esperar_fallo(self, dry_run):
        data = _data_fake()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            menu_json = tmp / "data" / "menu.json"
            menu_json.parent.mkdir(parents=True)
            menu_json.write_text("CONTENIDO_ANTERIOR_INTACTO", encoding="utf-8")
            dist_dir = tmp / "dist"
            args = _ArgsFake(dry_run=dry_run, disponibilidad_estricta=True,
                              template=tmp / "no-se-lee.html", out=dist_dir / "index.html")

            with patch.object(build, "MENU_JSON", menu_json), \
                 patch.object(build.extract, "extract", return_value=data), \
                 patch.object(build.validate, "validate", return_value=([], [])), \
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods",
                               side_effect=ad.DisponibilidadInvalida("simulado: hoja no confiable")), \
                 patch.object(build.render, "render") as mock_render, \
                 patch.object(build.render, "copiar_assets") as mock_copiar, \
                 patch.object(build.render, "_escribir_seo_estatico") as mock_seo:
                with self.assertRaises(SystemExit) as cm:
                    build.ejecutar(args, Path("fake.xlsx"))
                self.assertEqual(cm.exception.code, 1)

            # data/menu.json: byte a byte igual a como estaba antes de correr build.py
            self.assertEqual(menu_json.read_text(encoding="utf-8"), "CONTENIDO_ANTERIOR_INTACTO")
            # dist/index.html, sitemap, robots: nada de esto se llegó a crear ni a llamar
            self.assertFalse(dist_dir.exists())
            mock_render.assert_not_called()
            mock_copiar.assert_not_called()
            mock_seo.assert_not_called()

    def test_fallo_estricto_sin_dry_run_no_toca_ningun_output(self):
        self._correr_y_esperar_fallo(dry_run=False)

    def test_fallo_estricto_con_dry_run_no_toca_ningun_output(self):
        self._correr_y_esperar_fallo(dry_run=True)


class TestValidacionExitosaPermiteContinuar(unittest.TestCase):
    def test_validacion_exitosa_escribe_los_outputs(self):
        data = _data_fake()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            menu_json = tmp / "data" / "menu.json"
            dist_dir = tmp / "dist"
            template_path = tmp / "template.html"
            template_path.write_text("PLANTILLA", encoding="utf-8")
            args = _ArgsFake(dry_run=False, disponibilidad_estricta=True,
                              template=template_path, out=dist_dir / "index.html")

            with patch.object(build, "MENU_JSON", menu_json), \
                 patch.object(build.extract, "extract", return_value=data), \
                 patch.object(build.validate, "validate", return_value=([], [])), \
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods", return_value=0), \
                 patch.object(build.render, "render", return_value="<html>fake</html>") as mock_render, \
                 patch.object(build.render, "copiar_assets") as mock_copiar, \
                 patch.object(build.render, "_escribir_seo_estatico") as mock_seo:
                build.ejecutar(args, Path("fake.xlsx"))

            self.assertTrue(menu_json.exists())
            self.assertEqual((dist_dir / "index.html").read_text(encoding="utf-8"), "<html>fake</html>")
            mock_render.assert_called_once()
            mock_copiar.assert_called_once()
            mock_seo.assert_called_once()

            publicado = json.loads(menu_json.read_text(encoding="utf-8"))
            self.assertEqual([p["id"] for p in publicado["prods"]], ["BEB001"])


class TestJsonPersistidoSinDisponibilidadEfimera(unittest.TestCase):
    def test_disponibilidad_efimera_no_llega_al_json_versionado(self):
        data = _data_fake()
        self.assertNotIn("disp", data["prods"][0])  # de partida: disponible, sin código

        def _mutar_en_memoria(prods, url, estricto):
            # Simula lo que hace aplicar_a_prods de verdad: muta la lista en
            # memoria (para que el render la vea), pero build.py ya calculó
            # el texto de data/menu.json ANTES de esta llamada.
            prods[0]["disp"] = "agotado"
            return 1

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            menu_json = tmp / "data" / "menu.json"
            dist_dir = tmp / "dist"
            template_path = tmp / "template.html"
            template_path.write_text("PLANTILLA", encoding="utf-8")
            args = _ArgsFake(dry_run=False, disponibilidad_estricta=True,
                              template=template_path, out=dist_dir / "index.html")

            render_calls = []

            def _render_falso(data_al_renderizar, template):
                # Capturamos una copia superficial del disp del producto en
                # el momento exacto en que render.render() es invocado.
                render_calls.append(data_al_renderizar["prods"][0].get("disp"))
                return "<html>fake</html>"

            with patch.object(build, "MENU_JSON", menu_json), \
                 patch.object(build.extract, "extract", return_value=data), \
                 patch.object(build.validate, "validate", return_value=([], [])), \
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods", side_effect=_mutar_en_memoria), \
                 patch.object(build.render, "render", side_effect=_render_falso), \
                 patch.object(build.render, "copiar_assets"), \
                 patch.object(build.render, "_escribir_seo_estatico"):
                build.ejecutar(args, Path("fake.xlsx"))

            # El render sí vio la disponibilidad efímera aplicada en memoria...
            self.assertEqual(render_calls, ["agotado"])
            # ...pero el data/menu.json escrito a disco (lo versionado) no la
            # incorpora: sigue reflejando el Excel, disponible por defecto.
            publicado = json.loads(menu_json.read_text(encoding="utf-8"))
            self.assertNotIn("disp", publicado["prods"][0])


if __name__ == "__main__":
    unittest.main()
