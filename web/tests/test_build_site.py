#!/usr/bin/env python3
"""Suite de pruebas de build_site.py -- stdlib únicamente (unittest),
sin dependencias externas, sin red. Corre con:

    python -m unittest discover -s tests -v

Los tests de construir() end-to-end trabajan sobre un sandbox temporal
aislado (nunca tocan site.config.json, templates/ ni dist/ reales) --
se logra parcheando las constantes de ruta del módulo build_site
durante cada test y restaurándolas siempre en tearDown."""
import contextlib
import copy
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build_site  # noqa: E402


def _renombrar_que_falla_en(indices_falla):
    """Devuelve (fake, llamadas) para parchear build_site._renombrar en
    una prueba: `llamadas` acumula cada (origen, destino) tal como se
    invocó, y la llamada cuyo número (1-based) esté en `indices_falla`
    levanta OSError en vez de renombrar de verdad -- así se simula un
    fallo puntual y determinista del sistema de archivos sin depender
    de condiciones reales (permisos, disco lleno), que no son
    reproducibles de forma portable."""
    if isinstance(indices_falla, int):
        indices_falla = {indices_falla}
    llamadas = []
    original = build_site._renombrar

    def fake(origen, destino):
        llamadas.append((origen, destino))
        if len(llamadas) in indices_falla:
            raise OSError(f"fallo simulado en la llamada #{len(llamadas)} de _renombrar")
        return original(origen, destino)

    return fake, llamadas


CONFIG_VALIDO = {
    "marca": "Amelí",
    "categoria": "Casa de Té & Brunch",
    "ubicacion_corta": "Malargüe, Mendoza",
    "ubicacion_completa": "Malargüe, Mendoza, Argentina",
    "tagline": "Patagonia lenta",
    "descripcion_menu_confirmada": "Desayunos, brunch, pastelería artesanal, café y selección de tés.",
    "site_url": "https://amelicasadete.com.ar/",
    "menu_url": "/menu/",
    "whatsapp_e164": "5492604106653",
    "whatsapp_display": "+54 9 260 410-6653",
    "contacto_email": "contacto@amelicasadete.com.ar",
    "instagram_handle": "ameli.casadete",
    "google_reviews_url": "https://g.page/r/CQ7xLLR2pchDEBM/review",
    "tripadvisor_url": "https://www.tripadvisor.com.ar/UserReviewEdit-d34258612?m=68676",
    "direccion_calle": "Villegas Oeste 48, Malargüe",
    "maps_query": "Amelí Casa de Té & Brunch, Villegas Oeste 48, Malargüe, Mendoza, Argentina",
    "horarios": None,
    "presentacion_sobre_ameli": None,
    "razon_social": None,
    "cuit": None,
    "domicilio_comercial": None,
    "aviso_copyright": None,
    "informacion_servicio": None,
    "servicios_habilitado": False,
}


def config_valido(**cambios):
    base = copy.deepcopy(CONFIG_VALIDO)
    base.update(cambios)
    return base


# ================= _url_https_valida =================

class TestUrlHttpsValida(unittest.TestCase):
    def test_acepta_https_valida(self):
        self.assertTrue(build_site._url_https_valida(
            "https://www.tripadvisor.com.ar/algo?x=1", build_site.DOMINIOS_TRIPADVISOR))

    def test_acepta_subdominio_real(self):
        self.assertTrue(build_site._url_https_valida(
            "https://sub.google.com/reviews", build_site.DOMINIOS_GOOGLE))

    def test_rechaza_http(self):
        self.assertFalse(build_site._url_https_valida(
            "http://google.com", build_site.DOMINIOS_GOOGLE))

    def test_rechaza_esquema_javascript(self):
        self.assertFalse(build_site._url_https_valida(
            "javascript:alert(1)", build_site.DOMINIOS_GOOGLE))

    def test_rechaza_esquema_data(self):
        self.assertFalse(build_site._url_https_valida(
            "data:text/html,hola", build_site.DOMINIOS_GOOGLE))

    def test_rechaza_usuario_en_url(self):
        self.assertFalse(build_site._url_https_valida(
            "https://usuario@google.com/", build_site.DOMINIOS_GOOGLE))

    def test_rechaza_usuario_y_password_en_url(self):
        self.assertFalse(build_site._url_https_valida(
            "https://usuario:clave@google.com/", build_site.DOMINIOS_GOOGLE))

    def test_rechaza_puerto_no_443(self):
        self.assertFalse(build_site._url_https_valida(
            "https://google.com:8443/", build_site.DOMINIOS_GOOGLE))

    def test_acepta_puerto_443_explicito(self):
        self.assertTrue(build_site._url_https_valida(
            "https://google.com:443/", build_site.DOMINIOS_GOOGLE))

    def test_acepta_sin_puerto(self):
        self.assertTrue(build_site._url_https_valida(
            "https://google.com/", build_site.DOMINIOS_GOOGLE))

    def test_rechaza_dominio_no_permitido(self):
        self.assertFalse(build_site._url_https_valida(
            "https://bing.com/", build_site.DOMINIOS_GOOGLE))

    def test_rechaza_dominio_enganoso_como_sufijo_falso(self):
        # "tripadvisor.com.ar" es un dominio permitido -- pero
        # "tripadvisor.com.ar.evil.com" NO es ese dominio ni un
        # subdominio suyo (el host permitido tendría que ser el
        # SUFIJO, no un prefijo del host real).
        self.assertFalse(build_site._url_https_valida(
            "https://tripadvisor.com.ar.evil.com/", build_site.DOMINIOS_TRIPADVISOR))

    def test_rechaza_dominio_enganoso_como_prefijo_pegado(self):
        # "eviltripadvisor.com" contiene "tripadvisor.com" como
        # subcadena pero no termina en ".tripadvisor.com".
        self.assertFalse(build_site._url_https_valida(
            "https://eviltripadvisor.com/", build_site.DOMINIOS_TRIPADVISOR))

    def test_rechaza_url_malformada_puerto_no_numerico(self):
        self.assertFalse(build_site._url_https_valida(
            "https://google.com:noesunpuerto/", build_site.DOMINIOS_GOOGLE))

    def test_rechaza_vacio(self):
        self.assertFalse(build_site._url_https_valida("", build_site.DOMINIOS_GOOGLE))

    def test_rechaza_none(self):
        self.assertFalse(build_site._url_https_valida(None, build_site.DOMINIOS_GOOGLE))

    def test_rechaza_tipo_no_str(self):
        self.assertFalse(build_site._url_https_valida(12345, build_site.DOMINIOS_GOOGLE))


# ================= _site_url_valida =================

class TestSiteUrlValida(unittest.TestCase):
    def test_acepta_exacta_sin_barra_final(self):
        self.assertTrue(build_site._site_url_valida("https://amelicasadete.com.ar"))

    def test_acepta_exacta_con_barra_final(self):
        self.assertTrue(build_site._site_url_valida("https://amelicasadete.com.ar/"))

    def test_rechaza_subdominio(self):
        # Política más estricta que _url_https_valida: acá ni un
        # subdominio real cuenta -- tiene que ser el origen exacto.
        self.assertFalse(build_site._site_url_valida("https://menu.amelicasadete.com.ar/"))

    def test_rechaza_http(self):
        self.assertFalse(build_site._site_url_valida("http://amelicasadete.com.ar/"))

    def test_rechaza_path_extra(self):
        self.assertFalse(build_site._site_url_valida("https://amelicasadete.com.ar/menu"))

    def test_rechaza_query_string(self):
        self.assertFalse(build_site._site_url_valida("https://amelicasadete.com.ar/?x=1"))

    def test_rechaza_fragmento(self):
        self.assertFalse(build_site._site_url_valida("https://amelicasadete.com.ar/#top"))

    def test_rechaza_usuario_password(self):
        self.assertFalse(build_site._site_url_valida("https://user:pass@amelicasadete.com.ar/"))

    def test_rechaza_puerto_no_443(self):
        self.assertFalse(build_site._site_url_valida("https://amelicasadete.com.ar:8443/"))

    def test_rechaza_otro_dominio(self):
        self.assertFalse(build_site._site_url_valida("https://otrodominio.com/"))

    def test_rechaza_vacio_o_none(self):
        self.assertFalse(build_site._site_url_valida(""))
        self.assertFalse(build_site._site_url_valida(None))


# ================= validar_config =================

class TestValidarConfig(unittest.TestCase):
    def test_config_valido_no_da_errores_en_preview(self):
        self.assertEqual(build_site.validar_config(config_valido(), requiere_site_url=False), [])

    def test_config_valido_no_da_errores_en_produccion(self):
        self.assertEqual(build_site.validar_config(config_valido(), requiere_site_url=True), [])

    def test_falta_campo_obligatorio(self):
        config = config_valido()
        del config["marca"]
        errores = build_site.validar_config(config, requiere_site_url=False)
        self.assertTrue(any("marca" in e for e in errores))

    def test_tipo_incorrecto_en_campo_de_texto(self):
        errores = build_site.validar_config(config_valido(marca=12345), requiere_site_url=False)
        self.assertTrue(any("marca" in e for e in errores))

    def test_texto_demasiado_largo(self):
        errores = build_site.validar_config(
            config_valido(tagline="x" * 500), requiere_site_url=False)
        self.assertTrue(any("tagline" in e for e in errores))

    def test_whatsapp_invalido_letras(self):
        errores = build_site.validar_config(
            config_valido(whatsapp_e164="no-es-un-numero"), requiere_site_url=False)
        self.assertTrue(any("whatsapp_e164" in e for e in errores))

    def test_whatsapp_invalido_muy_corto(self):
        errores = build_site.validar_config(
            config_valido(whatsapp_e164="123"), requiere_site_url=False)
        self.assertTrue(any("whatsapp_e164" in e for e in errores))

    def test_contacto_email_exige_dominio_institucional(self):
        errores = build_site.validar_config(
            config_valido(contacto_email="contacto@gmail.com"), requiere_site_url=False)
        self.assertTrue(any("contacto_email" in e for e in errores))

    def test_instagram_invalido(self):
        errores = build_site.validar_config(
            config_valido(instagram_handle="no valido!"), requiere_site_url=False)
        self.assertTrue(any("instagram_handle" in e for e in errores))

    def test_maps_query_vacio(self):
        errores = build_site.validar_config(config_valido(maps_query=""), requiere_site_url=False)
        self.assertTrue(any("maps_query" in e for e in errores))

    def test_direccion_calle_vacia(self):
        errores = build_site.validar_config(config_valido(direccion_calle=""), requiere_site_url=False)
        self.assertTrue(any("direccion_calle" in e for e in errores))

    def test_direccion_calle_falta(self):
        config = config_valido()
        del config["direccion_calle"]
        errores = build_site.validar_config(config, requiere_site_url=False)
        self.assertTrue(any("direccion_calle" in e for e in errores))

    def test_horarios_null_no_da_error(self):
        self.assertEqual(
            build_site.validar_config(config_valido(horarios=None), requiere_site_url=False), [])

    def test_horarios_texto_no_da_error(self):
        self.assertEqual(
            build_site.validar_config(
                config_valido(horarios="Lunes a viernes: 9 a 18."), requiere_site_url=False),
            [])

    def test_horarios_tipo_incorrecto(self):
        errores = build_site.validar_config(config_valido(horarios=123), requiere_site_url=False)
        self.assertTrue(any("horarios" in e for e in errores))

    def test_menu_url_dominio_no_permitido(self):
        errores = build_site.validar_config(
            config_valido(menu_url="https://otro-sitio.com/"), requiere_site_url=False)
        self.assertTrue(any("menu_url" in e for e in errores))

    def test_menu_url_acepta_ruta_interna_menu(self):
        """Arquitectura unificada: /menu/ es el valor real esperado hoy."""
        self.assertEqual(
            build_site.validar_config(config_valido(menu_url="/menu/"), requiere_site_url=False), [])

    def test_menu_url_acepta_url_externa_de_rollback(self):
        """El dominio externo del repo separado sigue aceptado a propósito,
        como red de seguridad para un rollback sin tocar código -- ver
        procedimiento de rollback del informe de unificación."""
        self.assertEqual(
            build_site.validar_config(
                config_valido(menu_url="https://ameli-casa-de-te-brunch.github.io/"),
                requiere_site_url=False),
            [])

    def test_menu_url_rechaza_ruta_interna_distinta_de_menu(self):
        errores = build_site.validar_config(
            config_valido(menu_url="/otra-ruta/"), requiere_site_url=False)
        self.assertTrue(any("menu_url" in e for e in errores))

    def test_site_url_opcional_en_preview(self):
        config = config_valido()
        del config["site_url"]
        self.assertEqual(build_site.validar_config(config, requiere_site_url=False), [])

    def test_site_url_obligatorio_en_produccion(self):
        config = config_valido()
        del config["site_url"]
        errores = build_site.validar_config(config, requiere_site_url=True)
        self.assertTrue(any("site_url" in e for e in errores))

    def test_site_url_invalido_en_produccion(self):
        errores = build_site.validar_config(
            config_valido(site_url="https://otro-dominio.com/"), requiere_site_url=True)
        self.assertTrue(any("site_url" in e for e in errores))

    def test_site_url_invalido_incluso_en_preview_si_esta_presente(self):
        # No se acepta basura en site_url solo porque estamos en
        # preview -- si está presente, tiene que ser válido igual.
        errores = build_site.validar_config(
            config_valido(site_url="no-es-una-url"), requiere_site_url=False)
        self.assertTrue(any("site_url" in e for e in errores))

    def test_sobre_ameli_null_no_da_error(self):
        self.assertEqual(
            build_site.validar_config(config_valido(presentacion_sobre_ameli=None), requiere_site_url=False), [])

    def test_sobre_ameli_texto_no_da_error(self):
        self.assertEqual(
            build_site.validar_config(
                config_valido(presentacion_sobre_ameli="Texto real."), requiere_site_url=False),
            [])

    def test_sobre_ameli_tipo_incorrecto(self):
        errores = build_site.validar_config(
            config_valido(presentacion_sobre_ameli=123), requiere_site_url=False)
        self.assertTrue(any("presentacion_sobre_ameli" in e for e in errores))

    def test_datos_legales_todos_null_no_da_error(self):
        self.assertEqual(build_site.validar_config(config_valido(), requiere_site_url=False), [])

    def test_cuit_formato_invalido(self):
        errores = build_site.validar_config(
            config_valido(razon_social="Amelí SRL", cuit="30123456789",
                          domicilio_comercial="Malargüe, Mendoza"),
            requiere_site_url=False)
        self.assertTrue(any("cuit" in e for e in errores))

    def test_cuit_formato_valido_no_da_error_de_formato(self):
        errores = build_site.validar_config(
            config_valido(razon_social="Amelí SRL", cuit="30-12345678-9",
                          domicilio_comercial="Malargüe, Mendoza"),
            requiere_site_url=False)
        self.assertFalse(any("cuit" in e for e in errores))

    def test_datos_fiscales_parciales_dan_error(self):
        # Solo razon_social, sin cuit ni domicilio -- un dato fiscal
        # parcial en el pie es peor que no mostrar nada.
        errores = build_site.validar_config(
            config_valido(razon_social="Amelí SRL"), requiere_site_url=False)
        self.assertTrue(any("razon_social" in e and "domicilio_comercial" in e for e in errores))

    def test_datos_fiscales_completos_no_da_error(self):
        errores = build_site.validar_config(
            config_valido(razon_social="Amelí SRL", cuit="30-12345678-9",
                          domicilio_comercial="Malargüe, Mendoza"),
            requiere_site_url=False)
        self.assertEqual(errores, [])

    def test_informacion_servicio_null_no_da_error(self):
        self.assertEqual(
            build_site.validar_config(config_valido(informacion_servicio=None), requiere_site_url=False), [])

    def test_informacion_servicio_tipo_incorrecto(self):
        errores = build_site.validar_config(
            config_valido(informacion_servicio=123), requiere_site_url=False)
        self.assertTrue(any("informacion_servicio" in e for e in errores))


# ================= construir() end-to-end, en sandbox aislado =================

class SandboxConstruirTestCase(unittest.TestCase):
    """Base: arma un sandbox temporal con la misma forma que el
    proyecto real (templates/ + assets/ + site.config.json) y parchea
    las rutas de build_site para apuntar ahí -- nunca toca el proyecto
    real (ni site.config.json, ni templates/, ni dist/)."""

    def setUp(self):
        self._rutas_originales = {
            "HERE": build_site.HERE,
            "CONFIG_PATH": build_site.CONFIG_PATH,
            "TEMPLATE_INDEX_PATH": build_site.TEMPLATE_INDEX_PATH,
            "TEMPLATE_404_PATH": build_site.TEMPLATE_404_PATH,
            "ASSETS_SRC": build_site.ASSETS_SRC,
            "DIST_PATH": build_site.DIST_PATH,
        }

        self.sandbox = Path(tempfile.mkdtemp(prefix="ameli-web-sandbox-"))
        (self.sandbox / "templates").mkdir()
        (self.sandbox / "assets" / "css").mkdir(parents=True)
        (self.sandbox / "assets" / "js").mkdir(parents=True)
        (self.sandbox / "assets" / "fonts").mkdir(parents=True)
        (self.sandbox / "assets" / "img").mkdir(parents=True)

        # Copias reales de los templates y assets del proyecto real
        # (solo lectura de acá, nunca se escribe sobre el original).
        shutil.copy2(self._rutas_originales["TEMPLATE_INDEX_PATH"],
                     self.sandbox / "templates" / "index.template.html")
        shutil.copy2(self._rutas_originales["TEMPLATE_404_PATH"],
                     self.sandbox / "templates" / "404.template.html")
        for sub in ("css", "js", "fonts", "img"):
            origen = self._rutas_originales["ASSETS_SRC"] / sub
            for archivo in origen.iterdir():
                if archivo.is_file():
                    shutil.copy2(archivo, self.sandbox / "assets" / sub / archivo.name)

        (self.sandbox / "site.config.json").write_text(
            json.dumps(config_valido(), ensure_ascii=False, indent=2), encoding="utf-8")

        build_site.HERE = self.sandbox
        build_site.CONFIG_PATH = self.sandbox / "site.config.json"
        build_site.TEMPLATE_INDEX_PATH = self.sandbox / "templates" / "index.template.html"
        build_site.TEMPLATE_404_PATH = self.sandbox / "templates" / "404.template.html"
        build_site.ASSETS_SRC = self.sandbox / "assets"
        build_site.DIST_PATH = self.sandbox / "dist"

    def tearDown(self):
        for clave, valor in self._rutas_originales.items():
            setattr(build_site, clave, valor)
        shutil.rmtree(self.sandbox, ignore_errors=True)

    def escribir_config(self, config: dict):
        build_site.CONFIG_PATH.write_text(
            json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    def _manifiesto_dist(self):
        """(ruta relativa, contenido) de cada archivo en dist/ -- para
        comparar byte a byte que dist/ no cambió entre dos momentos."""
        return sorted(
            (p.relative_to(build_site.DIST_PATH).as_posix(), p.read_bytes())
            for p in build_site.DIST_PATH.rglob("*") if p.is_file()
        )


class TestConstruirPreviewYProduccion(SandboxConstruirTestCase):
    def test_preview_index_siempre_noindex_sin_canonical(self):
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn('name="robots" content="noindex, nofollow"', contenido)
        self.assertNotIn('rel="canonical"', contenido)

    def test_preview_robots_txt_bloquea_todo(self):
        build_site.construir(produccion=False)
        robots = (build_site.DIST_PATH / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("Disallow: /", robots)

    def test_preview_no_genera_sitemap(self):
        build_site.construir(produccion=False)
        self.assertFalse((build_site.DIST_PATH / "sitemap.xml").exists())

    def test_produccion_index_con_canonical_y_robots_indexable(self):
        build_site.construir(produccion=True)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn('name="robots" content="index, follow"', contenido)
        self.assertIn('rel="canonical" href="https://amelicasadete.com.ar/"', contenido)

    def test_produccion_robots_txt_permite_y_referencia_sitemap(self):
        build_site.construir(produccion=True)
        robots = (build_site.DIST_PATH / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("Allow: /", robots)
        self.assertIn("Sitemap: https://amelicasadete.com.ar/sitemap.xml", robots)

    def test_produccion_genera_sitemap_con_site_url(self):
        build_site.construir(produccion=True)
        sitemap = (build_site.DIST_PATH / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("<loc>https://amelicasadete.com.ar/</loc>", sitemap)

    def test_produccion_sin_site_url_falla_antes_de_escribir(self):
        config = config_valido()
        del config["site_url"]
        self.escribir_config(config)
        with self.assertRaises(SystemExit):
            build_site.construir(produccion=True)
        self.assertFalse(build_site.DIST_PATH.exists())

    def test_404_siempre_noindex_en_ambos_modos(self):
        build_site.construir(produccion=False)
        contenido_preview = (build_site.DIST_PATH / "404.html").read_text(encoding="utf-8")
        self.assertIn('name="robots" content="noindex, nofollow"', contenido_preview)

        build_site.construir(produccion=True)
        contenido_prod = (build_site.DIST_PATH / "404.html").read_text(encoding="utf-8")
        self.assertIn('name="robots" content="noindex, nofollow"', contenido_prod)

    def test_404_permite_volver_al_inicio(self):
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "404.html").read_text(encoding="utf-8")
        self.assertIn('href="index.html"', contenido)

    def test_privacidad_siempre_noindex_en_ambos_modos(self):
        """privacidad.html es un borrador (ver aviso PROPUESTO adentro)
        -- nunca debe ser indexable, ni siquiera en producción."""
        build_site.construir(produccion=False)
        contenido_preview = (build_site.DIST_PATH / "privacidad.html").read_text(encoding="utf-8")
        self.assertIn('name="robots" content="noindex, nofollow"', contenido_preview)

        build_site.construir(produccion=True)
        contenido_prod = (build_site.DIST_PATH / "privacidad.html").read_text(encoding="utf-8")
        self.assertIn('name="robots" content="noindex, nofollow"', contenido_prod)

    def test_privacidad_explica_alcance_y_derechos(self):
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "privacidad.html").read_text(encoding="utf-8")
        self.assertIn("Datos tratados y finalidad", contenido)
        self.assertIn("Tus derechos", contenido)
        self.assertIn("Ley 25.326", contenido)
        self.assertIn('href="index.html"', contenido)

    def test_privacidad_identificacion_legal_ausente_por_defecto(self):
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "privacidad.html").read_text(encoding="utf-8")
        self.assertNotIn("Responsable del tratamiento", contenido)

    def test_enlaces_externos_llevan_rel_seguro(self):
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        for match in re.finditer(r'<a\s[^>]*target="_blank"[^>]*>', contenido):
            self.assertIn('rel="noopener noreferrer"', match.group(0))

    def test_dist_no_contiene_archivos_privados(self):
        build_site.construir(produccion=False)
        for ruta in build_site.DIST_PATH.rglob("*"):
            if ruta.is_dir():
                continue
            self.assertNotEqual(ruta.suffix.lower(), ".py", msg=f"archivo .py en dist/: {ruta}")
            self.assertNotEqual(ruta.suffix.lower(), ".json", msg=f"archivo .json en dist/: {ruta}")
            self.assertNotEqual(ruta.suffix.lower(), ".md", msg=f"archivo .md en dist/: {ruta}")
            self.assertNotIn("__pycache__", ruta.parts)
            self.assertNotIn(".git", ruta.parts)

    def test_sobre_ameli_se_omite_si_null(self):
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("Sobre Amelí", contenido)

    def test_sobre_ameli_se_incluye_si_hay_texto(self):
        self.escribir_config(config_valido(presentacion_sobre_ameli="Una historia real."))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn("Una historia real.", contenido)
        self.assertIn("Nuestra historia", contenido)

    def test_sobre_ameli_con_varios_parrafos_genera_un_p_por_parrafo(self):
        """Texto real de Ignacio: 3 ideas separadas por línea en blanco
        -- tienen que quedar como 3 <p class="texto-editorial"> reales
        dentro de .sobre-ameli, no un único bloque de texto plano con
        saltos de línea invisibles para un lector de pantalla."""
        self.escribir_config(config_valido(presentacion_sobre_ameli=(
            "Primer párrafo real.\n\nSegundo párrafo real.\n\nTercer párrafo real.")))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        bloque = re.search(
            r'<section class="sobre-ameli".*?</section>', contenido, flags=re.S).group(0)
        parrafos = re.findall(r'<p class="texto-editorial">([^<]*)</p>', bloque)
        self.assertEqual(
            parrafos,
            ["Primer párrafo real.", "Segundo párrafo real.", "Tercer párrafo real."])

    def test_horarios_se_omiten_si_null(self):
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("horario-info", contenido)

    def test_horarios_se_incluyen_si_hay_texto(self):
        self.escribir_config(config_valido(
            horarios="Martes a sábado: 9:00–13:00 y 17:30–21:00.\nDomingo: 17:30–21:00.\nLunes: cerrado."))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn("horario-info", contenido)
        self.assertIn("Martes a sábado: 9:00–13:00 y 17:30–21:00.", contenido)
        self.assertIn("Domingo: 17:30–21:00.", contenido)
        self.assertIn("Lunes: cerrado.", contenido)

    def test_direccion_calle_aparece_en_como_llegar_y_en_maps_url(self):
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn(">Villegas Oeste 48, Malargüe<", contenido)
        enlace_maps = re.search(r'href="(https://www\.google\.com/maps[^"]*)"', contenido).group(1)
        self.assertIn(urllib.parse.quote("Villegas Oeste 48"), enlace_maps)

    def test_datos_legales_se_omiten_si_null(self):
        """Estado por defecto de site.config.json real -- los tres
        campos fiscales en null, nada de esto debe aparecer publicado.
        Se descartan los comentarios HTML antes de comparar: el propio
        template explica en un comentario por qué el bloque está
        ausente, y ese comentario menciona la palabra "CUIT" sin que
        eso implique que el dato esté publicado (los comentarios no son
        contenido -- no los ve un lector de pantalla ni un visitante)."""
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        sin_comentarios = re.sub(r"<!--.*?-->", "", contenido, flags=re.S)
        self.assertNotIn("CUIT", sin_comentarios)

    def test_datos_legales_se_incluyen_si_completos(self):
        self.escribir_config(config_valido(
            razon_social="Amelí SRL", cuit="30-12345678-9",
            domicilio_comercial="Av. San Martín 123, Malargüe, Mendoza"))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn("Amelí SRL", contenido)
        self.assertIn("30-12345678-9", contenido)
        self.assertIn("Av. San Martín 123, Malargüe, Mendoza", contenido)

    def test_copyright_se_omite_si_null(self):
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("Copyright", contenido)
        self.assertNotIn("©", contenido)

    def test_copyright_se_incluye_si_hay_texto(self):
        self.escribir_config(config_valido(aviso_copyright="© 2026 Amelí. Todos los derechos reservados."))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn("© 2026 Amelí. Todos los derechos reservados.", contenido)

    def test_informacion_servicio_se_omite_si_null(self):
        # Mismo motivo que test_datos_legales_se_omiten_si_null: el
        # comentario que explica el mecanismo menciona el nombre de la
        # sección aunque el bloque en sí esté ausente.
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        sin_comentarios = re.sub(r"<!--.*?-->", "", contenido, flags=re.S)
        self.assertNotIn("Información del servicio", sin_comentarios)

    def test_informacion_servicio_no_se_duplica_en_portada(self):
        self.escribir_config(config_valido(
            informacion_servicio="Reglas reales aprobadas por Ignacio."))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        sin_comentarios = re.sub(r"<!--.*?-->", "", contenido, flags=re.S)
        self.assertNotIn("Reglas reales aprobadas por Ignacio.", contenido)
        self.assertNotIn("Información del servicio", sin_comentarios)

    def test_servicios_se_omite_por_defecto(self):
        """'Servicios Amelí' es contenido en BORRADOR -- nombres, alcance
        y textos todavía sin confirmar con Ignacio -- oculto a propósito
        (servicios_habilitado=false) hasta que se confirme. A diferencia
        de los otros bloques opcionales, acá el propio comentario
        explicativo (que menciona "BORRADOR") queda adentro de
        SERVICIOS_START/END, así que con el mecanismo apagado no debe
        sobrevivir ni siquiera dentro de un comentario HTML."""
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("BORRADOR", contenido)
        self.assertNotIn("Servicios Amelí", contenido)
        self.assertNotIn('class="servicios"', contenido)
        self.assertNotIn('class="servicio-card"', contenido)
        for nombre_no_confirmado in (
            "Amelí Eventos", "Amelí Catering", "Amelí Experiences",
            "Amelí Boxes", "Amelí Empresas", "Amelí Turismo",
        ):
            self.assertNotIn(nombre_no_confirmado, contenido)

    def test_servicios_se_incluye_si_esta_habilitado(self):
        """Las seis categorías confirmadas se agrupan en tres rutas y
        comparten una única llamada a la acción."""
        self.escribir_config(config_valido(servicios_habilitado=True))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn("Experiencias y encuentros", contenido)
        self.assertIn('class="servicios arquitectura-bloque"', contenido)
        for categoria in ("Experiencias", "Eventos", "Catering", "Boxes", "Turismo", "Empresas"):
            self.assertIn(f"<li>{categoria}</li>", contenido)
        self.assertEqual(contenido.count("Contanos qué estás organizando"), 1)
        self.assertNotIn('id="empresas"', contenido)
        self.assertNotIn('id="turismo"', contenido)

    def test_secciones_esenciales_siguen_presentes_con_servicios_oculta(self):
        """Ocultar las experiencias no debe afectar a portada,
        historia, ubicación/contacto ni el acceso al menú
        del salón."""
        self.escribir_config(config_valido(
            presentacion_sobre_ameli="Texto real ya confirmado."))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn("Nuestra historia", contenido)
        self.assertIn("Ver el menú", contenido)
        self.assertRegex(contenido, r'<section[^>]+id="filosofia"')
        self.assertRegex(contenido, r'<section[^>]+id="ubicacion"')
        self.assertRegex(contenido, r'<section[^>]+id="contacto"')
        self.assertIn('class="consultas-directorio', contenido)
        self.assertNotIn("Servicios Amelí", contenido)

    def test_secciones_nuevas_se_omiten_si_null(self):
        """Pastelería y pedidos especiales / Preguntas frecuentes --
        sin texto real todavía: no se inventó contenido, así que con la
        config por defecto (null) ninguna de las dos debe aparecer."""
        self.escribir_config(config_valido(pasteleria_pedidos_texto=None, preguntas_frecuentes_texto=None))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        sin_comentarios = re.sub(r"<!--.*?-->", "", contenido, flags=re.S)
        self.assertNotIn("Pastelería y pedidos especiales", sin_comentarios)
        self.assertNotIn("Preguntas frecuentes", sin_comentarios)
        self.assertNotIn('id="pasteleria-pedidos"', contenido)
        self.assertNotIn('id="preguntas-frecuentes"', contenido)

    def test_secciones_nuevas_se_incluyen_con_texto_real(self):
        self.escribir_config(config_valido(
            pasteleria_pedidos_texto="Texto real de pastelería.",
            preguntas_frecuentes_texto="Texto real de preguntas frecuentes."))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn("Texto real de pastelería.", contenido)
        self.assertIn("Texto real de preguntas frecuentes.", contenido)
        self.assertIn('id="tienda"', contenido)
        self.assertIn('id="preguntas-frecuentes"', contenido)

    def test_la_experiencia_no_existe_mas(self):
        """La sección genérica 'La experiencia' se retiró: no forma
        parte de la estructura literal de 11 secciones pedida por
        Ignacio (bocetos 2026-09-14) y duplicaba el número de índice
        '03' con Eventos & Catering."""
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('id="la-experiencia"', contenido)
        self.assertNotIn('class="la-experiencia"', contenido)

    def test_sustentabilidad_texto_se_renderiza_cuando_esta_habilitada(self):
        """El párrafo de cierre de Origen & Sustentabilidad ahora viene
        de site.config.json (antes quedaba fijo en el template y el
        valor de sustentabilidad_texto nunca se mostraba)."""
        self.escribir_config(config_valido(
            sustentabilidad_texto="Texto real de sustentabilidad, a validar."))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn("Texto real de sustentabilidad, a validar.", contenido)

    def test_numeracion_de_secciones_no_se_repite(self):
        """Cada 'indice-num' visible en el documento (fuera de
        comentarios) debe ser único -- ver bug corregido 2026-09-14
        donde '03', '07' y '08' aparecían duplicados tras sumar la
        arquitectura comercial ampliada."""
        self.escribir_config(config_valido(servicios_habilitado=True))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        sin_comentarios = re.sub(r"<!--.*?-->", "", contenido, flags=re.S)
        numeros = re.findall(r'class="indice-num"[^>]*>(\d+)<', sin_comentarios)
        self.assertEqual(len(numeros), len(set(numeros)), f"números repetidos en {numeros}")

    def test_identificacion_legal_ausente_por_defecto(self):
        """Ningún dato legal está confirmado hoy (todos null en
        site.config.json) -- la sección entera no debe aparecer, ni su
        <dl>, ni ningún campo individual."""
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('class="identificacion-legal', contenido)
        self.assertNotIn('class="lista-legal"', contenido)

    def test_identificacion_legal_parcial_no_crea_paginas_ni_bloques(self):
        """Un dato legal aislado no crea una ficha pública incompleta."""
        self.escribir_config(config_valido(responsable_reclamos="Ignacio Soto Iturbe"))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('class="identificacion-legal', contenido)
        self.assertFalse((build_site.DIST_PATH / "terminos.html").exists())
        self.assertFalse((build_site.DIST_PATH / "arrepentimiento.html").exists())

    def test_identidad_completa_genera_paquete_legal_enlazado(self):
        self.escribir_config(config_valido(
            razon_social="SOTO ITURBE MARTINA ORIANA",
            cuit="27-42862121-8",
            domicilio_comercial="Villegas Oeste 48, Malargüe, Mendoza",
            domicilio_legal="Villa del Milagro 1045, Malargüe, Mendoza, 5613",
            condicion_fiscal="Monotributista — categoría C",
            responsable_reclamos="Martina Oriana Soto Iturbe",
        ))
        build_site.construir(produccion=False)
        index = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        for nombre in (
            "terminos.html", "informacion-alimentaria.html", "arrepentimiento.html"
        ):
            self.assertTrue((build_site.DIST_PATH / nombre).is_file())
            self.assertIn(f'href="{nombre}"', index)
            contenido = (build_site.DIST_PATH / nombre).read_text(encoding="utf-8")
            self.assertIn('name="robots" content="noindex, nofollow"', contenido)
            self.assertEqual(build_site._escanear_placeholders_restantes(contenido), [])
        terminos = (build_site.DIST_PATH / "terminos.html").read_text(encoding="utf-8")
        self.assertIn("27-42862121-8", terminos)
        self.assertIn("50 %", terminos)
        self.assertIn("48 horas", terminos)

    def test_calendario_google_ausente_sin_url(self):
        self.escribir_config(config_valido(servicios_habilitado=True))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("Ver disponibilidad en Google Calendar", contenido)
        # el CTA de WhatsApp para cotizar sigue presente igual
        self.assertIn("Contanos qué estás organizando", contenido)

    def test_calendario_google_aparece_solo_con_url_valida(self):
        self.escribir_config(config_valido(
            servicios_habilitado=True,
            google_calendar_url="https://calendar.google.com/calendar/u/0/appointments/algo"))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn("Ver disponibilidad en Google Calendar", contenido)
        self.assertIn("https://calendar.google.com/calendar/u/0/appointments/algo", contenido)

    def test_calendario_google_rechaza_dominio_no_permitido(self):
        errores = build_site.validar_config(
            config_valido(google_calendar_url="https://evil.com/calendar"), requiere_site_url=False)
        self.assertTrue(any("google_calendar_url" in e for e in errores))

    def test_sumate_se_oculta_completo_sin_urls(self):
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('id="sumate"', contenido)
        self.assertNotIn('href="#sumate"', contenido)
        self.assertNotIn("Formulario en preparación", contenido)
        self.assertNotIn("Completar formulario", contenido)

    def test_formularios_sumate_usan_enlace_real_cuando_esta_cargado(self):
        self.escribir_config(config_valido(
            google_form_trabajo_url="https://docs.google.com/forms/d/e/algo/viewform"))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn("Completar formulario", contenido)
        self.assertIn("https://docs.google.com/forms/d/e/algo/viewform", contenido)
        # la otra pestaña (marcas), sin url cargada, sigue con el botón inactivo
        self.assertEqual(contenido.count("Formulario en preparación"), 1)
        self.assertNotIn("<form", contenido)  # sigue sin ningún <form> real

    def test_no_publica_aviso_interno_de_arrepentimiento(self):
        """Una nota de implementación pendiente no debe mostrarse como
        contenido público mientras no exista venta online en el sitio."""
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('id="arrepentimiento"', contenido)
        self.assertNotIn("PENDIENTE DE HABILITACIÓN", contenido)

    def test_ninguna_afirmacion_ambiental_o_de_alergenos_sin_respaldo(self):
        """Frases prohibidas por el bloque legal 2026-09-14 salvo
        respaldo verificable -- no deben aparecer en ningún lado del
        HTML generado."""
        self.escribir_config(config_valido(servicios_habilitado=True))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        for frase in (
            "Sin TACC", "Libre de", "100% biodegradable", "Orgánico",
            "Artesanal certificado", "Detox",
        ):
            self.assertNotIn(frase, contenido)

    def test_instagram_visitarnos_y_consultas_tienen_orden_y_funcion_propios(self):
        """Instagram va primero; llegar y escribir no se mezclan."""
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertRegex(contenido, r'<section[^>]+id="ubicacion"')
        self.assertRegex(contenido, r'<section[^>]+id="contacto"')
        self.assertIn('class="consultas-directorio', contenido)
        self.assertLess(contenido.index('id="instagram"'), contenido.index('id="ubicacion"'))
        self.assertLess(contenido.index('id="ubicacion"'), contenido.index('id="contacto"'))
        self.assertIn('id="titulo-ubicacion">Encontranos en Malargüe</h2>', contenido)
        self.assertNotIn("Vení a encontrarnos", contenido)
        self.assertNotIn('id="encontranos"', contenido)
        # Los 3 enlaces de mapa, calculados desde la misma dirección,
        # nunca inventados -- ver build_site.py.
        self.assertIn("Google Maps", contenido)
        self.assertIn("Apple Maps", contenido)
        self.assertIn("Waze", contenido)
        self.assertIn("https://maps.apple.com/?q=", contenido)
        self.assertIn("https://waze.com/ul?q=", contenido)

    def test_placeholder_sin_reemplazar_hace_fallar_build(self):
        plantilla = build_site.TEMPLATE_INDEX_PATH.read_text(encoding="utf-8")
        plantilla += "\n<!-- __ALGO_NUEVO_SIN_REEMPLAZAR__ -->"
        build_site.TEMPLATE_INDEX_PATH.write_text(plantilla, encoding="utf-8")
        with self.assertRaises(SystemExit):
            build_site.construir(produccion=False)

    def test_placeholder_sin_reemplazar_hace_fallar_build_en_404(self):
        plantilla = build_site.TEMPLATE_404_PATH.read_text(encoding="utf-8")
        plantilla += "\n<!-- __ALGO_NUEVO_SIN_REEMPLAZAR__ -->"
        build_site.TEMPLATE_404_PATH.write_text(plantilla, encoding="utf-8")
        with self.assertRaises(SystemExit):
            build_site.construir(produccion=False)
        # ni siquiera dist/ debería haberse creado -- el 404 se renderiza
        # antes de tocar el sistema de archivos de dist/.
        self.assertFalse(build_site.DIST_PATH.exists())

    def test_build_que_falla_no_reemplaza_dist_valido(self):
        # 1) build válido -- dist/ queda con contenido conocido.
        build_site.construir(produccion=False)
        manifiesto_antes = self._manifiesto_dist()

        # 2) se cuela un archivo no permitido en el origen de assets --
        # tiene que hacer fallar la allowlist DESPUÉS de armar el
        # staging, antes de reemplazar dist/.
        archivo_intruso = build_site.ASSETS_SRC / "css" / "no_deberia_estar.py"
        archivo_intruso.write_text("# esto no debe llegar nunca a dist/", encoding="utf-8")
        try:
            with self.assertRaises(SystemExit):
                build_site.construir(produccion=False)
        finally:
            archivo_intruso.unlink()

        # 3) dist/ tiene que seguir siendo EXACTAMENTE lo del build
        #    válido anterior -- nunca a medias, nunca con el intruso.
        self.assertEqual(self._manifiesto_dist(), manifiesto_antes)

        # y no debe quedar ningún directorio de staging huérfano.
        restos = [p for p in self.sandbox.glob(".build-tmp-*")]
        self.assertEqual(restos, [])

    def test_contenido_esencial_y_boton_a11y_seguros_sin_javascript(self):
        """Confirma, sin ejecutar ningún JavaScript (solo leyendo el
        HTML/CSS crudo tal como sale de dist/), que: (1) el contenido
        esencial ya está en el HTML servido, no depende de que corra un
        script para existir; (2) el botón de accesibilidad arranca
        marcado como pendiente; (3) el propio site.css lo oculta de
        verdad mientras esté pendiente -- sin esto, el atributo por sí
        solo no protegería nada; (4) borrar el <script> del documento
        entero no hace desaparecer ningún enlace esencial."""
        build_site.construir(produccion=False)
        html_crudo = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")

        # 1) contenido esencial presente directamente en el HTML.
        self.assertIn("wa.me/5492604106653", html_crudo)
        self.assertIn("instagram.com/ameli.casadete", html_crudo)
        self.assertIn(CONFIG_VALIDO["menu_url"], html_crudo)

        # 2) el botón de accesibilidad arranca marcado como pendiente.
        self.assertRegex(html_crudo, r'id="a11yBtn"[^>]*data-a11y-pending')

        # 3) site.css real oculta ese botón mientras esté pendiente.
        css = (build_site.DIST_PATH / "assets" / "css" / "site.css").read_text(encoding="utf-8")
        self.assertIn("[data-a11y-pending]", css)
        self.assertIn("visibility:hidden", css.replace(" ", ""))

        # 4) sin el <script>, el contenido esencial sigue en el
        #    documento -- nada esencial depende de JS para EXISTIR.
        sin_script = re.sub(r"<script[^>]*>.*?</script>", "", html_crudo, flags=re.S)
        self.assertIn("wa.me/5492604106653", sin_script)
        self.assertIn(CONFIG_VALIDO["menu_url"], sin_script)

    def test_navegacion_principal_apunta_a_secciones_reales(self):
        """La navegación usa anclas reales a secciones que existen en
        el propio documento (no JS, no scroll-spy). Desde 2026-09-14
        vive adentro de #navPanel (menú de tres rayas) en vez de una
        barra siempre visible en el header -- ver #navBtn/site.js."""
        self.escribir_config(config_valido(
            presentacion_sobre_ameli="Texto real.", servicios_habilitado=True,
            pasteleria_pedidos_texto="Estructura de tienda.",
            sustentabilidad_texto="Estructura de origen.",
            preguntas_frecuentes_texto="Preguntas reales."))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn('aria-label="Navegación principal"', contenido)
        self.assertRegex(contenido, r'<button[^>]+id="navBtn"')
        self.assertRegex(contenido, r'<dialog[^>]+id="navPanel"')
        for ancla in (
            "contenido", "filosofia", "experiencias", "tienda",
            "sustentabilidad", "preguntas-frecuentes", "instagram", "ubicacion", "contacto",
        ):
            self.assertIn(f'href="#{ancla}"', contenido)
            self.assertRegex(contenido, rf'id="{ancla}"')
        for ancla_eliminada in ("turismo", "empresas", "sumate"):
            self.assertNotIn(f'href="#{ancla_eliminada}"', contenido)

    def test_mapa_de_arquitectura_comercial_queda_representado(self):
        self.escribir_config(config_valido(
            presentacion_sobre_ameli="Filosofía confirmada.",
            servicios_habilitado=True,
            pasteleria_pedidos_texto="Pedidos sujetos a confirmación.",
            sustentabilidad_texto="Texto prudente.",
            preguntas_frecuentes_texto="Consultas frecuentes."))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        for texto in (
            "Casa de Té &amp; Brunch",
            "Experiencias y encuentros", "Experiencias", "Eventos",
            "Catering", "Boxes", "Turismo", "Empresas",
            "Carta y pedidos", "Origen y compromiso", "Texto prudente.",
            "Ver el menú", "Encontranos en Malargüe", "Pedidos, entregas y consultas generales",
        ):
            self.assertIn(texto, contenido)
        self.assertNotIn('role="tablist"', contenido)
        self.assertNotIn("Dos unidades, una misma marca", contenido)
        self.assertNotIn("Salón &amp; Take Away", contenido)
        self.assertNotIn('id="turismo"', contenido)
        self.assertNotIn('id="empresas"', contenido)

    def test_pestanas_sumate_son_locales_y_navegables_por_teclado(self):
        self.escribir_config(config_valido(
            google_form_trabajo_url="https://docs.google.com/forms/d/e/trabajo/viewform",
            google_form_marcas_url="https://docs.google.com/forms/d/e/marcas/viewform"))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        js = (build_site.DIST_PATH / "assets" / "js" / "site.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("<form", contenido)
        self.assertIn('id="sumate"', contenido)
        self.assertIn('role="tablist"', contenido)
        self.assertIn('role="tabpanel"', contenido)
        self.assertIn("ArrowLeft", js)
        self.assertIn("ArrowRight", js)

    def test_enlaces_que_abren_otra_pestana_lo_anuncian(self):
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        enlaces = re.findall(
            r'<a\s[^>]*target="_blank"[^>]*>.*?</a>', contenido, flags=re.S
        )
        self.assertGreater(len(enlaces), 0)
        for enlace in enlaces:
            self.assertIn("se abre en una pestaña nueva", enlace)

    def test_informacion_practica_usa_semantica_address(self):
        """La lista de consultas vive dentro de un
        <address> real -- no un <div> genérico -- y el CSS resetea el
        font-style:italic que el navegador le aplica por defecto."""
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        bloque = re.search(r'<address[^>]*>.*?</address>', contenido, flags=re.S)
        self.assertIsNotNone(bloque)
        self.assertIn('consultas-grid', bloque.group(0))
        self.assertIn('WhatsApp', bloque.group(0))

        css = (build_site.DIST_PATH / "assets" / "css" / "site.css").read_text(
            encoding="utf-8"
        ).replace(" ", "").replace("\n", "")
        self.assertRegex(css, r"\.consultas-grid\{[^}]*font-style:normal")

    def test_fotografias_reales_tienen_atributos_completos_y_mapa_sigue_reservado(self):
        """Portada, Carta y pedidos, Origen y compromiso, y las 4 fotos de
        Instagram ya son <img> reales (fotos propias incorporadas el
        2026-09-16) -- cada una con ancho/alto (evita saltos de layout),
        srcset+sizes (responsive) y alt no vacío con texto real (no son
        decorativas). El mapa sigue sin foto ni embed, por diseño."""
        self.escribir_config(config_valido(
            presentacion_sobre_ameli="Filosofía confirmada.",
            servicios_habilitado=True,
            pasteleria_pedidos_texto="Pedidos sujetos a confirmación.",
            sustentabilidad_texto="Texto prudente.",
            preguntas_frecuentes_texto="Consultas frecuentes."))
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        imgs = re.findall(r'<img\b[^>]*>', contenido)
        clases_con_foto = (
            "portada-hero-fondo", "espacio-tienda", "espacio-sustentabilidad",
            "espacio-instagram",
        )
        for clase in clases_con_foto:
            etiquetas = [img for img in imgs if f'class="{clase}"' in img or f' {clase}"' in img or f'"{clase} ' in img]
            self.assertTrue(etiquetas, f"no se encontró <img> con la clase {clase}")
            for etiqueta in etiquetas:
                self.assertRegex(etiqueta, r'\balt="[^"]+"')
                self.assertNotRegex(etiqueta, r'alt=""')
                self.assertRegex(etiqueta, r'\bwidth="\d+"')
                self.assertRegex(etiqueta, r'\bheight="\d+"')
                self.assertIn("srcset=", etiqueta)
                self.assertIn("sizes=", etiqueta)
                self.assertIn(".webp", etiqueta)
        # La foto de portada es la única que NO debe ser lazy (LCP).
        portada_img = next(img for img in imgs if "portada-hero-fondo" in img)
        self.assertNotIn('loading="lazy"', portada_img)
        self.assertIn('loading="eager"', portada_img)
        # El resto de las fotos sí son lazy.
        for img in imgs:
            if "portada-hero-fondo" not in img and ("espacio-tienda" in img or "espacio-sustentabilidad" in img or "espacio-instagram" in img):
                self.assertIn('loading="lazy"', img)
        self.assertIn("espacio-mapa", contenido)
        self.assertNotRegex(contenido, r'<img\b[^>]*espacio-mapa')
        plantilla = build_site.TEMPLATE_INDEX_PATH.read_text(encoding="utf-8")
        self.assertNotIn("espacio-turismo", plantilla)

    def test_acceso_al_menu_del_salon_esta_en_html_sin_js(self):
        build_site.construir(produccion=False)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        sin_script = re.sub(r"<script[^>]*>.*?</script>", "", contenido, flags=re.S)
        self.assertIn("Ver el menú", sin_script)
        self.assertIn(CONFIG_VALIDO["menu_url"], sin_script)
        self.assertIn("Sin publicidad ni seguimiento", sin_script)

    def test_metadatos_sociales_solo_aparecen_en_produccion(self):
        build_site.construir(produccion=False)
        preview = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('property="og:', preview)
        self.assertNotIn('name="twitter:', preview)

        build_site.construir(produccion=True)
        produccion = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn('property="og:type" content="website"', produccion)
        self.assertIn('property="og:locale" content="es_AR"', produccion)
        self.assertIn('property="og:url" content="https://amelicasadete.com.ar/"', produccion)
        self.assertIn('name="twitter:card" content="summary"', produccion)
        self.assertNotIn('property="og:image"', produccion)

    def test_controles_del_panel_tienen_objetivo_tactil_minimo(self):
        # 48px, no 44px: piso más estricto que el mínimo WCAG (24px en
        # 2.2, 44px en el criterio AAA) pedido explícitamente para el
        # cierre operativo.
        build_site.construir(produccion=False)
        css = (build_site.DIST_PATH / "assets" / "css" / "site.css").read_text(
            encoding="utf-8"
        ).replace(" ", "").replace("\n", "")
        self.assertRegex(css, r"\.a11y-btn\{[^}]*width:48px;height:48px")
        self.assertRegex(css, r"\.a11y-cerrar\{[^}]*width:48px;height:48px")
        self.assertNotIn("44px", css)

    def test_objetivos_tactiles_minimos_en_todo_el_sitio(self):
        """Barrido general -- todo min-height/min-width/width+height de
        controles interactivos declarado en el CSS tiene que ser >=48px,
        no solo los dos casos puntuales de arriba."""
        build_site.construir(produccion=False)
        css = (build_site.DIST_PATH / "assets" / "css" / "site.css").read_text(encoding="utf-8")
        # Única excepción conocida y deliberada: el <input type=checkbox>
        # visual del switch de accesibilidad mide 20x20px, pero el
        # objetivo táctil real es toda la fila <label class="a11y-switch">
        # que lo contiene (esa sí en 48px, ver test de arriba en el
        # propio .a11y-switch). El input chico es el dibujo del
        # interruptor, no un control táctil aparte.
        css_sin_excepcion = re.sub(
            r"\.a11y-switch input\{[^}]*\}", "", css)
        for match in re.finditer(r"(?:min-height|min-width|height|width)\s*:\s*(\d+)px", css_sin_excepcion):
            valor = int(match.group(1))
            # Solo interesan valores en el rango típico de un objetivo
            # táctil (excluye anchos/altos grandes de layout, imágenes,
            # etc. que no son controles interactivos).
            if 20 <= valor <= 43:
                self.fail(f"posible objetivo táctil por debajo de 48px: {match.group(0)!r}")


class TestEnlacesYRecursosSeguros(SandboxConstruirTestCase):
    """Escaneo explícito de todo lo que build_site.py genera, buscando
    esquemas o destinos que nunca deberían aparecer -- independiente de
    que hoy el propio config no los produzca; esto es una red de
    seguridad contra un cambio futuro que sí lo haga."""

    ESQUEMAS_PROHIBIDOS = ("http://", "//", "javascript:", "data:", "ftp:")

    def _hrefs(self, html_texto):
        return re.findall(r'href="([^"]*)"', html_texto)

    def test_ningun_href_usa_esquema_inseguro(self):
        build_site.construir(produccion=False)
        for nombre in ("index.html", "404.html", "privacidad.html"):
            contenido = (build_site.DIST_PATH / nombre).read_text(encoding="utf-8")
            for href in self._hrefs(contenido):
                if href.startswith("#"):
                    continue  # anclas internas, siempre seguras
                if href.startswith("mailto:"):
                    destino = href[len("mailto:"):].split("?", 1)[0]
                    self.assertEqual(destino, CONFIG_VALIDO["contacto_email"])
                    continue
                for prohibido in self.ESQUEMAS_PROHIBIDOS:
                    self.assertFalse(
                        href.startswith(prohibido),
                        msg=f"href inseguro en {nombre}: {href!r} (esquema {prohibido!r})",
                    )
                if href.startswith("https://"):
                    # ninguna URL absoluta debe llevar credenciales
                    # embebidas ("usuario[:clave]@host").
                    resto = href[len("https://"):]
                    self.assertNotIn("@", resto.split("/")[0])
                else:
                    # todo lo que no es "https://...", tiene que ser una
                    # referencia relativa propia del sitio (mismo
                    # archivo, un ancla, o -- desde la unificación en un
                    # único artefacto de GitHub Pages -- la ruta interna
                    # exacta del menú), nunca otra cosa.
                    self.assertTrue(
                        href in ("index.html", "privacidad.html")
                        or href.startswith("assets/")
                        or href == build_site.RUTA_MENU_INTERNA,
                        msg=f"href inesperado (ni https:// ni relativo propio) en {nombre}: {href!r}",
                    )

    def test_recursos_cargados_son_de_origen_propio(self):
        """A diferencia de los <a href>, que sí pueden apuntar afuera
        (son navegación, no carga de recursos), ningún <link>, <script
        src>, <img src> ni url() de CSS debe ser absoluto a otro
        origen -- eso sería una petición de red no documentada."""
        build_site.construir(produccion=False)
        for nombre in ("index.html", "404.html", "privacidad.html"):
            contenido = (build_site.DIST_PATH / nombre).read_text(encoding="utf-8")
            recursos = (
                re.findall(r'<link[^>]+href="([^"]*)"', contenido)
                + re.findall(r'<script[^>]+src="([^"]*)"', contenido)
                + re.findall(r'<img[^>]+src="([^"]*)"', contenido)
            )
            for recurso in recursos:
                self.assertFalse(recurso.startswith(("http://", "https://", "//")),
                                  msg=f"recurso externo inesperado en {nombre}: {recurso!r}")

        css = (build_site.DIST_PATH / "assets" / "css" / "site.css").read_text(encoding="utf-8")
        for url_valor in re.findall(r"url\(['\"]?([^'\")]+)['\"]?\)", css):
            self.assertFalse(url_valor.startswith(("http://", "https://", "//")),
                              msg=f"url() externa inesperada en site.css: {url_valor!r}")


class TestUrlRelativaAProtocolo(unittest.TestCase):
    """`//dominio` (URL relativa al esquema) hereda el esquema de la
    página que la usa -- en https, se resuelve como https://dominio,
    pero es un vector de confusión clásico (parece "relativa", en
    realidad apunta afuera) y debe rechazarse explícitamente, no solo
    por accidente de que el chequeo de esquema ya lo cubra."""

    def test_url_https_valida_la_rechaza(self):
        self.assertFalse(build_site._url_https_valida("//evil.com/x", build_site.DOMINIOS_GOOGLE))

    def test_site_url_valida_la_rechaza(self):
        self.assertFalse(build_site._site_url_valida("//amelicasadete.com.ar/"))


class TestConstruirSwapYRespaldo(SandboxConstruirTestCase):
    """Las 7 pruebas pedidas para el reemplazo de dist/ con respaldo y
    restauración automática. Ninguna toca el dist/ real -- todas corren
    sobre el sandbox aislado de SandboxConstruirTestCase."""

    def test_1_fallo_al_apartar_dist_anterior_no_toca_nada(self):
        build_site.construir(produccion=False)
        manifiesto_antes = self._manifiesto_dist()

        fake, llamadas = _renombrar_que_falla_en(1)
        with mock.patch.object(build_site, "_renombrar", fake):
            with self.assertRaises(SystemExit) as ctx:
                build_site.construir(produccion=False)

        self.assertEqual(len(llamadas), 1)
        self.assertIn("no debería haber cambiado", str(ctx.exception))
        self.assertTrue(build_site.DIST_PATH.is_dir())
        self.assertEqual(self._manifiesto_dist(), manifiesto_antes)
        self.assertEqual(list(self.sandbox.glob(".build-tmp-*")), [])
        self.assertEqual(list(self.sandbox.glob(".dist-respaldo-*")), [])

    def test_2_fallo_al_mover_staging_a_dist(self):
        build_site.construir(produccion=False)
        manifiesto_antes = self._manifiesto_dist()

        # llamada 1 = apartar dist -> respaldo (OK); llamada 2 = mover
        # staging -> dist (falla).
        fake, llamadas = _renombrar_que_falla_en(2)
        with mock.patch.object(build_site, "_renombrar", fake):
            with self.assertRaises(SystemExit) as ctx:
                build_site.construir(produccion=False)

        self.assertEqual(len(llamadas), 3)  # apartar, mover (falla), restaurar
        self.assertIn("se restauró", str(ctx.exception))

        # la restauración automática deja dist/ exactamente como estaba
        # -- la prueba dedicada a esto en detalle es test_3, acá solo se
        # confirma el caso base: falló el segundo rename y no se perdió
        # nada.
        self.assertEqual(self._manifiesto_dist(), manifiesto_antes)
        restos_staging = list(self.sandbox.glob(".build-tmp-*"))
        self.assertEqual(len(restos_staging), 1, "el staging fallido debe conservarse para inspección")
        self.assertEqual(list(self.sandbox.glob(".dist-respaldo-*")), [])
        shutil.rmtree(restos_staging[0], ignore_errors=True)  # limpieza del test

    def test_3_restauracion_correcta_del_anterior(self):
        self.escribir_config(config_valido(marca="Version Uno"))
        build_site.construir(produccion=False)
        manifiesto_antes = self._manifiesto_dist()

        self.escribir_config(config_valido(marca="Version Dos"))
        fake, llamadas = _renombrar_que_falla_en(2)
        with mock.patch.object(build_site, "_renombrar", fake):
            with self.assertRaises(SystemExit) as ctx:
                build_site.construir(produccion=False)

        self.assertIn("se restauró", str(ctx.exception))
        # dist/ sigue siendo exactamente la Versión Uno, byte a byte.
        self.assertEqual(self._manifiesto_dist(), manifiesto_antes)
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn("Version Uno", contenido)
        self.assertNotIn("Version Dos", contenido)

        shutil.rmtree(list(self.sandbox.glob(".build-tmp-*"))[0], ignore_errors=True)

    def test_4_fallo_durante_la_restauracion_conserva_evidencia(self):
        build_site.construir(produccion=False)
        manifiesto_antes = self._manifiesto_dist()

        # llamada 1 = apartar (OK); llamada 2 = mover a dist (falla);
        # llamada 3 = intentar restaurar el respaldo (también falla).
        fake, llamadas = _renombrar_que_falla_en({2, 3})
        with mock.patch.object(build_site, "_renombrar", fake):
            with self.assertRaises(SystemExit) as ctx:
                build_site.construir(produccion=False)

        mensaje = str(ctx.exception)
        self.assertIn("FALLO CRÍTICO", mensaje)

        # en este estado dist/ NO existe -- ambos renames fallaron.
        self.assertFalse(build_site.DIST_PATH.exists())
        respaldos = list(self.sandbox.glob(".dist-respaldo-*"))
        stagings = list(self.sandbox.glob(".build-tmp-*"))
        self.assertEqual(len(respaldos), 1)
        self.assertEqual(len(stagings), 1)
        # el mensaje de error tiene que nombrar las dos rutas exactas
        # para que se puedan resolver a mano.
        self.assertIn(str(respaldos[0]), mensaje)
        self.assertIn(str(stagings[0]), mensaje)

        # recuperación manual, siguiendo exactamente lo que diría el
        # mensaje de error a un humano -- confirma que la evidencia
        # dejada alcanza para reparar el estado sin pérdida.
        respaldos[0].rename(build_site.DIST_PATH)
        shutil.rmtree(stagings[0], ignore_errors=True)
        self.assertEqual(self._manifiesto_dist(), manifiesto_antes)

    def test_5_respaldo_residual_bloquea_build_nuevo(self):
        build_site.construir(produccion=False)
        residual = self.sandbox / ".dist-respaldo-999999-0"
        residual.mkdir()
        try:
            with self.assertRaises(SystemExit) as ctx:
                build_site.construir(produccion=False)
            self.assertIn(str(residual), str(ctx.exception))
        finally:
            shutil.rmtree(residual, ignore_errors=True)

    def test_6_fallo_de_limpieza_del_respaldo_no_pierde_el_dist_nuevo(self):
        self.escribir_config(config_valido(marca="Version Uno"))
        build_site.construir(produccion=False)

        self.escribir_config(config_valido(marca="Version Dos"))

        rmtree_real = shutil.rmtree

        def rmtree_selectivo(ruta, *args, **kwargs):
            if ".dist-respaldo-" in str(ruta):
                raise OSError("fallo simulado al limpiar el respaldo")
            return rmtree_real(ruta, *args, **kwargs)

        captura = io.StringIO()
        with mock.patch("build_site.shutil.rmtree", side_effect=rmtree_selectivo):
            with contextlib.redirect_stdout(captura):
                resumen = build_site.construir(produccion=False)  # no debe levantar

        self.assertEqual(resumen["modo"], "preview")
        contenido = (build_site.DIST_PATH / "index.html").read_text(encoding="utf-8")
        self.assertIn("Version Dos", contenido)
        self.assertIn("[ADVERTENCIA]", captura.getvalue())

        respaldos = list(self.sandbox.glob(".dist-respaldo-*"))
        self.assertEqual(len(respaldos), 1, "el respaldo debe conservarse cuando falla su limpieza")
        shutil.rmtree(respaldos[0], ignore_errors=True)

    def test_7_build_exitoso_no_deja_respaldo_ni_staging_ni_advertencias(self):
        captura = io.StringIO()
        with contextlib.redirect_stdout(captura):
            resumen = build_site.construir(produccion=False)

        self.assertEqual(resumen["modo"], "preview")
        self.assertTrue(build_site.DIST_PATH.is_dir())
        self.assertEqual(list(self.sandbox.glob(".dist-respaldo-*")), [])
        self.assertEqual(list(self.sandbox.glob(".build-tmp-*")), [])
        self.assertNotIn("ADVERTENCIA", captura.getvalue())
        self.assertNotIn("FALLO", captura.getvalue())


if __name__ == "__main__":
    unittest.main()
