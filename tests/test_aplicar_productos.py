"""Pruebas de build/aplicar_productos.py: columnas de producto del Excel maestro
(activo, destacado, recomendado, más vendido, nuevo, edición limitada, etiqueta
inicial) desde una pestaña de Google Sheets.

Lo más importante: la hoja armada desde lo publicado, leída de vuelta, no
cambia nada (idempotente); cada fila es independiente (una fila mala no frena
las demás) salvo los errores estructurales, que frenan todo; y la hoja nunca
puede publicar un producto que el Excel tiene en pausa. Sin red y sin openpyxl:
la descarga se reemplaza por texto y el Excel por una hoja de mentira."""
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
import aplicar_productos as ap  # noqa: E402
import extract_common as ec  # noqa: E402
import validate_json_publico as vjp  # noqa: E402

MENU_REAL = ROOT / "data" / "menu.json"
URL = "https://docs.google.com/spreadsheets/d/x/pub?gid=1&output=csv"
ENC = ["id", "nombre", "categoria", "estado", "activo", "destacado", "recomendado", "mas_vendido", "nuevo",
       "edicion_limitada", "etiqueta_inicial", "nota"]


def _data():
    return json.loads(MENU_REAL.read_text(encoding="utf-8"))


# Un producto sin ninguna etiqueta hoy (para probar que "Nuevo" aparece) y otro con "Favorito".
SIN_ETIQUETA = next(p["id"] for p in _data()["prods"] if not p["b"] and p["cat"] != "STC")
CON_FAVORITO = next(p["id"] for p in _data()["prods"] if "fav" in p["b"])


def _filas_publicadas(data):
    """Una fila por producto publicado, con lo que hoy muestra el menú."""
    filas = []
    for p in data["prods"]:
        b = p["b"]
        filas.append({"id": p["id"], "nombre": p["n"]["es"], "categoria": p["cat"], "estado": "Publicado",
                      "activo": "Sí", "destacado": "Sí" if p["dest"] else "No",
                      "recomendado": "Sí" if "reco" in b else "No", "mas_vendido": "Sí" if "pedido" in b else "No",
                      "nuevo": "Sí" if "nuevo" in b else "No", "edicion_limitada": "No",
                      "etiqueta_inicial": p.get("tag", ""), "nota": ""})
    return filas


def _csv(filas, columnas=ENC):
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(columnas)
    for f in filas:
        w.writerow([f.get(c, "") for c in columnas])
    return out.getvalue()


def _hoja(cambios=None, quitar=(), agregar=(), columnas=ENC):
    filas = _filas_publicadas(_data())
    filas = [f for f in filas if f["id"] not in quitar]
    for f in filas:
        if cambios and f["id"] in cambios:
            f.update(cambios[f["id"]])
    filas += list(agregar)
    return _csv(filas, columnas)


def _pausa(pid="ZZZ001", **extra):
    base = {"id": pid, "nombre": "Producto en pausa", "categoria": "DEL", "estado": "En pausa", "activo": "No",
            "destacado": "No", "recomendado": "No", "mas_vendido": "No", "nuevo": "No", "edicion_limitada": "No"}
    base.update(extra)
    return base


def _parsear(contenido, data=None):
    return ap.parsear_csv(contenido, data or _data())


def _aplicar(contenido):
    data = _data()
    filas, problemas = ap.parsear_csv(contenido, data)
    cambios = ap.aplicar_a_datos(data, filas) if filas is not None else None
    return data, cambios, problemas


class TestIdempotencia(unittest.TestCase):
    def test_la_hoja_armada_desde_lo_publicado_no_cambia_nada(self):
        data = _data()
        original = copy.deepcopy(data)
        contenido = _hoja(agregar=[_pausa("ZZZ001"), _pausa("ZZZ002")])
        filas, problemas = ap.parsear_csv(contenido, data)
        self.assertEqual(problemas, [])
        self.assertEqual(ap.aplicar_a_datos(data, filas), [])
        self.assertEqual(data, original)

    def test_cubre_los_51_publicados(self):
        filas, _ = _parsear(_hoja())
        self.assertEqual(len(filas), len(_data()["prods"]))


class TestAplicacion(unittest.TestCase):
    def test_activo_no_oculta_el_producto_y_su_precio(self):
        data, cambios, problemas = _aplicar(_hoja({"DYM001": {"activo": "No"}}))
        self.assertEqual(problemas, [])
        self.assertEqual(cambios, ["DYM001: oculto"])
        self.assertNotIn("DYM001", {p["id"] for p in data["prods"]})
        self.assertNotIn("DYM001", data["precios"])
        self.assertEqual(len(data["prods"]), len(_data()["prods"]) - 1)
        self.assertEqual(len(data["precios"]), len(_data()["precios"]) - 1)

    def test_quitar_destacado_apaga_dest_y_la_etiqueta_favorito(self):
        d = _data()
        pid = next(p["id"] for p in d["prods"] if p["dest"])
        data, cambios, _ = _aplicar(_hoja({pid: {"destacado": "No"}}))
        p = next(x for x in data["prods"] if x["id"] == pid)
        self.assertFalse(p["dest"])
        self.assertNotIn("fav", p["b"])

    def test_prioridad_de_etiquetas_destacado_recomendado_mas_vendido_nuevo(self):
        casos = [
            ({"destacado": "Sí", "recomendado": "Sí", "mas_vendido": "Sí", "nuevo": "Sí"}, ["fav"]),
            ({"destacado": "No", "recomendado": "Sí", "mas_vendido": "Sí", "nuevo": "Sí"}, ["reco"]),
            ({"destacado": "No", "recomendado": "No", "mas_vendido": "Sí", "nuevo": "Sí"}, ["pedido"]),
            ({"destacado": "No", "recomendado": "No", "mas_vendido": "No", "nuevo": "Sí"}, ["nuevo"]),
            ({"destacado": "No", "recomendado": "No", "mas_vendido": "No", "nuevo": "No"}, []),
        ]
        for flags, esperado in casos:
            with self.subTest(flags=flags):
                data, _, problemas = _aplicar(_hoja({"DYM001": flags}))
                self.assertEqual(problemas, [])
                self.assertEqual(next(x for x in data["prods"] if x["id"] == "DYM001")["b"], esperado)

    def test_la_etiqueta_sin_tacc_se_conserva(self):
        data, _, _ = _aplicar(_hoja({"STC001": {"recomendado": "Sí"}}))
        self.assertEqual(next(x for x in data["prods"] if x["id"] == "STC001")["b"], ["reco", "sintacc"])

    def test_etiqueta_inicial_se_pone_cambia_y_se_saca(self):
        data, _, p = _aplicar(_hoja({"DYM001": {"etiqueta_inicial": "Nuevo en la carta"}, "BLE001": {"etiqueta_inicial": ""}}))
        self.assertEqual(p, [])
        self.assertEqual(next(x for x in data["prods"] if x["id"] == "DYM001")["tag"], "Nuevo en la carta")
        self.assertNotIn("tag", next(x for x in data["prods"] if x["id"] == "BLE001"))

    def test_edicion_limitada_se_acepta_pero_no_cambia_nada_visible(self):
        data, cambios, problemas = _aplicar(_hoja({"DYM001": {"edicion_limitada": "Sí"}}))
        self.assertEqual((cambios, problemas), ([], []))
        self.assertEqual(data, _data())

    def test_valores_si_no_con_o_sin_tilde_y_mayusculas(self):
        for valor in ("Sí", "si", "SI", "SÍ", " sí "):
            with self.subTest(valor=valor):
                data, _, problemas = _aplicar(_hoja({SIN_ETIQUETA: {"nuevo": valor}}))
                self.assertEqual(problemas, [])
                self.assertEqual(next(x for x in data["prods"] if x["id"] == SIN_ETIQUETA)["b"], ["nuevo"])
        for valor in ("No", "no", "NO", ""):
            with self.subTest(valor=valor):
                data, cambios, problemas = _aplicar(_hoja({SIN_ETIQUETA: {"nuevo": valor}}))
                self.assertEqual((cambios, problemas), ([], []))

    def test_el_resultado_pasa_el_validador_del_json_publico(self):
        data, _, _ = _aplicar(_hoja({"DYM001": {"activo": "No"}, "BLE001": {"etiqueta_inicial": "Hoy sí", "nuevo": "Sí"}}))
        errores, _ = vjp.validate_menu_json(data)
        self.assertEqual(errores, [])

    def test_los_demas_campos_del_producto_no_se_tocan(self):
        data, _, _ = _aplicar(_hoja({"DYM001": {"nuevo": "Sí", "destacado": "No"}}))
        antes = next(x for x in _data()["prods"] if x["id"] == "DYM001")
        despues = next(x for x in data["prods"] if x["id"] == "DYM001")
        for campo in ("id", "cat", "orden", "n", "d", "m", "img", "alerg", "disp"):
            self.assertEqual(antes.get(campo), despues.get(campo), campo)


class TestFilasIndependientes(unittest.TestCase):
    def test_una_fila_mala_no_frena_a_las_demas(self):
        data, cambios, problemas = _aplicar(_hoja({CON_FAVORITO: {"nuevo": "quizás"}, SIN_ETIQUETA: {"nuevo": "Sí"}}))
        self.assertEqual(len(problemas), 1)
        self.assertTrue(problemas[0].startswith("Fila "))
        self.assertEqual(cambios, [f"{SIN_ETIQUETA}: etiquetas actualizadas"])
        self.assertEqual(next(x for x in data["prods"] if x["id"] == CON_FAVORITO), next(x for x in _data()["prods"] if x["id"] == CON_FAVORITO))

    def test_activo_vacio_o_invalido_es_error_de_esa_fila(self):
        for valor in ("", "quizás", "1"):
            with self.subTest(valor=valor):
                filas, problemas = _parsear(_hoja({"DYM001": {"activo": valor}}))
                self.assertEqual(len(problemas), 1)
                self.assertNotIn("DYM001", filas)

    def test_etiqueta_invalida(self):
        for malo in ("<b>hola</b>", "mirá http://x.com", "entrá a www.x.com", "a" * 41, "dos\nlíneas"):
            with self.subTest(malo=malo):
                filas, problemas = _parsear(_hoja({"DYM001": {"etiqueta_inicial": malo}}))
                self.assertEqual(len(problemas), 1)
                self.assertNotIn("DYM001", filas)

    def test_etiqueta_de_40_caracteres_es_el_limite_valido(self):
        _, problemas = _parsear(_hoja({"DYM001": {"etiqueta_inicial": "a" * 40}}))
        self.assertEqual(problemas, [])

    def test_id_repetido_o_con_formato_invalido(self):
        filas, problemas = _parsear(_hoja(agregar=[_filas_publicadas(_data())[0]]))
        self.assertTrue(any("repite" in p for p in problemas))
        filas, problemas = _parsear(_hoja(agregar=[_pausa("mal id!")]))
        self.assertTrue(any("formato" in p for p in problemas))

    def test_producto_publicado_sin_fila_se_deja_como_esta_y_se_informa(self):
        data, cambios, problemas = _aplicar(_hoja(quitar=("DYM001",)))
        self.assertTrue(any("DYM001" in p and "no tiene fila" in p for p in problemas))
        self.assertIn("DYM001", {p["id"] for p in data["prods"]})


class TestProductosEnPausa(unittest.TestCase):
    def test_una_fila_de_producto_en_pausa_con_no_se_ignora_sin_problemas(self):
        data, cambios, problemas = _aplicar(_hoja(agregar=[_pausa("ZZZ001")]))
        self.assertEqual((cambios, problemas), ([], []))
        self.assertEqual(data, _data())

    def test_poner_si_a_un_producto_no_publicado_se_informa_y_no_publica_nada(self):
        data, cambios, problemas = _aplicar(_hoja({SIN_ETIQUETA: {"nuevo": "Sí"}}, agregar=[_pausa("ZZZ001", activo="Sí")]))
        self.assertEqual(len(problemas), 1)
        self.assertIn("todavía no está publicado", problemas[0])
        self.assertNotIn("ZZZ001", problemas[0])  # el ID de un producto no publicado no se reproduce
        self.assertNotIn("ZZZ001", {p["id"] for p in data["prods"]})
        self.assertEqual(cambios, [f"{SIN_ETIQUETA}: etiquetas actualizadas"])  # el resto sí se aplicó
        self.assertEqual(len(data["prods"]), len(_data()["prods"]))


class TestErroresEstructurales(unittest.TestCase):
    def test_frenan_todo(self):
        casos = {
            "vacía": "",
            "columna que no existe": _hoja(agregar=[], columnas=ENC + ["color"]),
            "falta una obligatoria": _hoja(columnas=[c for c in ENC if c != "nuevo"]),
            "columna repetida": _hoja(columnas=ENC + ["activo"]),
        }
        for nombre, contenido in casos.items():
            with self.subTest(nombre):
                filas, problemas = _parsear(contenido)
                self.assertIsNone(filas)
                self.assertTrue(problemas)

    def test_demasiadas_filas(self):
        filas_ = [_pausa(f"ZZ{i:04d}") for i in range(ap.MAX_FILAS + 1)]
        filas, problemas = _parsear(_csv(filas_))
        self.assertIsNone(filas)

    def test_ocultar_demasiados_productos_de_una_vez_frena_todo(self):
        data = _data()
        ids = [p["id"] for p in data["prods"]][: ap.MAX_OCULTOS + 1]
        filas, problemas = _parsear(_hoja({i: {"activo": "No"} for i in ids}))
        self.assertIsNone(filas)
        self.assertIn(str(ap.MAX_OCULTOS), problemas[0])

    def test_ocultar_exactamente_el_maximo_pasa(self):
        ids = [p["id"] for p in _data()["prods"]][: ap.MAX_OCULTOS]
        filas, problemas = _parsear(_hoja({i: {"activo": "No"} for i in ids}))
        self.assertIsNotNone(filas)
        self.assertEqual(problemas, [])

    def test_los_mensajes_nunca_reproducen_el_texto_de_las_celdas(self):
        secreto = "TEXTO SECRETO 123"
        contenidos = [
            _hoja({"DYM001": {"activo": secreto}}),
            _hoja({"DYM001": {"nuevo": secreto}}),
            _hoja({"DYM001": {"etiqueta_inicial": "<" + secreto + ">"}}),
            _hoja(agregar=[_pausa(secreto)]),
            _hoja(columnas=ENC + [secreto]),
        ]
        for contenido in contenidos:
            _, problemas = _parsear(contenido)
            self.assertTrue(problemas)
            self.assertNotIn(secreto, " ".join(problemas))

    def test_nombre_categoria_estado_y_nota_nunca_se_leen(self):
        filas = _filas_publicadas(_data())
        for f in filas:
            f.update(nombre="<script>alert(1)</script>", categoria="x", estado="y", nota="z")
        self.assertEqual(_parsear(_csv(filas))[1], [])


class TestArchivoYMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / "menu.json"
        shutil.copy(MENU_REAL, self.ruta)
        self.original = self.ruta.read_bytes()

    def test_cambios_reescriben_el_archivo(self):
        with patch.object(ap, "_descargar", return_value=_hoja({"DYM001": {"activo": "No"}})):
            cambios, problemas = ap.aplicar_a_archivo(URL, self.ruta)
        self.assertEqual((cambios, problemas), (["DYM001: oculto"], []))
        self.assertNotIn("DYM001", {p["id"] for p in json.loads(self.ruta.read_text(encoding="utf-8"))["prods"]})
        self.assertFalse(self.ruta.with_suffix(".json.tmp").exists())

    def test_sin_cambios_no_reescribe(self):
        with patch.object(ap, "_descargar", return_value=_hoja()):
            self.assertEqual(ap.aplicar_a_archivo(URL, self.ruta), ([], []))
        self.assertEqual(self.ruta.read_bytes(), self.original)

    def test_error_estructural_levanta_y_no_toca_nada(self):
        with patch.object(ap, "_descargar", return_value=""):
            with self.assertRaises(ap.ProductosInvalidos):
                ap.aplicar_a_archivo(URL, self.ruta)
        self.assertEqual(self.ruta.read_bytes(), self.original)

    def test_filas_con_problemas_aplican_el_resto_y_devuelven_los_problemas(self):
        with patch.object(ap, "_descargar", return_value=_hoja({CON_FAVORITO: {"nuevo": "ay"}, SIN_ETIQUETA: {"nuevo": "Sí"}})):
            cambios, problemas = ap.aplicar_a_archivo(URL, self.ruta)
        self.assertEqual(cambios, [f"{SIN_ETIQUETA}: etiquetas actualizadas"])
        self.assertEqual(len(problemas), 1)

    def test_comparar_no_escribe(self):
        with patch.object(ap, "_descargar", return_value=_hoja({"DYM001": {"activo": "No"}})):
            cambios, _ = ap.comparar(URL, self.ruta)
        self.assertEqual(cambios, ["DYM001: oculto"])
        self.assertEqual(self.ruta.read_bytes(), self.original)

    def _main(self, env):
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / "out"
            with patch.dict(os.environ, dict(env, GITHUB_OUTPUT=str(salida)), clear=False):
                if "PRODUCTOS_CSV_URL" not in env:
                    os.environ.pop("PRODUCTOS_CSV_URL", None)
                codigo = ap.main([])
            return codigo, (salida.read_text(encoding="utf-8") if salida.exists() else "")

    def test_main_sin_url_no_es_error(self):
        codigo, salida = self._main({})
        self.assertEqual((codigo, "productos_ok=true" in salida), (0, True))

    def test_main_ok(self):
        with patch.object(ap, "aplicar_a_archivo", return_value=(["X: oculto"], [])):
            codigo, salida = self._main({"PRODUCTOS_CSV_URL": URL})
        self.assertEqual((codigo, "productos_ok=true" in salida), (0, True))

    def test_main_con_filas_rechazadas_marca_rojo_pero_no_frena(self):
        with patch.object(ap, "aplicar_a_archivo", return_value=(["X: oculto"], ["Fila 3: algo"])):
            codigo, salida = self._main({"PRODUCTOS_CSV_URL": URL})
        self.assertEqual((codigo, "productos_ok=false" in salida), (0, True))

    def test_main_error_estructural_o_bug_no_frenan_el_build(self):
        for error in (ap.ProductosInvalidos("roto"), RuntimeError("bug")):
            with patch.object(ap, "aplicar_a_archivo", side_effect=error):
                codigo, salida = self._main({"PRODUCTOS_CSV_URL": URL})
            self.assertEqual((codigo, "productos_ok=false" in salida), (0, True))


class _HojaDeMentira:
    """Imita lo que usa plantilla_desde_hoja de una hoja de openpyxl."""
    def __init__(self, filas):
        self.celdas = {}
        for r, fila in enumerate(filas, start=5):
            for columna, valor in fila.items():
                self.celdas[(r, columna)] = valor

    def cell(self, row, column):
        class _C:
            pass
        c = _C()
        c.value = self.celdas.get((row, column))
        return c


def _fila_excel(pid, cat, nombre, activo, **extra):
    C = ec.COL
    fila = {C["id"]: pid, C["cat"]: cat, C["activo"]: activo}
    for l in ec.LANGS:
        fila[C["nombre"][l]] = nombre if l == "es" else f"{nombre} {l}"
        fila[C["desc"][l]] = f"desc {l}"
    for k in ("destacado", "recomendado", "mas_vendido", "nuevo", "edicion_limitada"):
        fila[C[k]] = "No"
    fila[C["precio_chico"]] = 5000
    for k, v in extra.items():
        fila[C[k] if k in C else k] = v
    return fila


class TestPlantillaDesdeExcel(unittest.TestCase):
    def _plantilla(self):
        C = ec.COL
        completo_pausa = _fila_excel("AAA002", "DEL", "Torta", "No")
        sin_ingles = _fila_excel("AAA003", "DEL", "Flan", "No")
        sin_ingles[C["nombre"]["en"]] = None
        sin_ingles[C["desc"]["fr"]] = None
        sin_precio = _fila_excel("AAA004", "DEL", "Budín", "No", precio_chico=None)
        sin_precio[C["precio_grande"]] = None
        publicado = _fila_excel("AAA001", "DEL", "Medialuna", "Sí", destacado="Sí", etiqueta_inicial="De la casa")
        ws = _HojaDeMentira([publicado, completo_pausa, sin_ingles, sin_precio])
        return ap.plantilla_desde_hoja(ws, {"AAA001"})

    def test_trae_todos_los_productos_del_excel_con_sus_valores(self):
        filas = list(csv.DictReader(io.StringIO(self._plantilla())))
        self.assertEqual([f["id"] for f in filas], ["AAA001", "AAA002", "AAA003", "AAA004"])
        publicado = filas[0]
        self.assertEqual((publicado["activo"], publicado["destacado"], publicado["etiqueta_inicial"], publicado["estado"]),
                         ("Sí", "Sí", "De la casa", "Publicado"))
        self.assertEqual(filas[1]["activo"], "No")

    def test_el_estado_explica_por_que_un_producto_esta_en_pausa(self):
        filas = {f["id"]: f["estado"] for f in csv.DictReader(io.StringIO(self._plantilla()))}
        self.assertIn("contenido completo", filas["AAA002"])
        self.assertIn("falta nombre o descripción en 2 de 5 idiomas", filas["AAA003"])
        self.assertIn("sin precio", filas["AAA004"])

    def test_la_plantilla_es_una_hoja_valida_para_el_aplicador(self):
        data = _data()
        data["prods"] = [{"id": "AAA001", "cat": "DEL", "orden": 1, "dest": True, "n": {}, "d": {}, "m": [],
                          "b": ["fav"], "img": None, "tag": "De la casa"}]
        data["precios"] = {"AAA001": {"ars": "$ 5.000"}}
        filas, problemas = ap.parsear_csv(self._plantilla(), data)
        self.assertEqual(problemas, [])
        self.assertEqual(ap.aplicar_a_datos(data, filas), [])


class TestDescargaCompartida(unittest.TestCase):
    def test_solo_https_de_docs_google_com(self):
        for url in ("http://docs.google.com/x", "https://evil.example.com/x.csv", "file:///etc/passwd", ""):
            with self.subTest(url=url):
                with self.assertRaises(ap.ProductosInvalidos):
                    ap._descargar(url)

    def test_redireccion_fuera_de_google_se_corta(self):
        with self.assertRaises(ap.ProductosInvalidos):
            ap._RedirectHandlerRestringido().redirect_request(None, None, 307, "x", {}, "https://evil.example.com/x")


if __name__ == "__main__":
    unittest.main()
