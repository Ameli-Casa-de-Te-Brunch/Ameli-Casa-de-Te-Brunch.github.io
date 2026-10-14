"""Pruebas de build/aplicar_precios.py (precios desde una pestaña de Google
Sheets) y build/hoja_publica.py (descarga restringida a Google).

Lo más importante: la plantilla armada desde data/menu.json, leída de vuelta,
reproduce EXACTAMENTE los precios publicados (el cálculo es el mismo que el del
Excel), y cualquier dato dudoso -- un cero de más, un producto ausente, un
tamaño agregado -- frena todo sin tocar nada. Sin red: la descarga se
reemplaza por texto. Solo biblioteca estándar."""
import copy
import csv
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))
import aplicar_precios as ap  # noqa: E402
import hoja_publica  # noqa: E402
import validate_json_publico as vjp  # noqa: E402

MENU_REAL = ROOT / "data" / "menu.json"
TASAS = (1485, 1715, 289)
URL = "https://docs.google.com/spreadsheets/d/x/pub?gid=1&output=csv"


def _data():
    return json.loads(MENU_REAL.read_text(encoding="utf-8"))


def _hoja(cambios=None, quitar=(), agregar=(), tasas=TASAS, columnas=None):
    """CSV de la hoja = plantilla real + modificaciones. cambios: {id: (chico, grande)}
    con textos tal cual se escribirían en la celda."""
    filas = list(csv.reader(io.StringIO(ap.plantilla_csv(_data(), *tasas))))
    enc = filas[0]
    salida = [enc]
    for f in filas[1:]:
        if f[0] in quitar:
            continue
        if cambios and f[0] in cambios:
            f = list(f)
            f[enc.index("precio_chico")], f[enc.index("precio_grande")] = cambios[f[0]]
        salida.append(f)
    salida.extend(agregar)
    if columnas is not None:
        salida = [[f[enc.index(c)] if c in enc else "" for c in columnas] for f in salida]
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(salida)
    return out.getvalue()


def _parsear(contenido):
    return ap.parsear_csv(contenido, _data())


class TestIdaYVuelta(unittest.TestCase):
    def test_la_plantilla_leida_de_vuelta_reproduce_exactamente_los_precios_publicados(self):
        data = _data()
        tasas, precios, problemas = ap.parsear_csv(ap.plantilla_csv(data, *TASAS), data)
        self.assertEqual(problemas, [])
        self.assertEqual(tasas, {"usd": 1485, "eur": 1715, "brl": 289})
        self.assertEqual(ap.nuevos_precios(data, tasas, precios), data["precios"])

    def test_la_plantilla_cubre_todos_los_productos_con_precio(self):
        data = _data()
        filas = list(csv.DictReader(io.StringIO(ap.plantilla_csv(data, *TASAS))))
        ids = {f["id"] for f in filas}
        self.assertEqual(ids - {"TASA_USD", "TASA_EUR", "TASA_BRL"}, set(data["precios"]))

    def test_las_tasas_de_hoy_siguen_siendo_las_del_json_publicado(self):
        """Si alguien cambia los equivalentes en el Excel y no acá, este test
        avisa (1485/1715/289 son los valores con los que se armó el JSON)."""
        data = _data()
        self.assertEqual(data["precios"]["DYM001"]["usd"], "≈ USD 11")


class TestAplicacion(unittest.TestCase):
    def test_cambio_de_un_precio_unico_recalcula_ars_y_equivalentes(self):
        data = _data()
        tasas, precios, p = ap.parsear_csv(_hoja({"DYM001": ("18.000", "")}), data)
        self.assertEqual(p, [])
        nuevos = ap.nuevos_precios(data, tasas, precios)
        self.assertEqual(nuevos["DYM001"]["ars"], "$ 18.000")
        self.assertEqual(nuevos["DYM001"]["usd"], "≈ USD 12")
        self.assertNotIn("niveles", nuevos["DYM001"])
        otros = {k: v for k, v in nuevos.items() if k != "DYM001"}
        self.assertEqual(otros, {k: v for k, v in data["precios"].items() if k != "DYM001"})

    def test_cambio_de_dos_tamanos(self):
        data = _data()
        tasas, precios, p = ap.parsear_csv(_hoja({"BLE001": ("$ 5.000", "6000")}), data)
        self.assertEqual(p, [])
        e = ap.nuevos_precios(data, tasas, precios)["BLE001"]
        self.assertEqual(e["ars"], "Chico $ 5.000 · Grande $ 6.000")
        self.assertEqual([n["ars"] for n in e["niveles"]], ["$ 5.000", "$ 6.000"])
        self.assertIn("usd", e["niveles"][0])
        self.assertNotIn("usd", e["niveles"][1])  # el equivalente va solo en el primer nivel

    def test_vaso_y_jarra_conservan_sus_etiquetas(self):
        data = _data()
        tasas, precios, p = ap.parsear_csv(_hoja({"BYJ002": ("7800", "16500")}), data)
        self.assertEqual(p, [])
        e = ap.nuevos_precios(data, tasas, precios)["BYJ002"]
        self.assertEqual([n["etiqueta"] for n in e["niveles"]], ["Vaso", "Jarra"])

    def test_cambiar_la_tasa_recalcula_los_equivalentes(self):
        data = _data()
        tasas, precios, p = ap.parsear_csv(_hoja(tasas=(1700, 1715, 289)), data)
        self.assertEqual(p, [])
        nuevos = ap.nuevos_precios(data, tasas, precios)
        self.assertEqual(nuevos["DYM001"]["usd"], "≈ USD 10")  # 17000 / 1700
        self.assertEqual(nuevos["DYM001"]["eur"], data["precios"]["DYM001"]["eur"])

    def test_tasa_con_coma_decimal_y_miles(self):
        data = _data()
        _, _, p = ap.parsear_csv(_hoja(tasas=("1.485,50", "1715", "289,5")), data)
        self.assertEqual(p, [])

    def test_el_resultado_pasa_el_validador_del_json_publico(self):
        data = _data()
        tasas, precios, _ = ap.parsear_csv(_hoja({"DYM001": ("18000", ""), "BLE001": ("5000", "6000")}), data)
        data["precios"] = ap.nuevos_precios(data, tasas, precios)
        errores, _ = vjp.validate_menu_json(data)
        self.assertEqual(errores, [])


class TestNumeros(unittest.TestCase):
    def test_pesos_validos(self):
        for texto, esperado in (("4800", 4800), ("4.800", 4800), ("$ 4.800", 4800), ("$4800", 4800),
                                (" 17.000 ", 17000), ("", None)):
            with self.subTest(texto=texto):
                self.assertEqual(ap.parsear_pesos(texto), esperado)

    def test_pesos_invalidos(self):
        for texto in ("4,8", "4800.50", "4.80", "abc", "-500", "4 800 pesos", "4.8000", "1e3"):
            with self.subTest(texto=texto):
                self.assertIs(ap.parsear_pesos(texto), False)


class TestGuardas(unittest.TestCase):
    def _problemas(self, contenido):
        return ap.parsear_csv(contenido, _data())[2]

    def test_un_cero_de_mas_o_de_menos_se_frena(self):
        self.assertTrue(self._problemas(_hoja({"DYM001": ("170000", "")})))
        self.assertTrue(self._problemas(_hoja({"DYM001": ("1700", "")})))

    def test_un_ajuste_razonable_pasa(self):
        self.assertEqual(self._problemas(_hoja({"DYM001": ("20000", "")})), [])  # +17 %

    def test_fuera_de_rango(self):
        self.assertTrue(self._problemas(_hoja({"DYM001": ("300", "")})))
        self.assertTrue(self._problemas(_hoja({"DYM001": ("250000", "")})))

    def test_agregar_o_quitar_un_tamano_no_se_puede_desde_la_hoja(self):
        self.assertTrue(self._problemas(_hoja({"DYM001": ("17000", "20000")})))  # único -> dos
        self.assertTrue(self._problemas(_hoja({"BLE001": ("4800", "")})))        # dos -> único

    def test_grande_menor_que_chico(self):
        self.assertTrue(self._problemas(_hoja({"BLE001": ("5600", "4800")})))

    def test_producto_ausente_o_desconocido_o_repetido(self):
        self.assertTrue(self._problemas(_hoja(quitar=("DYM001",))))
        self.assertTrue(self._problemas(_hoja(agregar=[["ZZZ999", "x", "", "5000", "", ""]])))
        self.assertTrue(self._problemas(_hoja(agregar=[["DYM001", "x", "", "17000", "", ""]])))
        self.assertTrue(self._problemas(_hoja(agregar=[["", "sin id", "", "5000", "", ""]])))

    def test_tasas_faltantes_repetidas_o_fuera_de_rango(self):
        self.assertTrue(self._problemas(_hoja(quitar=("TASA_USD",))))
        self.assertTrue(self._problemas(_hoja(agregar=[["TASA_USD", "x", "", "1500", "", ""]])))
        self.assertTrue(self._problemas(_hoja(tasas=(5, 1715, 289))))
        self.assertTrue(self._problemas(_hoja(tasas=(1485, "mucho", 289))))

    def test_valores_no_numericos(self):
        self.assertTrue(self._problemas(_hoja({"DYM001": ("gratis", "")})))
        self.assertTrue(self._problemas(_hoja({"BLE001": ("4800", "5,5")})))
        self.assertTrue(self._problemas(_hoja({"DYM001": ("", "")})))

    def test_encabezados(self):
        self.assertTrue(ap.parsear_csv("", _data())[2])
        self.assertTrue(self._problemas("id,precio_chico\nDYM001,17000\n"))                 # falta precio_grande
        self.assertTrue(self._problemas("id,precio_chico,precio_grande,color\nDYM001,1,,x\n"))
        self.assertTrue(self._problemas("id,id,precio_chico,precio_grande\nDYM001,x,1,\n"))

    def test_los_errores_citan_la_fila_y_nunca_el_texto_de_la_celda(self):
        secreto = "TEXTO-SECRETO-123"
        for contenido in (_hoja({"DYM001": (secreto, "")}),
                          _hoja({"DYM001": ("17000", secreto)}),
                          _hoja(agregar=[[secreto, "x", "", "5000", "", ""]]),
                          _hoja(tasas=(secreto, 1715, 289))):
            problemas = self._problemas(contenido)
            self.assertTrue(problemas)
            self.assertNotIn(secreto, " ".join(problemas))
            self.assertTrue(any(p.startswith("Fila ") for p in problemas), problemas)

    def test_nombre_categoria_y_nota_nunca_se_leen(self):
        filas = list(csv.reader(io.StringIO(_hoja())))
        for f in filas[1:]:
            f[1] = "<script>alert(1)</script>"
            f[2] = "cualquier cosa"
            f[5] = "nota libre"
        out = io.StringIO()
        csv.writer(out, lineterminator="\n").writerows(filas)
        self.assertEqual(ap.parsear_csv(out.getvalue(), _data())[2], [])

    def test_columnas_en_otro_orden_y_sin_las_informativas(self):
        contenido = _hoja({"DYM001": ("18000", "")}, columnas=["precio_grande", "precio_chico", "id"])
        tasas, precios, p = ap.parsear_csv(contenido, _data())
        self.assertEqual(p, [])
        self.assertEqual(precios["DYM001"], (18000, None))


class TestArchivoYMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / "menu.json"
        shutil.copy(MENU_REAL, self.ruta)
        self.original = self.ruta.read_bytes()

    def test_hoja_con_cambios_reescribe_solo_lo_que_cambio(self):
        with patch.object(ap, "_descargar", return_value=_hoja({"DYM001": ("18000", "")})):
            n, omitidos = ap.aplicar_a_archivo(URL, self.ruta)
        self.assertEqual((n, omitidos), (1, []))
        nuevo = json.loads(self.ruta.read_text(encoding="utf-8"))
        original = json.loads(self.original.decode("utf-8"))
        self.assertEqual(nuevo["precios"]["DYM001"]["ars"], "$ 18.000")
        for clave in ("cats", "prods", "config"):
            self.assertEqual(nuevo[clave], original[clave])
        self.assertFalse(self.ruta.with_suffix(".json.tmp").exists())

    def test_hoja_igual_al_json_no_reescribe_el_archivo(self):
        with patch.object(ap, "_descargar", return_value=_hoja()):
            self.assertEqual(ap.aplicar_a_archivo(URL, self.ruta), (0, []))
        self.assertEqual(self.ruta.read_bytes(), self.original)

    def test_hoja_con_un_error_de_estructura_no_toca_nada(self):
        with patch.object(ap, "_descargar", return_value=_hoja({"DYM001": ("18000", "")}, quitar=("TASA_USD",))):
            with self.assertRaises(ap.PreciosInvalidos):
                ap.aplicar_a_archivo(URL, self.ruta)
        self.assertEqual(self.ruta.read_bytes(), self.original)

    def test_una_tasa_mala_frena_todo_aunque_haya_cambios_validos(self):
        with patch.object(ap, "_descargar", return_value=_hoja({"DYM001": ("18000", "")}, tasas=(5, 1715, 289))):
            with self.assertRaises(ap.PreciosInvalidos):
                ap.aplicar_a_archivo(URL, self.ruta)
        self.assertEqual(self.ruta.read_bytes(), self.original)

    def test_una_fila_mala_no_frena_a_las_demas(self):
        # DYM001 con un cero de mas (se omite) y BLE001 con un ajuste razonable (se aplica)
        hoja = _hoja({"DYM001": ("170000", ""), "BLE001": ("5000", "6000")})
        with patch.object(ap, "_descargar", return_value=hoja):
            n, omitidos = ap.aplicar_a_archivo(URL, self.ruta)
        self.assertEqual(n, 1)
        self.assertEqual(len(omitidos), 1)
        self.assertIn("'DYM001'", omitidos[0])
        nuevo = json.loads(self.ruta.read_text(encoding="utf-8"))
        original = json.loads(self.original.decode("utf-8"))
        self.assertEqual(nuevo["precios"]["DYM001"], original["precios"]["DYM001"])  # conserva su precio
        self.assertNotEqual(nuevo["precios"]["BLE001"], original["precios"]["BLE001"])  # el otro si cambio

    def test_todas_las_filas_malas_no_cambian_nada_y_no_levantan(self):
        with patch.object(ap, "_descargar", return_value=_hoja({"DYM001": ("170000", "")})):
            n, omitidos = ap.aplicar_a_archivo(URL, self.ruta)
        self.assertEqual((n, len(omitidos)), (0, 1))
        self.assertEqual(self.ruta.read_bytes(), self.original)

    def test_producto_ausente_o_repetido_conserva_el_precio_y_se_avisa(self):
        hoja = _hoja({"BLE001": ("5000", "6000")}, quitar=("DYM001",),
                     agregar=[["DYM002", "x", "", "20000", "", ""]])
        with patch.object(ap, "_descargar", return_value=hoja):
            n, omitidos = ap.aplicar_a_archivo(URL, self.ruta)
        self.assertEqual(n, 1)
        self.assertTrue(any("'DYM001'" in o for o in omitidos))
        self.assertTrue(any("'DYM002'" in o and "repetido" in o for o in omitidos))

    def test_los_avisos_citan_fila_e_id_y_nunca_el_texto_de_la_celda(self):
        secreto = "TEXTO-SECRETO-123"
        hoja = _hoja({"DYM001": (secreto, "")})
        with patch.object(ap, "_descargar", return_value=hoja):
            _, omitidos = ap.aplicar_a_archivo(URL, self.ruta)
        self.assertTrue(omitidos)
        self.assertNotIn(secreto, " ".join(omitidos))

    def test_comparar_no_escribe_y_lista_las_diferencias(self):
        with patch.object(ap, "_descargar", return_value=_hoja({"DYM001": ("18000", "")})):
            lineas = ap.comparar(URL, self.ruta)
        self.assertEqual(len(lineas), 1)
        self.assertIn("$ 17.000  ->  $ 18.000", lineas[0])
        self.assertEqual(self.ruta.read_bytes(), self.original)

    def _main(self, env, argv=()):
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / "out"
            with patch.dict(os.environ, dict(env, GITHUB_OUTPUT=str(salida)), clear=False):
                if "PRECIOS_CSV_URL" not in env:
                    os.environ.pop("PRECIOS_CSV_URL", None)
                codigo = ap.main(list(argv))
            return codigo, (salida.read_text(encoding="utf-8") if salida.exists() else "")

    def test_main_sin_url_no_es_error(self):
        codigo, salida = self._main({})
        self.assertEqual(codigo, 0)
        self.assertIn("precios_ok=true", salida)

    def test_main_con_hoja_valida(self):
        with patch.object(ap, "aplicar_a_archivo", return_value=(2, [])):
            codigo, salida = self._main({"PRECIOS_CSV_URL": URL})
        self.assertEqual((codigo, "precios_ok=true" in salida), (0, True))

    def test_main_con_filas_omitidas_aplica_el_resto_pero_marca_la_corrida(self):
        with patch.object(ap, "aplicar_a_archivo", return_value=(2, ["Fila 40 ('DEL006'): x"])):
            codigo, salida = self._main({"PRECIOS_CSV_URL": URL})
        self.assertEqual(codigo, 0)
        self.assertIn("precios_ok=false", salida)

    def test_main_con_errores_no_frena_el_build_pero_lo_marca(self):
        with patch.object(ap, "aplicar_a_archivo", side_effect=ap.PreciosInvalidos("roto")):
            codigo, salida = self._main({"PRECIOS_CSV_URL": URL})
        self.assertEqual(codigo, 0)
        self.assertIn("precios_ok=false", salida)

    def test_main_ante_un_bug_inesperado_tampoco_frena_el_build(self):
        with patch.object(ap, "aplicar_a_archivo", side_effect=RuntimeError("bug")):
            codigo, salida = self._main({"PRECIOS_CSV_URL": URL})
        self.assertEqual(codigo, 0)
        self.assertIn("precios_ok=false", salida)

    def test_main_plantilla_imprime_el_csv(self):
        from io import StringIO
        with patch("sys.stdout", new_callable=StringIO) as out:
            codigo = ap.main(["--plantilla", "1485", "1715", "289"])
        self.assertEqual(codigo, 0)
        self.assertEqual(out.getvalue(), ap.plantilla_csv(_data(), "1485", "1715", "289"))


class TestDescargaCompartida(unittest.TestCase):
    def test_solo_https_de_docs_google_com(self):
        for url in ("http://docs.google.com/x", "https://evil.example.com/x.csv",
                    "https://docs.google.com.evil.com/x", "file:///etc/passwd", ""):
            with self.subTest(url=url):
                with self.assertRaises(ap.PreciosInvalidos):
                    ap._descargar(url)

    def test_fallo_de_red_no_filtra_la_url(self):
        url = "https://docs.google.com/spreadsheets/d/CLAVE-SECRETA/pub?output=csv"
        with patch("urllib.request.OpenerDirector.open", side_effect=OSError("fallo " + url)):
            with self.assertRaises(ap.PreciosInvalidos) as cm:
                ap._descargar(url)
        self.assertNotIn("CLAVE-SECRETA", str(cm.exception))

    def test_redireccion_fuera_de_google_se_corta(self):
        with self.assertRaises(ap.PreciosInvalidos):
            ap._RedirectHandlerRestringido().redirect_request(None, None, 307, "x", {}, "https://evil.example.com/x")

    def test_tope_de_tamano(self):
        class Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, n): return b"a" * n
        with patch("urllib.request.OpenerDirector.open", return_value=Resp()):
            with self.assertRaises(ap.PreciosInvalidos):
                ap._descargar(URL)

    def test_codificacion_invalida(self):
        class Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, n): return b"\xff\xfe\xfa"
        with patch("urllib.request.OpenerDirector.open", return_value=Resp()):
            with self.assertRaises(ap.PreciosInvalidos):
                ap._descargar(URL)

    def test_el_modulo_compartido_esta_en_los_dos_aplicadores(self):
        import aplicar_calendario
        self.assertIs(aplicar_calendario.hoja_publica, hoja_publica)
        self.assertIs(ap.hoja_publica, hoja_publica)


if __name__ == "__main__":
    unittest.main()
