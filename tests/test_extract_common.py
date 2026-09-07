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
