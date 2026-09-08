"""Pruebas de build.py (el orquestador local extract -> validate -> render):

- que los 4 modos de disponibilidad se comporten exactamente como deben:
  "--dry-run" plano nunca consulta la hoja ni llama a aplicar_a_prods;
  "--dry-run --disponibilidad-estricta" sí la consulta, en modo estricto,
  y exige URL; la ejecución normal sin --disponibilidad-estricta conserva
  el comportamiento de siempre (aplica en modo no estricto si hay URL, si
  no la hay sigue sin aplicarla); la ejecución normal con
  --disponibilidad-estricta exige URL igual que el dry-run estricto;
- que el documento público (extract.datos_publicos(data)) se valide de
  verdad con validate_json_publico.validate_menu_json ANTES de escribir
  nada -- sin mockear esa validación, para probar que realmente se invoca;
- que cualquiera de esos fallos (disponibilidad o JSON público) deje
  data/menu.json, dist/index.html y todo lo demás exactamente igual que
  antes de correr build.py;
- que una corrida exitosa sí escriba los outputs, y que data/menu.json
  persistido nunca incorpore la disponibilidad efímera aplicada en
  memoria para el render.

Todo con dobles (unittest.mock) para extract.extract, validate.validate
(el validador "de Excel") y aplicar_disponibilidad.aplicar_a_prods: nunca
se usa un Excel real, nunca se hace una descarga real ni se toca la hoja
de disponibilidad real. validate_json_publico.validate_menu_json NUNCA se
mockea -- correr de verdad es justamente lo que estas pruebas necesitan
demostrar."""
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
    """Documento COMPLETO y válido -- con la validación real de
    validate_json_publico corriendo de verdad adentro de build.py (quinta
    corrección, punto 2), tiene que pasarla sin errores para que estas
    pruebas puedan llegar a ejercitar disponibilidad y escritura de
    archivos. Misma forma que _doc_valido() en
    tests/test_validate_json_publico.py."""
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
        "precios": {"BEB001": {"ars": "$ 1.000"}},
        "config": {
            "moneda": "ARS",
            "disponibilidad_csv_url": "https://docs.google.com/fake-no-se-usa",
            "url_base": "https://ameli-casa-de-te-brunch.github.io",
        },
    }


def _data_sin_url():
    data = _data_fake()
    data["config"]["disponibilidad_csv_url"] = None
    return data


class _ArgsFake:
    def __init__(self, dry_run, disponibilidad_estricta, template, out, publicar=False):
        self.dry_run = dry_run
        self.disponibilidad_estricta = disponibilidad_estricta
        self.publicar = publicar
        self.template = template
        self.out = out


class TestModosDeDisponibilidad(unittest.TestCase):
    """Los 4 modos, uno por uno, tal como los pide la especificación."""

    def test_1_dry_run_plano_no_llama_a_disponibilidad(self):
        """--dry-run sin --disponibilidad-estricta: nunca llama a
        aplicar_a_prods, sin importar que haya URL configurada -- no hace
        falta red para poder decir "esto pasaría"."""
        data = _data_fake()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            args = _ArgsFake(dry_run=True, disponibilidad_estricta=False,
                              template=tmp / "no-se-lee.html", out=tmp / "dist" / "index.html")
            with patch.object(build.extract, "extract", return_value=data), \
                 patch.object(build.validate, "validate", return_value=([], [])), \
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods") as mock_aplicar:
                build.ejecutar(args, Path("fake.xlsx"))

            mock_aplicar.assert_not_called()
            self.assertFalse((tmp / "dist").exists())

    def test_2_dry_run_estricto_invoca_la_validacion_real_con_estricto_true(self):
        """--dry-run --disponibilidad-estricta: sí consulta, con
        estricto=True."""
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
            self.assertFalse((tmp / "dist").exists())

    def test_3_dry_run_estricto_sin_url_falla(self):
        """--dry-run --disponibilidad-estricta exige URL -- si falta,
        falla antes de escribir nada, y ni siquiera llega a llamar a
        aplicar_a_prods (no hay nada que consultar)."""
        data = _data_sin_url()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            args = _ArgsFake(dry_run=True, disponibilidad_estricta=True,
                              template=tmp / "no-se-lee.html", out=tmp / "dist" / "index.html")
            with patch.object(build.extract, "extract", return_value=data), \
                 patch.object(build.validate, "validate", return_value=([], [])), \
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods") as mock_aplicar:
                with self.assertRaises(SystemExit) as cm:
                    build.ejecutar(args, Path("fake.xlsx"))
                self.assertEqual(cm.exception.code, 1)

            mock_aplicar.assert_not_called()
            self.assertFalse((tmp / "dist").exists())

    def test_4_ejecucion_normal_estricta_sin_url_falla(self):
        """Ejecución normal (sin --dry-run) con --disponibilidad-estricta:
        misma exigencia de URL, y falla ANTES de escribir cualquier
        archivo."""
        data = _data_sin_url()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            menu_json = tmp / "data" / "menu.json"
            menu_json.parent.mkdir(parents=True)
            menu_json.write_text("CONTENIDO_ANTERIOR_INTACTO", encoding="utf-8")
            dist_dir = tmp / "dist"
            args = _ArgsFake(dry_run=False, disponibilidad_estricta=True,
                              template=tmp / "no-se-lee.html", out=dist_dir / "index.html")

            with patch.object(build, "MENU_JSON", menu_json), \
                 patch.object(build.extract, "extract", return_value=data), \
                 patch.object(build.validate, "validate", return_value=([], [])), \
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods") as mock_aplicar, \
                 patch.object(build.render, "render") as mock_render, \
                 patch.object(build.render, "copiar_assets") as mock_copiar, \
                 patch.object(build.render, "_escribir_seo_estatico") as mock_seo:
                with self.assertRaises(SystemExit) as cm:
                    build.ejecutar(args, Path("fake.xlsx"))
                self.assertEqual(cm.exception.code, 1)

            mock_aplicar.assert_not_called()
            self.assertEqual(menu_json.read_text(encoding="utf-8"), "CONTENIDO_ANTERIOR_INTACTO")
            self.assertFalse(dist_dir.exists())
            mock_render.assert_not_called()
            mock_copiar.assert_not_called()
            mock_seo.assert_not_called()

    def test_5a_normal_no_estricta_con_url_aplica_no_estricto(self):
        """Ejecución normal sin --disponibilidad-estricta: comportamiento
        de siempre -- si hay URL, se aplica en modo NO estricto."""
        data = _data_fake()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            menu_json = tmp / "data" / "menu.json"
            dist_dir = tmp / "dist"
            template_path = tmp / "template.html"
            template_path.write_text("PLANTILLA", encoding="utf-8")
            args = _ArgsFake(dry_run=False, disponibilidad_estricta=False,
                              template=template_path, out=dist_dir / "index.html")

            with patch.object(build, "MENU_JSON", menu_json), \
                 patch.object(build.extract, "extract", return_value=data), \
                 patch.object(build.validate, "validate", return_value=([], [])), \
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods", return_value=-1) as mock_aplicar, \
                 patch.object(build.render, "render", return_value="<html>fake</html>"), \
                 patch.object(build.render, "copiar_assets"), \
                 patch.object(build.render, "_escribir_seo_estatico"):
                build.ejecutar(args, Path("fake.xlsx"))

            mock_aplicar.assert_called_once()
            _, kwargs = mock_aplicar.call_args
            self.assertFalse(kwargs.get("estricto", mock_aplicar.call_args[0][-1]))
            self.assertTrue(menu_json.exists())

    def test_5b_normal_no_estricta_sin_url_sigue_sin_aplicarla(self):
        """Ejecución normal sin --disponibilidad-estricta y sin URL: sigue
        el comportamiento de siempre -- continúa sin aplicar nada, nunca
        llama a aplicar_a_prods, y el build igual termina bien."""
        data = _data_sin_url()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            menu_json = tmp / "data" / "menu.json"
            dist_dir = tmp / "dist"
            template_path = tmp / "template.html"
            template_path.write_text("PLANTILLA", encoding="utf-8")
            args = _ArgsFake(dry_run=False, disponibilidad_estricta=False,
                              template=template_path, out=dist_dir / "index.html")

            with patch.object(build, "MENU_JSON", menu_json), \
                 patch.object(build.extract, "extract", return_value=data), \
                 patch.object(build.validate, "validate", return_value=([], [])), \
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods") as mock_aplicar, \
                 patch.object(build.render, "render", return_value="<html>fake</html>"), \
                 patch.object(build.render, "copiar_assets"), \
                 patch.object(build.render, "_escribir_seo_estatico"):
                build.ejecutar(args, Path("fake.xlsx"))

            mock_aplicar.assert_not_called()
            self.assertTrue(menu_json.exists())


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


class TestValidacionDocumentoPublicoEnMemoria(unittest.TestCase):
    """extract.datos_publicos(data) se valida de verdad con
    validate_json_publico.validate_menu_json ANTES de escribir nada --
    esa función NUNCA se mockea acá, justamente para probar que build.py
    realmente la invoca (no alcanza con que el validador "de Excel",
    mockeado, diga que todo está bien)."""

    def test_modelo_extraido_pasa_excel_pero_documento_publico_es_invalido(self):
        data = _data_fake()
        # Corrompemos justo lo que ve validate_json_publico (falta un
        # idioma obligatorio) -- validate.validate (el "de Excel") sigue
        # mockeado a "sin errores", así que si el build se detiene acá es
        # porque el control independiente del JSON público realmente
        # corrió y lo encontró.
        del data["cats"][0]["nom"]["it"]

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            menu_json = tmp / "data" / "menu.json"
            menu_json.parent.mkdir(parents=True)
            menu_json.write_text("CONTENIDO_ANTERIOR_INTACTO", encoding="utf-8")
            dist_dir = tmp / "dist"
            args = _ArgsFake(dry_run=False, disponibilidad_estricta=False,
                              template=tmp / "no-se-lee.html", out=dist_dir / "index.html")

            with patch.object(build, "MENU_JSON", menu_json), \
                 patch.object(build.extract, "extract", return_value=data), \
                 patch.object(build.validate, "validate", return_value=([], [])), \
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods") as mock_aplicar, \
                 patch.object(build.render, "render") as mock_render, \
                 patch.object(build.render, "copiar_assets") as mock_copiar, \
                 patch.object(build.render, "_escribir_seo_estatico") as mock_seo:
                with self.assertRaises(SystemExit) as cm:
                    build.ejecutar(args, Path("fake.xlsx"))
                self.assertEqual(cm.exception.code, 1)

            self.assertEqual(menu_json.read_text(encoding="utf-8"), "CONTENIDO_ANTERIOR_INTACTO")
            self.assertFalse(dist_dir.exists())
            mock_render.assert_not_called()
            mock_copiar.assert_not_called()
            mock_seo.assert_not_called()
            # la validación del documento público corre ANTES que
            # disponibilidad -- ni siquiera llega a intentarla.
            mock_aplicar.assert_not_called()

    def test_documento_publico_valido_no_detiene_el_build(self):
        """Contraprueba: con un documento realmente válido, el build sigue
        de largo (no es que cualquier cosa lo detenga)."""
        data = _data_fake()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            menu_json = tmp / "data" / "menu.json"
            dist_dir = tmp / "dist"
            template_path = tmp / "template.html"
            template_path.write_text("PLANTILLA", encoding="utf-8")
            args = _ArgsFake(dry_run=False, disponibilidad_estricta=False,
                              template=template_path, out=dist_dir / "index.html")

            with patch.object(build, "MENU_JSON", menu_json), \
                 patch.object(build.extract, "extract", return_value=data), \
                 patch.object(build.validate, "validate", return_value=([], [])), \
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods", return_value=-1), \
                 patch.object(build.render, "render", return_value="<html>fake</html>"), \
                 patch.object(build.render, "copiar_assets"), \
                 patch.object(build.render, "_escribir_seo_estatico"):
                build.ejecutar(args, Path("fake.xlsx"))

            self.assertTrue(menu_json.exists())


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
            # memoria (para que el render la vea), pero build.py ya validó
            # y serializó el texto de data/menu.json ANTES de esta llamada.
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
