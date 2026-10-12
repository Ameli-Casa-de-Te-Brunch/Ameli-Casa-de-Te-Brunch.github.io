#!/usr/bin/env python3
"""Descarga de una pestaña de Google Sheets "publicada en la web" (CSV), común
a build/aplicar_calendario.py y build/aplicar_precios.py.

Mismas restricciones que build/aplicar_disponibilidad.py: solo https de
docs.google.com, redirecciones únicamente a los dominios de Google, tope de
tamaño, y mensajes de error que nunca reproducen la URL (puede llevar el ID de
la planilla) ni el contenido de la hoja. Solo biblioteca estándar.
"""
import urllib.error
import urllib.request

import aplicar_disponibilidad as ad
import extract_common as ec

TAMANO_MAXIMO_BYTES = ad.TAMANO_MAXIMO_BYTES


def manejador_de_redirecciones(error_cls, nombre: str):
    """Clase de HTTPRedirectHandler que corta toda redirección fuera de los
    dominios permitidos levantando error_cls."""
    class _RedirectHandlerRestringido(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if not ec.url_https_valida(newurl, ad.DOMINIOS_REDIRECCION_PERMITIDOS):
                raise error_cls(f"La hoja {nombre} redirigió a un destino no permitido -- corto acá.")
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    return _RedirectHandlerRestringido


def descargar_csv(url: str, nombre: str, error_cls, timeout: int = 10) -> str:
    """Devuelve el CSV como texto. `nombre` (p. ej. "del calendario") solo se
    usa en los mensajes; `error_cls` es la excepción propia de cada módulo."""
    if not ec.url_https_valida(url, ec.DOMINIOS_DISPONIBILIDAD):
        raise error_cls(f"La URL {nombre} configurada no es https de docs.google.com -- no se descarga.")
    opener = urllib.request.build_opener(manejador_de_redirecciones(error_cls, nombre))
    try:
        with opener.open(url, timeout=timeout) as resp:
            crudo = resp.read(TAMANO_MAXIMO_BYTES + 1)
    except error_cls:
        raise
    except Exception as e:
        # Nunca str(e): algunos errores de urllib incluyen la URL completa.
        raise error_cls(f"No se pudo descargar la hoja {nombre} ({type(e).__name__}).") from None
    if len(crudo) > TAMANO_MAXIMO_BYTES:
        raise error_cls(f"La hoja {nombre} supera el máximo permitido ({TAMANO_MAXIMO_BYTES} bytes).")
    try:
        return crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise error_cls(f"La hoja {nombre} no es un CSV de texto en una codificación válida.") from None
