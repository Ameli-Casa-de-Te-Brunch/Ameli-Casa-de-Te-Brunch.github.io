"""Pruebas de build/extract_common.py: validación de URLs (positivas y
negativas), WhatsApp e Instagram. Solo biblioteca estándar -- no necesita
openpyxl ni el Excel real, así que puede correr en CI sin instalar nada."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
import extract_common as ec  # noqa: E402


class TestUrlHttpsValida(unittest.TestCase):
    def test_positivas(self):
        casos = [
            ("https://ameli-casa-de-te-brunch.github.io/", ec.DOMINIOS_MENU),
            ("https://g.page/r/CQ7xLLR2pchDEBM/review", ec.DOMINIOS_GOOGLE),
            ("https://www.google.com/maps/place/x", ec.DOMINIOS_GOOGLE),
            ("https://www.tripadvisor.com.ar/Restaurant_Review-x", ec.DOMINIOS_TRIPADVISOR),
            ("https://docs.google.com/spreadsheets/d/x/pub?output=csv", ec.DOMINIOS_DISPONIBILIDAD),
        ]
        for url, dominios in casos:
            with self.subTest(url=url):
                self.assertTrue(ec.url_https_valida(url, dominios))

    def test_negativas(self):
        casos = [
            "https://google.com.ejemplo.com/",
            "https://google.com@ejemplo.com/",
            "https://tripadvisor.com.ar.ejemplo.com/",
            "javascript:alert(1)",
            "http://g.page/",
            "http://docs.google.com/spreadsheets/d/x/pub?output=csv",  # http, no https
            "data:text/html,<script>alert(1)</script>",
            "",
            None,
        ]
        for url in casos:
            with self.subTest(url=url):
                self.assertFalse(ec.url_https_valida(url, ec.DOMINIOS_GOOGLE))

    def test_sin_dominios_permitidos_solo_exige_https(self):
        self.assertTrue(ec.url_https_valida("https://cualquier-cosa.com/"))
        self.assertFalse(ec.url_https_valida("http://cualquier-cosa.com/"))

    def test_subdominio_real_se_acepta(self):
        self.assertTrue(ec.url_https_valida("https://www.google.com/", ec.DOMINIOS_GOOGLE))
        self.assertTrue(ec.url_https_valida("https://sub.tripadvisor.com/", ec.DOMINIOS_TRIPADVISOR))


class TestUrlBaseValida(unittest.TestCase):
    """Política propia y más estricta que url_https_valida() para
    config.url_base: un origen https limpio y exacto, sin nada más. No
    debe romper TripAdvisor/Google Reseñas (esos siguen validándose con
    url_https_valida, que sí permite paths -- ver TestUrlHttpsValida
    arriba, sin cambios)."""

    def test_positivas(self):
        casos = [
            "https://ameli-casa-de-te-brunch.github.io",
            "https://ameli-casa-de-te-brunch.github.io/",
        ]
        for url in casos:
            with self.subTest(url=url):
                self.assertTrue(ec.url_base_valida(url))

    def test_negativas(self):
        casos = [
            "http://ameli-casa-de-te-brunch.github.io",  # http, no https
            "https://ejemplo-no-permitido.com",  # host no permitido
            "https://ameli-casa-de-te-brunch.github.io.ejemplo.com",  # coincidencia parcial engañosa
            "https://sub.ameli-casa-de-te-brunch.github.io",  # ni un subdominio real cuenta acá
            "https://usuario@ameli-casa-de-te-brunch.github.io",  # usuario embebido
            "https://usuario:clave@ameli-casa-de-te-brunch.github.io",  # usuario y contraseña
            "https://ameli-casa-de-te-brunch.github.io:8443",  # puerto distinto de 443
            "https://ameli-casa-de-te-brunch.github.io/menu",  # cualquier path que no sea "/"
            "https://ameli-casa-de-te-brunch.github.io?x=1",  # query string
            "https://ameli-casa-de-te-brunch.github.io/#seccion",  # fragmento
            "https://ameli-casa-de-te-brunch.github.io//",  # "//" como path
            "//ameli-casa-de-te-brunch.github.io",  # protocolo relativo
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "https://ameli-casa-de-te-brunch.github.io:abc/",  # puerto no numérico -- malformada
            "",
            None,
            42,
            ["https://ameli-casa-de-te-brunch.github.io"],
        ]
        for url in casos:
            with self.subTest(url=url):
                self.assertFalse(ec.url_base_valida(url))

    def test_regresion_query_con_token_se_rechaza_y_no_se_reproduce(self):
        """Caso exacto pedido: una query string con un valor sensible
        pegado tiene que rechazarse -- y el centinela no debe aparecer en
        ningún lado de la salida de esta prueba (acá no hay logs de por
        medio, pero el valor de retorno no lo reproduce de ninguna forma)."""
        url = "https://ameli-casa-de-te-brunch.github.io/?token=SECRETO_NO_DEBE_APARECER_123"
        self.assertFalse(ec.url_base_valida(url))

    def test_tripadvisor_y_google_con_path_siguen_funcionando(self):
        """url_base_valida es una política aparte -- no reemplaza ni
        rompe url_https_valida, que sigue permitiendo paths reales para
        TripAdvisor/Google Reseñas."""
        self.assertTrue(ec.url_https_valida(
            "https://www.tripadvisor.com.ar/Restaurant_Review-x", ec.DOMINIOS_TRIPADVISOR
        ))
        self.assertTrue(ec.url_https_valida(
            "https://g.page/r/CQ7xLLR2pchDEBM/review", ec.DOMINIOS_GOOGLE
        ))
        # y esas mismas URLs, con path, tienen que seguir siendo inválidas
        # para la política de url_base (que exige "/" o nada de path)
        self.assertFalse(ec.url_base_valida("https://www.tripadvisor.com.ar/Restaurant_Review-x"))


class TestWhatsappValido(unittest.TestCase):
    def test_positivos(self):
        self.assertEqual(ec.whatsapp_valido("5492604106653"), "5492604106653")
        self.assertEqual(ec.whatsapp_valido("+54 9 260 410-6653"), "5492604106653")
        self.assertEqual(ec.whatsapp_valido(54926041066), "54926041066")  # 11 dígitos, dentro de rango

    def test_negativos_por_longitud(self):
        self.assertIsNone(ec.whatsapp_valido("1234567"))  # 7 dígitos, corto
        self.assertIsNone(ec.whatsapp_valido("1234567890123456"))  # 16 dígitos, largo
        self.assertIsNone(ec.whatsapp_valido(""))
        self.assertIsNone(ec.whatsapp_valido(None))


class TestHandleInstagramSano(unittest.TestCase):
    def test_positivos(self):
        self.assertEqual(ec.handle_instagram_sano("@ameli.casadete"), "ameli.casadete")
        self.assertEqual(ec.handle_instagram_sano("ameli_casadete"), "ameli_casadete")

    def test_negativos(self):
        self.assertIsNone(ec.handle_instagram_sano("<script>alert(1)</script>"))
        self.assertIsNone(ec.handle_instagram_sano("con espacio"))
        self.assertIsNone(ec.handle_instagram_sano(""))
        self.assertIsNone(ec.handle_instagram_sano(None))


if __name__ == "__main__":
    unittest.main()
