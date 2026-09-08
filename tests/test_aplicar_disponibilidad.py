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
        self.assertTrue(any("BEB001" in p and "no es reconocido" in p for p in problemas))
        self.assertFalse(any("sin stock" in p for p in problemas))  # el valor recibido nunca se reproduce

    def test_mensaje_de_valor_desconocido_no_repite_disponible(self):
        """El mensaje mencionaba 'Disponible' dos veces (una vez aparte,
        otra dentro de la lista de valores válidos) -- corregido para
        nombrarlo una sola vez."""
        contenido = _csv([
            ["ID", "Disponibilidad"],
            ["BEB001", "sin stock"],
            ["BEB002", ""],
            ["TYT001", ""],
        ])
        _, problemas = ad._parsear_y_validar(contenido, IDS_ACTIVOS)
        mensaje = next(p for p in problemas if "BEB001" in p)
        self.assertEqual(mensaje.count("Disponible"), 1, mensaje)
        for esperado in ("Agotado por hoy", "No disponible temporalmente", "Últimas porciones"):
            self.assertIn(esperado, mensaje)

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
        self.assertTrue(any("ningún producto activo" in p for p in problemas))
        self.assertFalse(any("ZZZ999" in p for p in problemas))  # el ID desconocido nunca se reproduce

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

    def test_no_estricto_no_levanta_y_devuelve_problemas_junto_con_lo_interpretado(self):
        contenido = _csv([
            ["ID", "Disponibilidad"],
            ["BEB001", "Agotado por hoy"],
            ["ZZZ999", ""],
        ])
        with self._stub_descarga(contenido):
            disp, problemas = ad.leer_csv("https://docs.google.com/x", ids_activos_esperados=IDS_ACTIVOS, estricto=False)
        self.assertEqual(disp.get("BEB001"), "agotado")
        self.assertTrue(problemas)  # el llamador (aplicar_a_prods) decide qué hacer con esto

    def test_estricto_sin_problemas_devuelve_tupla_con_lista_vacia(self):
        contenido = _csv([["ID", "Disponibilidad"], ["BEB001", ""], ["BEB002", ""], ["TYT001", ""]])
        with self._stub_descarga(contenido):
            disp, problemas = ad.leer_csv("https://docs.google.com/x", ids_activos_esperados=IDS_ACTIVOS, estricto=True)
        self.assertEqual(problemas, [])
        self.assertEqual(disp, {})


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


class TestAtomicidadModoNoEstricto(unittest.TestCase):
    """Si hay cualquier problema de integridad, en modo no estricto no se
    aplica NADA -- todo o nada, nunca una mezcla de productos actualizados
    y otros con el estado viejo por una fila mala en el medio."""

    def test_una_fila_mala_entre_varias_buenas_no_aplica_ningun_cambio(self):
        contenido = _csv([
            ["ID", "Disponibilidad"],
            ["BEB001", "Agotado por hoy"],   # esta sola sería un cambio válido
            ["BEB002", "Últimas porciones"],  # esta también
            ["TYT001", "sin stock"],          # valor desconocido -- problema
        ])
        prods = [
            {"id": "BEB001", "disp": "no_disp"},
            {"id": "BEB002"},
            {"id": "TYT001", "disp": "ultimas"},
        ]
        estado_original = [dict(p) for p in prods]
        with patch.object(ad, "_descargar", return_value=contenido):
            resultado = ad.aplicar_a_prods(prods, "https://docs.google.com/x", estricto=False)
        self.assertEqual(resultado, -1)
        self.assertEqual(prods, estado_original)  # ni un solo producto cambió

    def test_producto_activo_ausente_tambien_bloquea_todo_en_no_estricto(self):
        contenido = _csv([["ID", "Disponibilidad"], ["BEB001", "Agotado por hoy"]])
        prods = [{"id": "BEB001"}, {"id": "BEB002", "disp": "agotado"}, {"id": "TYT001"}]
        estado_original = [dict(p) for p in prods]
        with patch.object(ad, "_descargar", return_value=contenido):
            resultado = ad.aplicar_a_prods(prods, "https://docs.google.com/x", estricto=False)
        self.assertEqual(resultado, -1)
        self.assertEqual(prods, estado_original)

    def test_sin_problemas_si_aplica_normalmente(self):
        contenido = _csv([["ID", "Disponibilidad"], ["BEB001", "Agotado por hoy"], ["BEB002", ""], ["TYT001", ""]])
        prods = [{"id": "BEB001"}, {"id": "BEB002"}, {"id": "TYT001"}]
        with patch.object(ad, "_descargar", return_value=contenido):
            resultado = ad.aplicar_a_prods(prods, "https://docs.google.com/x", estricto=False)
        self.assertEqual(resultado, 1)
        self.assertEqual(prods[0]["disp"], "agotado")


class TestDecodificacionInvalida(unittest.TestCase):
    def test_bytes_invalidos_se_traducen_a_disponibilidad_invalida(self):
        bytes_invalidos = b"ID,Disponibilidad\r\nBEB001,\xff\xfe\x80\x81"

        class RespuestaFalsa:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self, n):
                return bytes_invalidos

        with patch.object(ad, "_RedirectHandlerRestringido"):
            with patch("urllib.request.build_opener") as mock_build_opener:
                mock_build_opener.return_value.open.return_value = RespuestaFalsa()
                with self.assertRaises(ad.DisponibilidadInvalida) as ctx:
                    ad._descargar("https://docs.google.com/x", timeout=1)
        # el mensaje nunca incluye los bytes crudos
        self.assertNotIn("\\xff", str(ctx.exception))

    def test_bytes_validos_utf8_sig_decodifican_bien(self):
        contenido_ok = "ID,Disponibilidad\r\nBEB001,".encode("utf-8-sig")

        class RespuestaFalsa:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self, n):
                return contenido_ok

        with patch("urllib.request.build_opener") as mock_build_opener:
            mock_build_opener.return_value.open.return_value = RespuestaFalsa()
            resultado = ad._descargar("https://docs.google.com/x", timeout=1)
        self.assertIn("BEB001", resultado)


class TestUrlObligatoriaEnProduccion(unittest.TestCase):
    """CI (main() -> aplicar_a_archivo(..., url_obligatoria=True)) no puede
    terminar 'exitosamente' sin URL -- eso publicaría todo como disponible
    sin que nadie se entere. Local (build.py) sigue siendo opcional."""

    def test_sin_url_y_obligatoria_levanta(self):
        with self.assertRaises(ad.DisponibilidadInvalida):
            ad.aplicar_a_archivo("", url_obligatoria=True)

    def test_sin_url_y_no_obligatoria_no_levanta(self):
        resultado = ad.aplicar_a_archivo("", url_obligatoria=False)
        self.assertEqual(resultado, -1)

    def test_main_sin_url_termina_con_exit_code_distinto_de_cero(self):
        import os as os_module
        with patch.dict(os_module.environ, {"DISPONIBILIDAD_CSV_URL": ""}, clear=False):
            with self.assertRaises(SystemExit) as ctx:
                ad.main()
        self.assertNotEqual(ctx.exception.code, 0)

    def test_main_con_url_en_blanco_tambien_falla(self):
        import os as os_module
        with patch.dict(os_module.environ, {"DISPONIBILIDAD_CSV_URL": "   "}, clear=False):
            with self.assertRaises(SystemExit) as ctx:
                ad.main()
        self.assertNotEqual(ctx.exception.code, 0)


SENTINEL = "SECRETO_NO_DEBE_APARECER_123"


class TestNuncaImprimeDatosNoConfiables(unittest.TestCase):
    """Ninguna celda de la hoja (columna ID o Disponibilidad) es confiable
    -- puede llevar cualquier cosa pegada por error, hasta una credencial.
    Ningún mensaje de problema, excepción, ni stdout/stderr debe reproducir
    ese contenido, salvo un ID que ya sea uno de nuestros públicos
    conocidos (ids_activos_esperados)."""

    def _sin_sentinel(self, *textos):
        for t in textos:
            self.assertNotIn(SENTINEL, t)

    def test_estado_invalido_con_id_conocido_no_reproduce_el_valor(self):
        contenido = _csv([["ID", "Disponibilidad"], ["BEB001", SENTINEL], ["BEB002", ""], ["TYT001", ""]])
        _, problemas = ad._parsear_y_validar(contenido, IDS_ACTIVOS)
        self._sin_sentinel(*problemas)
        # el ID sí conocido puede aparecer, el valor no
        self.assertTrue(any("BEB001" in p for p in problemas))

    def test_fila_sin_id_no_reproduce_el_valor(self):
        contenido = _csv([["ID", "Disponibilidad"], ["", SENTINEL], ["BEB001", ""], ["BEB002", ""], ["TYT001", ""]])
        _, problemas = ad._parsear_y_validar(contenido, IDS_ACTIVOS)
        self._sin_sentinel(*problemas)
        self.assertTrue(any("Fila 2" in p for p in problemas))

    def test_id_desconocido_no_se_reproduce(self):
        contenido = _csv([
            ["ID", "Disponibilidad"],
            ["BEB001", ""], ["BEB002", ""], ["TYT001", ""],
            [SENTINEL, ""],
        ])
        _, problemas = ad._parsear_y_validar(contenido, IDS_ACTIVOS)
        self._sin_sentinel(*problemas)
        self.assertTrue(any("no corresponde a ningún producto activo" in p for p in problemas))

    def test_id_duplicado_desconocido_no_se_reproduce(self):
        contenido = _csv([
            ["ID", "Disponibilidad"],
            [SENTINEL, ""], [SENTINEL, ""],
            ["BEB001", ""], ["BEB002", ""], ["TYT001", ""],
        ])
        _, problemas = ad._parsear_y_validar(contenido, IDS_ACTIVOS)
        self._sin_sentinel(*problemas)

    def test_estado_invalido_sin_ids_activos_esperados_no_reproduce_ni_id_ni_valor(self):
        """Sin el set de IDs activos (no hay forma de confirmar que el ID
        sea uno de los nuestros), ni el ID ni el valor se reproducen."""
        contenido = _csv([["ID", "Disponibilidad"], [SENTINEL, SENTINEL]])
        _, problemas = ad._parsear_y_validar(contenido, None)
        self._sin_sentinel(*problemas)

    def test_excepcion_en_modo_estricto_no_reproduce_el_sentinel(self):
        contenido = _csv([["ID", "Disponibilidad"], ["BEB001", SENTINEL], ["BEB002", ""], ["TYT001", ""]])
        with patch.object(ad, "_descargar", return_value=contenido):
            with self.assertRaises(ad.DisponibilidadInvalida) as ctx:
                ad.leer_csv("https://docs.google.com/x", ids_activos_esperados=IDS_ACTIVOS, estricto=True)
        self.assertNotIn(SENTINEL, str(ctx.exception))

    def test_stdout_stderr_de_aplicar_a_prods_no_reproduce_el_sentinel(self):
        """Cobertura de punta a punta: nada de lo que efectivamente se
        imprime por consola (avisos incluidos) contiene el centinela."""
        import contextlib
        import io as io_module

        contenido = _csv([
            ["ID", "Disponibilidad"],
            ["BEB001", SENTINEL],
            [SENTINEL, ""],
            ["BEB002", ""], ["TYT001", ""],
        ])
        prods = [{"id": "BEB001"}, {"id": "BEB002"}, {"id": "TYT001"}]
        buffer_out = io_module.StringIO()
        with patch.object(ad, "_descargar", return_value=contenido):
            with contextlib.redirect_stdout(buffer_out):
                ad.aplicar_a_prods(prods, "https://docs.google.com/x", estricto=False)
        self.assertNotIn(SENTINEL, buffer_out.getvalue())

    def test_stdout_de_main_no_reproduce_el_sentinel_en_modo_estricto(self):
        import contextlib
        import io as io_module
        import os as os_module

        contenido = _csv([
            ["ID", "Disponibilidad"],
            ["BLE001", SENTINEL],
            ["BLE002", ""],
        ])
        buffer_out = io_module.StringIO()
        with patch.object(ad, "_descargar", return_value=contenido):
            with patch("json.loads", return_value={"prods": [{"id": "BLE001"}, {"id": "BLE002"}]}):
                with patch.object(Path, "exists", return_value=True):
                    with patch.object(Path, "read_text", return_value="{}"):
                        with patch.dict(os_module.environ, {"DISPONIBILIDAD_CSV_URL": "https://docs.google.com/x"}):
                            with contextlib.redirect_stdout(buffer_out):
                                with self.assertRaises(SystemExit):
                                    ad.main()
        self.assertNotIn(SENTINEL, buffer_out.getvalue())


if __name__ == "__main__":
    unittest.main()
