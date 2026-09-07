"""Pruebas de build/aplicar_disponibilidad.py: integridad de filas, valores
válidos/desconocidos, IDs duplicados/faltantes/adicionales, tamaño máximo, y
que un fallo de descarga se traduzca en DisponibilidadInvalida sin filtrar
la URL. Solo biblioteca estándar."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
import aplicar_disponibilidad as ad  # noqa: E402
import extract_common as ec  # noqa: E402

IDS_ACTIVOS = {"BEB001", "BEB002", "TYT001"}


def _csv(filas):
    return "\n".join(",".join(f) for f in filas)


class TestParsearYValidar(unittest.TestCase):
    def test_hoja_completa_valida(self):
        contenido = _csv([
            ["ID", "Disponibilidad"],
            ["BEB001", ""],
            ["BEB002", "Agotado por hoy"],
            ["TYT001", "Últimas porciones"],
        ])
        disp, problemas = ad._parsear_y_validar(contenido, IDS_ACTIVOS)
        self.assertEqual(problemas, [])
        self.assertEqual(disp, {"BEB002": "agotado", "TYT001": "ultimas"})
        self.assertNotIn("BEB001", disp)  # vacío = disponible, sin código

    def test_valor_desconocido(self):
        contenido = _csv([
            ["ID", "Disponibilidad"],
            ["BEB001", "sin stock"],
            ["BEB002", ""],
            ["TYT001", ""],
        ])
        _, problemas = ad._parsear_y_validar(contenido, IDS_ACTIVOS)
        self.assertTrue(any("no es un valor reconocido" in p for p in problemas))

    def test_id_duplicado(self):
        contenido = _csv([
            ["ID", "Disponibilidad"],
            ["BEB001", ""],
            ["BEB001", "Agotado por hoy"],
            ["BEB002", ""],
            ["TYT001", ""],
        ])
        _, problemas = ad._parsear_y_validar(contenido, IDS_ACTIVOS)
        self.assertTrue(any("repetido" in p for p in problemas))

    def test_fila_sin_id_con_estado(self):
        contenido = _csv([
            ["ID", "Disponibilidad"],
            ["", "Agotado por hoy"],
            ["BEB001", ""],
            ["BEB002", ""],
            ["TYT001", ""],
        ])
        _, problemas = ad._parsear_y_validar(contenido, IDS_ACTIVOS)
        self.assertTrue(any("no tiene ID" in p for p in problemas))

    def test_fila_sin_id_sin_estado_se_ignora(self):
        contenido = _csv([
            ["ID", "Disponibilidad"],
            ["", ""],
            ["BEB001", ""],
            ["BEB002", ""],
            ["TYT001", ""],
        ])
        _, problemas = ad._parsear_y_validar(contenido, IDS_ACTIVOS)
        self.assertEqual(problemas, [])

    def test_id_desconocido(self):
        contenido = _csv([
            ["ID", "Disponibilidad"],
            ["BEB001", ""],
            ["BEB002", ""],
            ["TYT001", ""],
            ["ZZZ999", ""],
        ])
        _, problemas = ad._parsear_y_validar(contenido, IDS_ACTIVOS)
        self.assertTrue(any("ZZZ999" in p and "ningún producto activo" in p for p in problemas))

    def test_producto_activo_ausente(self):
        contenido = _csv([
            ["ID", "Disponibilidad"],
            ["BEB001", ""],
            ["BEB002", ""],
            # falta TYT001 por completo
        ])
        _, problemas = ad._parsear_y_validar(contenido, IDS_ACTIVOS)
        self.assertTrue(any("TYT001" in p and "no tiene ninguna fila" in p for p in problemas))

    def test_hoja_vacia(self):
        disp, problemas = ad._parsear_y_validar("", IDS_ACTIVOS)
        self.assertEqual(disp, {})
        self.assertTrue(any("vacía" in p for p in problemas))

    def test_hoja_truncada_sin_filas_de_datos(self):
        contenido = _csv([["ID", "Disponibilidad"]])
        _, problemas = ad._parsear_y_validar(contenido, IDS_ACTIVOS)
        self.assertTrue(any("no tiene ninguna fila de datos" in p for p in problemas))

    def test_sin_ids_activos_esperados_no_exige_cobertura(self):
        """Cuando no se pasa el set de IDs activos (compatibilidad), no se
        exige cobertura total ni se detectan IDs desconocidos -- mismo
        comportamiento que antes de este cambio para quien no lo use."""
        contenido = _csv([["ID", "Disponibilidad"], ["BEB001", ""]])
        disp, problemas = ad._parsear_y_validar(contenido, None)
        self.assertEqual(problemas, [])
        self.assertEqual(disp, {})


class TestModoEstrictoVsNoEstricto(unittest.TestCase):
    def _stub_descarga(self, contenido):
        return patch.object(ad, "_descargar", return_value=contenido)

    def test_estricto_levanta_con_problemas(self):
        contenido = _csv([["ID", "Disponibilidad"], ["ZZZ999", ""]])
        with self._stub_descarga(contenido):
            with self.assertRaises(ad.DisponibilidadInvalida):
                ad.leer_csv("https://docs.google.com/x", ids_activos_esperados=IDS_ACTIVOS, estricto=True)

    def test_no_estricto_no_levanta_y_devuelve_lo_que_pudo(self):
        contenido = _csv([
            ["ID", "Disponibilidad"],
            ["BEB001", "Agotado por hoy"],
            ["ZZZ999", ""],
        ])
        with self._stub_descarga(contenido):
            disp = ad.leer_csv("https://docs.google.com/x", ids_activos_esperados=IDS_ACTIVOS, estricto=False)
        self.assertEqual(disp.get("BEB001"), "agotado")


class TestTamanoMaximo(unittest.TestCase):
    def test_dentro_del_limite_no_levanta(self):
        ad._verificar_tamano(b"x" * ad.TAMANO_MAXIMO_BYTES)

    def test_por_encima_del_limite_levanta(self):
        with self.assertRaises(ad.DisponibilidadInvalida):
            ad._verificar_tamano(b"x" * (ad.TAMANO_MAXIMO_BYTES + 1))


class TestFalloDeDescarga(unittest.TestCase):
    def test_error_de_red_no_filtra_la_url_en_el_mensaje(self):
        url_secreta = "https://docs.google.com/spreadsheets/d/id-super-secreto/pub?output=csv"

        class ErrorConUrl(Exception):
            def __str__(self):
                return f"fallo al conectar con {url_secreta}"

        with patch("urllib.request.build_opener") as mock_build_opener:
            mock_build_opener.return_value.open.side_effect = ErrorConUrl()
            with self.assertRaises(ad.DisponibilidadInvalida) as ctx:
                ad._descargar(url_secreta, timeout=1)
        self.assertNotIn(url_secreta, str(ctx.exception))
        self.assertNotIn("id-super-secreto", str(ctx.exception))

    def test_url_no_permitida_no_intenta_descargar(self):
        with self.assertRaises(ad.DisponibilidadInvalida):
            ad._descargar("https://ejemplo-no-permitido.com/x.csv", timeout=1)


class TestRedireccion(unittest.TestCase):
    """Google Sheets redirige (307) el CSV publicado desde docs.google.com
    hacia un host doc-*-*-sheets.googleusercontent.com -- comprobado en
    vivo contra la hoja real de disponibilidad del maestro. Ese redirect
    tiene que permitirse; cualquier otro destino, no."""

    def test_redireccion_a_googleusercontent_permitida(self):
        self.assertTrue(
            ec.url_https_valida(
                "https://doc-00-2k-sheets.googleusercontent.com/pub/x", ad.DOMINIOS_REDIRECCION_PERMITIDOS
            )
        )

    def test_redireccion_a_host_ajeno_no_permitida(self):
        self.assertFalse(
            ec.url_https_valida("https://ejemplo-no-permitido.com/x", ad.DOMINIOS_REDIRECCION_PERMITIDOS)
        )


class TestAplicarAProds(unittest.TestCase):
    def test_estricto_propaga_excepcion(self):
        prods = [{"id": "BEB001"}, {"id": "BEB002"}, {"id": "TYT001"}]
        with patch.object(ad, "leer_csv", side_effect=ad.DisponibilidadInvalida("problema de prueba")):
            with self.assertRaises(ad.DisponibilidadInvalida):
                ad.aplicar_a_prods(prods, "https://docs.google.com/x", estricto=True)

    def test_no_estricto_devuelve_menos_uno_y_no_rompe(self):
        prods = [{"id": "BEB001"}, {"id": "BEB002"}, {"id": "TYT001"}]
        with patch.object(ad, "leer_csv", side_effect=ad.DisponibilidadInvalida("problema de prueba")):
            resultado = ad.aplicar_a_prods(prods, "https://docs.google.com/x", estricto=False)
        self.assertEqual(resultado, -1)

    def test_sin_url_devuelve_menos_uno_sin_tocar_nada(self):
        prods = [{"id": "BEB001", "disp": "agotado"}]
        resultado = ad.aplicar_a_prods(prods, "", estricto=True)
        self.assertEqual(resultado, -1)
        self.assertEqual(prods[0]["disp"], "agotado")  # intacto


if __name__ == "__main__":
    unittest.main()
