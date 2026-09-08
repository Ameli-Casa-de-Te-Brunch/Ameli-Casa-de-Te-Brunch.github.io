"""Pruebas de build.py (el orquestador local extract -> validate -> render):

- que "import build" nunca requiera openpyxl (extract.py y validate.py,
  los dos únicos módulos de build/ que lo necesitan, se cargan recién al
  ejecutar de verdad el flujo que abre el Excel -- nunca al importar este
  módulo). Se prueba de forma directa corriendo Python con -S (que excluye
  site-packages, incluido cualquier paquete de terceros instalado) tanto
  para "import build" como para la suite completa;
- que los 4 modos de disponibilidad se comporten exactamente como deben:
  "--dry-run" plano nunca consulta la hoja ni llama a aplicar_a_prods;
  "--dry-run --disponibilidad-estricta" sí la consulta, en modo estricto,
  y exige URL; la ejecución normal sin --disponibilidad-estricta conserva
  el comportamiento de siempre; la ejecución normal con
  --disponibilidad-estricta exige URL igual que el dry-run estricto;
- que el documento público (extract_common.datos_publicos(data)) se
  valide de verdad con validate_json_publico.validate_menu_json ANTES de
  escribir nada -- sin mockear esa validación, para probar que realmente
  se invoca;
- que cualquiera de esos fallos (openpyxl ausente, disponibilidad, o JSON
  público) deje data/menu.json, dist/index.html y todo lo demás
  exactamente igual que antes de correr build.py;
- que una corrida exitosa sí escriba los outputs, y que data/menu.json
  persistido nunca incorpore la disponibilidad efímera aplicada en
  memoria para el render.

extract.py y validate.py (los módulos reales que sí requieren openpyxl)
NUNCA se importan ni se simulan acá -- build.ejecutar() recibe
directamente dobles explícitos (extract_mod/validate_mod, objetos
simples con un método .extract()/.validate()) inyectados por cada test.
Ningún test instala un MagicMock global de 'openpyxl' en sys.modules --
eso podría ocultar un uso real accidental de esa dependencia en vez de
probarlo. validate_json_publico.validate_menu_json NUNCA se mockea --
correr de verdad es justamente lo que estas pruebas necesitan demostrar.
Nunca se usa un Excel real ni se hace una descarga real."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "build"))
import build  # noqa: E402
import aplicar_disponibilidad as ad  # noqa: E402


def _data_fake():
    """Documento COMPLETO y válido -- con la validación real de
    validate_json_publico corriendo de verdad adentro de build.py, tiene
    que pasarla sin errores para que estas pruebas puedan llegar a
    ejercitar disponibilidad y escritura de archivos. Misma forma que
    _doc_valido() en tests/test_validate_json_publico.py."""
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


class _ExtractModFake:
    """Doble explícito de extract.py -- nunca el módulo real (que
    requiere openpyxl), nunca un mock de sys.modules['openpyxl']."""

    def __init__(self, data):
        self._data = data
        self.llamadas = []

    def extract(self, xlsx_path):
        self.llamadas.append(xlsx_path)
        return self._data


class _ValidateModFake:
    """Doble explícito de validate.py (el validador "de Excel") -- nunca
    el módulo real."""

    def __init__(self, errors=(), warnings=()):
        self._errors = list(errors)
        self._warnings = list(warnings)
        self.llamadas = []

    def validate(self, data, xlsx_path):
        self.llamadas.append((data, xlsx_path))
        return self._errors, self._warnings


class _ArgsFake:
    def __init__(self, dry_run, disponibilidad_estricta, template, out, publicar=False):
        self.dry_run = dry_run
        self.disponibilidad_estricta = disponibilidad_estricta
        self.publicar = publicar
        self.template = template
        self.out = out


class TestImportYEjecucionSinOpenpyxl(unittest.TestCase):
    """Pruebas "de verdad" (subprocesos con -S, que excluye site-packages
    -- incluido cualquier openpyxl instalado) de que build.py nunca
    necesita esa dependencia salvo para el flujo real que abre el Excel."""

    def test_import_build_no_requiere_openpyxl(self):
        resultado = subprocess.run(
            [sys.executable, "-S", "-c", "import build"],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
        self.assertNotIn("ModuleNotFoundError", resultado.stderr)
        self.assertNotIn("Traceback", resultado.stdout + resultado.stderr)

    def test_suite_completa_corre_sin_site_packages(self):
        """La suite entera, corrida como subproceso con -S -- exactamente
        lo mismo que corre test-rama.yml en CI (sin pip install, solo
        stdlib).

        Guarda anti-recursión: este mismo test forma parte de la suite
        que el subproceso vuelve a descubrir, así que sin la variable de
        entorno de más abajo se dispararía a sí mismo de nuevo (y ese hijo
        a otro, sin fin). El hijo la ve seteada y se salta a sí mismo con
        skipTest -- un solo nivel de anidamiento, nunca más."""
        if os.environ.get("_AMELI_TEST_BUILD_SIN_RECURSION"):
            self.skipTest("evita recursión infinita: esta corrida ya es un subproceso anidado")
        env = dict(os.environ, _AMELI_TEST_BUILD_SIN_RECURSION="1")
        resultado = subprocess.run(
            [sys.executable, "-S", "-m", "unittest", "discover", "-s", "tests"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=60, env=env,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stdout[-3000:] + resultado.stderr[-3000:])

    def test_build_local_sin_openpyxl_muestra_mensaje_controlado_sin_traceback(self):
        """Reproduce el escenario real: alguien corre build.py de verdad
        (no los tests) en un entorno sin openpyxl instalado. Usa un
        archivo --xlsx cualquiera (nunca se llega a abrir, el build falla
        antes) para no depender de que exista un Excel real en esta PC."""
        with tempfile.TemporaryDirectory() as tmp:
            dummy_xlsx = Path(tmp) / "fake.xlsx"
            dummy_xlsx.write_bytes(b"contenido irrelevante -- nunca se llega a abrir")
            resultado = subprocess.run(
                [sys.executable, "-S", "build.py", "--dry-run", "--xlsx", str(dummy_xlsx)],
                cwd=str(ROOT), capture_output=True, text=True,
            )

        combinado = resultado.stdout + resultado.stderr
        self.assertNotEqual(resultado.returncode, 0)
        self.assertIn("pip install -r requirements.txt", combinado)
        self.assertNotIn("Traceback", combinado)
        # Falla ANTES de imprimir "1/3 extract" -- ni siquiera empezó a
        # intentar nada, así que no hay ningún output que pudiera haberse
        # tocado.
        self.assertNotIn("1/3 extract", combinado)

    def test_cargador_diferido_no_se_invoca_si_las_dependencias_estan_inyectadas(self):
        """Cuando ejecutar() recibe extract_mod/validate_mod explícitos
        (como hacen TODOS los demás tests de esta clase), nunca llama al
        cargador que importaría extract.py/validate.py (y por lo tanto
        openpyxl) -- ni siquiera para descartarlo."""
        data = _data_fake()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            args = _ArgsFake(dry_run=True, disponibilidad_estricta=False,
                              template=tmp / "no-se-lee.html", out=tmp / "dist" / "index.html")
            with patch.object(build, "_cargar_dependencias_xlsx") as mock_cargador:
                build.ejecutar(args, Path("fake.xlsx"),
                                extract_mod=_ExtractModFake(data), validate_mod=_ValidateModFake())
            mock_cargador.assert_not_called()


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
            with patch.object(build.aplicar_disponibilidad, "aplicar_a_prods") as mock_aplicar:
                build.ejecutar(args, Path("fake.xlsx"),
                                extract_mod=_ExtractModFake(data), validate_mod=_ValidateModFake())

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
            with patch.object(build.aplicar_disponibilidad, "aplicar_a_prods", return_value=0) as mock_aplicar:
                build.ejecutar(args, Path("fake.xlsx"),
                                extract_mod=_ExtractModFake(data), validate_mod=_ValidateModFake())

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
            with patch.object(build.aplicar_disponibilidad, "aplicar_a_prods") as mock_aplicar:
                with self.assertRaises(SystemExit) as cm:
                    build.ejecutar(args, Path("fake.xlsx"),
                                    extract_mod=_ExtractModFake(data), validate_mod=_ValidateModFake())
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
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods") as mock_aplicar, \
                 patch.object(build.render, "render") as mock_render, \
                 patch.object(build.render, "copiar_assets") as mock_copiar, \
                 patch.object(build.render, "_escribir_seo_estatico") as mock_seo:
                with self.assertRaises(SystemExit) as cm:
                    build.ejecutar(args, Path("fake.xlsx"),
                                    extract_mod=_ExtractModFake(data), validate_mod=_ValidateModFake())
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
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods", return_value=-1) as mock_aplicar, \
                 patch.object(build.render, "render", return_value="<html>fake</html>"), \
                 patch.object(build.render, "copiar_assets"), \
                 patch.object(build.render, "_escribir_seo_estatico"):
                build.ejecutar(args, Path("fake.xlsx"),
                                extract_mod=_ExtractModFake(data), validate_mod=_ValidateModFake())

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
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods") as mock_aplicar, \
                 patch.object(build.render, "render", return_value="<html>fake</html>"), \
                 patch.object(build.render, "copiar_assets"), \
                 patch.object(build.render, "_escribir_seo_estatico"):
                build.ejecutar(args, Path("fake.xlsx"),
                                extract_mod=_ExtractModFake(data), validate_mod=_ValidateModFake())

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
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods",
                               side_effect=ad.DisponibilidadInvalida("simulado: hoja no confiable")), \
                 patch.object(build.render, "render") as mock_render, \
                 patch.object(build.render, "copiar_assets") as mock_copiar, \
                 patch.object(build.render, "_escribir_seo_estatico") as mock_seo:
                with self.assertRaises(SystemExit) as cm:
                    build.ejecutar(args, Path("fake.xlsx"),
                                    extract_mod=_ExtractModFake(data), validate_mod=_ValidateModFake())
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
    """extract_common.datos_publicos(data) se valida de verdad con
    validate_json_publico.validate_menu_json ANTES de escribir nada --
    esa función NUNCA se mockea acá, justamente para probar que build.py
    realmente la invoca (no alcanza con que el validador "de Excel",
    reemplazado por un doble simple, diga que todo está bien)."""

    def test_modelo_extraido_pasa_excel_pero_documento_publico_es_invalido(self):
        data = _data_fake()
        # Corrompemos justo lo que ve validate_json_publico (falta un
        # idioma obligatorio) -- el doble de validate.py sigue diciendo
        # "sin errores", así que si el build se detiene acá es porque el
        # control independiente del JSON público realmente corrió y lo
        # encontró.
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
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods") as mock_aplicar, \
                 patch.object(build.render, "render") as mock_render, \
                 patch.object(build.render, "copiar_assets") as mock_copiar, \
                 patch.object(build.render, "_escribir_seo_estatico") as mock_seo:
                with self.assertRaises(SystemExit) as cm:
                    build.ejecutar(args, Path("fake.xlsx"),
                                    extract_mod=_ExtractModFake(data), validate_mod=_ValidateModFake())
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
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods", return_value=-1), \
                 patch.object(build.render, "render", return_value="<html>fake</html>"), \
                 patch.object(build.render, "copiar_assets"), \
                 patch.object(build.render, "_escribir_seo_estatico"):
                build.ejecutar(args, Path("fake.xlsx"),
                                extract_mod=_ExtractModFake(data), validate_mod=_ValidateModFake())

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
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods", return_value=0), \
                 patch.object(build.render, "render", return_value="<html>fake</html>") as mock_render, \
                 patch.object(build.render, "copiar_assets") as mock_copiar, \
                 patch.object(build.render, "_escribir_seo_estatico") as mock_seo:
                build.ejecutar(args, Path("fake.xlsx"),
                                extract_mod=_ExtractModFake(data), validate_mod=_ValidateModFake())

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
                 patch.object(build.aplicar_disponibilidad, "aplicar_a_prods", side_effect=_mutar_en_memoria), \
                 patch.object(build.render, "render", side_effect=_render_falso), \
                 patch.object(build.render, "copiar_assets"), \
                 patch.object(build.render, "_escribir_seo_estatico"):
                build.ejecutar(args, Path("fake.xlsx"),
                                extract_mod=_ExtractModFake(data), validate_mod=_ValidateModFake())

            # El render sí vio la disponibilidad efímera aplicada en memoria...
            self.assertEqual(render_calls, ["agotado"])
            # ...pero el data/menu.json escrito a disco (lo versionado) no la
            # incorpora: sigue reflejando el Excel, disponible por defecto.
            publicado = json.loads(menu_json.read_text(encoding="utf-8"))
            self.assertNotIn("disp", publicado["prods"][0])


if __name__ == "__main__":
    unittest.main()
