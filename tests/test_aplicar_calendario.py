"""Pruebas de build/aplicar_calendario.py (calendario de temas desde Google
Sheets): lectura de la pestaña, validación estricta con número de fila,
descarga restringida a Google, y -- lo más importante -- que un calendario
roto NUNCA pise el último válido ni frene la publicación. Sin red: la
descarga se reemplaza por texto. Solo biblioteca estándar."""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
import aplicar_calendario as ac  # noqa: E402
import calendario  # noqa: E402

ENC = "id,tipo,tema,desde,hasta,prioridad,activo,nota"
FILA_OK = "encantada-2026,tema,encantada,2026-10-19,2026-11-02,10,Sí,Halloween y Muertos"


def _csv(*lineas):
    return "\n".join(lineas) + "\n"


class TestParsearCsv(unittest.TestCase):
    def test_fila_valida(self):
        doc, problemas = ac.parsear_csv(_csv(ENC, FILA_OK))
        self.assertEqual(problemas, [])
        self.assertEqual(doc["eventos"][0], {"id": "encantada-2026", "tipo": "tema", "tema": "encantada",
                                             "desde": "2026-10-19", "hasta": "2026-11-02", "prioridad": 10})
        self.assertEqual(calendario.validar(doc), [])
        self.assertTrue(doc["activo"])

    def test_el_resultado_pasa_la_misma_validacion_que_el_calendario_del_repo(self):
        doc, _ = ac.parsear_csv(_csv(ENC, FILA_OK))
        self.assertEqual(calendario.validar(doc), [])

    def test_columnas_en_otro_orden_y_sin_las_opcionales(self):
        doc, problemas = ac.parsear_csv(_csv("hasta,desde,tema,tipo", "2026-11-02,2026-10-19,encantada,tema"))
        self.assertEqual(problemas, [])
        self.assertEqual(doc["eventos"][0]["id"], "fila-2")  # sin id: se arma con el número de fila
        self.assertNotIn("prioridad", doc["eventos"][0])

    def test_encabezado_y_mayusculas_se_normalizan(self):
        doc, problemas = ac.parsear_csv(_csv("Tipo,Tema,Desde,Hasta", "Tema,Encantada,2026-10-19,2026-11-02"))
        self.assertEqual(problemas, [])
        self.assertEqual(doc["eventos"][0]["tema"], "encantada")

    def test_fila_con_activo_no_se_ignora(self):
        doc, problemas = ac.parsear_csv(_csv(ENC, FILA_OK, "otra,tema,encantada,2026-12-01,2026-12-05,,No,apagada"))
        self.assertEqual(problemas, [])
        self.assertEqual(len(doc["eventos"]), 1)

    def test_filas_en_blanco_se_saltean(self):
        doc, problemas = ac.parsear_csv(_csv(ENC, ",,,,,,,", FILA_OK, ",,,,,,,"))
        self.assertEqual(problemas, [])
        self.assertEqual(len(doc["eventos"]), 1)

    def test_hoja_sin_filas_de_datos_es_un_calendario_vacio_valido(self):
        doc, problemas = ac.parsear_csv(_csv(ENC))
        self.assertEqual(problemas, [])
        self.assertEqual(doc["eventos"], [])

    def test_hoja_vacia(self):
        _, problemas = ac.parsear_csv("")
        self.assertTrue(problemas)

    def test_encabezado_con_columna_desconocida_repetida_o_faltante(self):
        self.assertTrue(ac.parsear_csv(_csv("tipo,tema,desde,hasta,color", "tema,encantada,2026-10-19,2026-11-02,rojo"))[1])
        self.assertTrue(ac.parsear_csv(_csv("tipo,tema,desde,hasta,tema", "tema,encantada,2026-10-19,2026-11-02,x"))[1])
        self.assertTrue(ac.parsear_csv(_csv("tipo,tema,desde", "tema,encantada,2026-10-19"))[1])

    def test_errores_citan_el_numero_de_fila(self):
        _, problemas = ac.parsear_csv(_csv(ENC, FILA_OK, "x,tema,encantada,2026-13-40,2026-11-02,,,"))
        self.assertTrue(any(p.startswith("Fila 3:") for p in problemas), problemas)

    def test_valores_invalidos(self):
        casos = {
            "tema desconocido": "a,tema,halowen,2026-10-19,2026-11-02,,,",
            "tipo desconocido": "a,cierre,encantada,2026-10-19,2026-11-02,,,",
            "fecha en formato argentino": "a,tema,encantada,19/10/2026,02/11/2026,,,",
            "desde posterior a hasta": "a,tema,encantada,2026-11-03,2026-11-02,,,",
            "prioridad no numerica": "a,tema,encantada,2026-10-19,2026-11-02,alta,,",
            "prioridad fuera de rango": "a,tema,encantada,2026-10-19,2026-11-02,500,,",
            "activo desconocido": "a,tema,encantada,2026-10-19,2026-11-02,,quizas,",
            "id invalido": "Con Espacio,tema,encantada,2026-10-19,2026-11-02,,,",
        }
        for nombre, fila in casos.items():
            with self.subTest(nombre):
                doc, problemas = ac.parsear_csv(_csv(ENC, fila))
                self.assertIsNone(doc)
                self.assertTrue(problemas)

    def test_ids_repetidos_entre_filas(self):
        doc, problemas = ac.parsear_csv(_csv(ENC, FILA_OK, FILA_OK))
        self.assertIsNone(doc)
        self.assertTrue(problemas)

    def test_datos_fuera_de_las_columnas_del_encabezado(self):
        _, problemas = ac.parsear_csv(_csv(ENC, FILA_OK + ",sobra"))
        self.assertTrue(problemas)

    def test_los_mensajes_nunca_reproducen_el_texto_de_las_celdas(self):
        secreto = "SECRETO NO DEBE SALIR"
        casos = [
            _csv(ENC, f"a,tema,{secreto},2026-10-19,2026-11-02,,,"),
            _csv(ENC, f"a,{secreto},encantada,2026-10-19,2026-11-02,,,"),
            _csv(ENC, f"a,tema,encantada,{secreto},2026-11-02,,,"),
            _csv(ENC, f"a,tema,encantada,2026-10-19,2026-11-02,{secreto},,"),
            _csv(ENC, f"a,tema,encantada,2026-10-19,2026-11-02,,{secreto},"),
            _csv(ENC, f"{secreto},tema,encantada,2026-10-19,2026-11-02,,,"),
            _csv(f"tipo,tema,desde,hasta,{secreto}", "tema,encantada,2026-10-19,2026-11-02,x"),
        ]
        for contenido in casos:
            _, problemas = ac.parsear_csv(contenido)
            self.assertTrue(problemas)
            self.assertNotIn(secreto.lower(), " ".join(problemas).lower())
            self.assertNotIn(secreto, " ".join(problemas))

    def test_demasiadas_filas(self):
        filas = [ENC] + [f"e{i},tema,encantada,2026-10-19,2026-11-02,,," for i in range(ac.MAX_FILAS + 1)]
        doc, problemas = ac.parsear_csv(_csv(*filas))
        self.assertIsNone(doc)
        self.assertTrue(problemas)


class TestDescarga(unittest.TestCase):
    def test_solo_https_de_docs_google_com(self):
        for url in ("http://docs.google.com/spreadsheets/d/x/pub?output=csv",
                    "https://evil.example.com/x.csv",
                    "https://docs.google.com.evil.com/x.csv",
                    "file:///etc/passwd", ""):
            with self.subTest(url=url):
                with self.assertRaises(ac.CalendarioInvalido):
                    ac._descargar(url)

    def test_fallo_de_red_no_filtra_la_url(self):
        url = "https://docs.google.com/spreadsheets/d/CLAVE-SECRETA/pub?gid=1&output=csv"
        with patch("urllib.request.OpenerDirector.open", side_effect=OSError("fallo en " + url)):
            with self.assertRaises(ac.CalendarioInvalido) as cm:
                ac._descargar(url)
        self.assertNotIn("CLAVE-SECRETA", str(cm.exception))
        self.assertIn("OSError", str(cm.exception))

    def test_redireccion_a_un_host_no_permitido_se_corta(self):
        handler = ac._RedirectHandlerRestringido()
        with self.assertRaises(ac.CalendarioInvalido):
            handler.redirect_request(None, None, 307, "x", {}, "https://evil.example.com/robado")

    def test_redireccion_al_host_de_contenido_de_google_se_permite(self):
        permitido = ac.ec.url_https_valida("https://doc-00-2k-sheets.googleusercontent.com/pub/x", ac.ad.DOMINIOS_REDIRECCION_PERMITIDOS)
        self.assertTrue(permitido)


class TestAplicarAArchivo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / "calendario.json"
        self.original = '{"original": true}\n'
        self.ruta.write_text(self.original, encoding="utf-8")
        self.url = "https://docs.google.com/spreadsheets/d/x/pub?gid=1&output=csv"

    def test_calendario_valido_reescribe_el_archivo(self):
        with patch.object(ac, "_descargar", return_value=_csv(ENC, FILA_OK)):
            n = ac.aplicar_a_archivo(self.url, self.ruta)
        self.assertEqual(n, 1)
        doc = json.loads(self.ruta.read_text(encoding="utf-8"))
        self.assertEqual(calendario.validar(doc), [])
        self.assertEqual(calendario.cargar(self.ruta)["eventos"][0]["tema"], "encantada")
        self.assertFalse(self.ruta.with_suffix(".json.tmp").exists())

    def test_calendario_roto_no_toca_el_archivo(self):
        with patch.object(ac, "_descargar", return_value=_csv(ENC, "a,tema,halowen,2026-10-19,2026-11-02,,,")):
            with self.assertRaises(ac.CalendarioInvalido):
                ac.aplicar_a_archivo(self.url, self.ruta)
        self.assertEqual(self.ruta.read_text(encoding="utf-8"), self.original)
        self.assertFalse(self.ruta.with_suffix(".json.tmp").exists())

    def test_descarga_fallida_no_toca_el_archivo(self):
        with patch.object(ac, "_descargar", side_effect=ac.CalendarioInvalido("sin red")):
            with self.assertRaises(ac.CalendarioInvalido):
                ac.aplicar_a_archivo(self.url, self.ruta)
        self.assertEqual(self.ruta.read_text(encoding="utf-8"), self.original)


class TestMain(unittest.TestCase):
    def _correr(self, env, **parches):
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / "output"
            variables = dict(env, GITHUB_OUTPUT=str(salida))
            with patch.dict(os.environ, variables, clear=False):
                for clave in ("CALENDARIO_CSV_URL",):
                    if clave not in env:
                        os.environ.pop(clave, None)
                codigo = ac.main()
            texto = salida.read_text(encoding="utf-8") if salida.exists() else ""
        return codigo, texto

    def test_sin_url_no_es_error_y_usa_el_calendario_del_repo(self):
        codigo, salida = self._correr({})
        self.assertEqual(codigo, 0)
        self.assertIn("calendario_ok=true", salida)

    def test_con_hoja_valida(self):
        with patch.object(ac, "aplicar_a_archivo", return_value=3):
            codigo, salida = self._correr({"CALENDARIO_CSV_URL": "https://docs.google.com/x"})
        self.assertEqual(codigo, 0)
        self.assertIn("calendario_ok=true", salida)

    def test_hoja_con_errores_no_frena_el_build_pero_lo_marca(self):
        with patch.object(ac, "aplicar_a_archivo", side_effect=ac.CalendarioInvalido("roto")):
            codigo, salida = self._correr({"CALENDARIO_CSV_URL": "https://docs.google.com/x"})
        self.assertEqual(codigo, 0, "un calendario roto no puede frenar la publicación del menú")
        self.assertIn("calendario_ok=false", salida)

    def test_un_bug_inesperado_tampoco_frena_el_build(self):
        with patch.object(ac, "aplicar_a_archivo", side_effect=RuntimeError("bug")):
            codigo, salida = self._correr({"CALENDARIO_CSV_URL": "https://docs.google.com/x"})
        self.assertEqual(codigo, 0)
        self.assertIn("calendario_ok=false", salida)


class TestPlantillaCsv(unittest.TestCase):
    def test_la_plantilla_de_la_guia_es_valida(self):
        """La plantilla vive dentro de docs/operations/CALENDARIO_SHEETS.md (los
        *.csv están en .gitignore a propósito, así que no puede ser un archivo)."""
        guia = (Path(__file__).resolve().parent.parent / "docs" / "operations" / "CALENDARIO_SHEETS.md").read_text(encoding="utf-8")
        bloque = re.search(r"```csv\r?\n(.*?)```", guia, re.S)
        self.assertIsNotNone(bloque, "falta el bloque ```csv en la guía")
        contenido = "\n".join(linea.strip() for linea in bloque.group(1).splitlines())
        doc, problemas = ac.parsear_csv(contenido)
        self.assertEqual(problemas, [])
        self.assertEqual(calendario.validar(doc), [])
        self.assertEqual(len(doc["eventos"]), 1)


if __name__ == "__main__":
    unittest.main()
