"""Pruebas de assets/js/menu.js para el carrusel de destacados (.dcard).

No hay Selenium/Playwright en este proyecto (ver requirements.txt: la
única dependencia real es openpyxl, y CI no instala nada más) -- así que,
igual que los tests de objetivos táctiles en web/tests/test_build_site.py,
estas pruebas son estáticas: leen assets/js/menu.js de verdad y verifican,
con expresiones regulares, las propiedades estructurales que hacen que el
comportamiento en el navegador sea correcto. Se agregaron después de un
bug real: las tarjetas del carrusel (role="button", anuncian "Ver detalle
de...") no abrían la ficha con clic de mouse real, porque
car.setPointerCapture(e.pointerId) se llamaba en el primer pointerdown de
CUALQUIER clic dentro de #carrusel -- eso retargetea el click/mouseup
subsiguiente al contenedor (#carrusel) en vez de a la tarjeta, así que el
listener de .dcard nunca se disparaba. El fix agrega un umbral de
movimiento antes de capturar el puntero (mismo criterio de histéresis que
pide /apple-design) y ata los listeners de bajo nivel del carrusel una
sola vez (initCarrusel() se llama en cada render(), pero el contenedor
#carrusel no se recrea -- solo su innerHTML)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MENU_JS = ROOT / "assets" / "js" / "menu.js"


class TestTarjetasCarruselAbrenFicha(unittest.TestCase):
    def setUp(self):
        self.js = MENU_JS.read_text(encoding="utf-8")

    def test_dcard_tiene_listener_de_click_que_reusa_abrirdetalle(self):
        self.assertRegex(
            self.js,
            r"card\.addEventListener\('click',\s*\(\)\s*=>\s*abrirDetalle\(card\.dataset\.id\)\)",
            "las tarjetas .dcard deben abrir el detalle reusando abrirDetalle(), "
            "no una función paralela",
        )

    def test_dcard_tiene_listener_de_teclado_para_enter_y_espacio(self):
        match = re.search(
            r"document\.querySelectorAll\('\.dcard'\)\.forEach\(card=>\{(.*?)\}\);",
            self.js, re.S,
        )
        self.assertIsNotNone(match, "no se encontró el bloque que ata listeners a .dcard")
        bloque = match.group(1)
        self.assertIn("card.addEventListener('keydown'", bloque)
        self.assertIn("e.key==='Enter'", bloque)
        self.assertIn("e.key===' '", bloque)
        self.assertIn("abrirDetalle(card.dataset.id)", bloque)

    def test_un_solo_lugar_ata_listeners_a_las_tarjetas_del_carrusel(self):
        """No deben existir listeners duplicados: el bloque que recorre
        '.dcard' y ata click/keydown aparece exactamente una vez en todo
        el archivo (el carrusel y las secciones de categoría comparten la
        misma clase .prod para sus propias tarjetas, con su propio bloque
        separado -- .dcard es exclusivo del carrusel)."""
        apariciones = self.js.count("document.querySelectorAll('.dcard').forEach(card=>{")
        self.assertEqual(apariciones, 1)

    def test_pointer_capture_no_se_llama_en_el_primer_pointerdown(self):
        """Causa raíz del bug: capturar el puntero apenas baja el dedo/
        clic (sin umbral de movimiento) hace que el click de un tap
        simple sobre una tarjeta se retargetee al contenedor #carrusel en
        vez de llegar a la tarjeta. setPointerCapture solo puede aparecer
        después de comprobar el umbral de arrastre, nunca dentro del
        cuerpo del primer handler de pointerdown."""
        match = re.search(
            r"car\.addEventListener\('pointerdown',\s*e=>\{(.*?)\}\);",
            self.js, re.S,
        )
        self.assertIsNotNone(match, "no se encontró el handler de pointerdown del carrusel")
        cuerpo_pointerdown = match.group(1)
        self.assertNotIn("setPointerCapture", cuerpo_pointerdown)

    def test_umbral_de_arrastre_antes_de_capturar_el_puntero(self):
        self.assertIn("UMBRAL_ARRASTRE", self.js)
        match = re.search(
            r"car\.addEventListener\('pointermove',\s*e=>\{(.*?)\}\);",
            self.js, re.S,
        )
        self.assertIsNotNone(match, "no se encontró el handler de pointermove del carrusel")
        cuerpo = match.group(1)
        idx_umbral = cuerpo.find("UMBRAL_ARRASTRE")
        idx_captura = cuerpo.find("setPointerCapture")
        self.assertNotEqual(idx_umbral, -1)
        self.assertNotEqual(idx_captura, -1)
        self.assertLess(
            idx_umbral, idx_captura,
            "setPointerCapture debe llamarse después de comprobar el umbral, no antes",
        )

    def test_listeners_de_bajo_nivel_del_carrusel_se_atan_una_sola_vez(self):
        """initCarrusel() se invoca en cada render() (cambio de idioma,
        chip de mood, limpiar filtro), pero el contenedor #carrusel
        persiste entre renders -- solo se le reemplaza el innerHTML. Sin
        una guarda, cada render() volvería a atar scroll/pointerdown/
        pointermove/pointerup/pointercancel/pointerleave sobre el mismo
        elemento, acumulando listeners duplicados para siempre."""
        idx_guarda = self.js.find("if(car.dataset.dragInit) return;")
        idx_pointerdown = self.js.find("car.addEventListener('pointerdown'")
        self.assertNotEqual(idx_guarda, -1, "falta la guarda contra listeners duplicados")
        self.assertNotEqual(idx_pointerdown, -1)
        self.assertLess(
            idx_guarda, idx_pointerdown,
            "la guarda debe ejecutarse antes de atar los listeners del carrusel",
        )
        self.assertIn("car.dataset.dragInit='1'", self.js)

    def test_arrastre_real_descarta_el_click_siguiente_sin_bloquear_el_tap_simple(self):
        """Un arrastre real (para scrollear el carrusel con mouse) no debe
        abrir la ficha del producto bajo el puntero al soltar; un tap
        simple sin movimiento sí debe abrirla -- por eso el descarte de
        click vive dentro de terminarArrastre() y solo se agrega cuando
        arrastrando ya es true, nunca de forma incondicional."""
        match = re.search(
            r"function terminarArrastre\(\)\{(.*?)\n\s*\}\n\s*car\.addEventListener\('pointerup'",
            self.js, re.S,
        )
        self.assertIsNotNone(match, "no se encontró terminarArrastre()")
        cuerpo = match.group(1)
        self.assertIn("if(!arrastrando) return;", cuerpo)
        self.assertIn("descartarClick", cuerpo)
        self.assertIn("capture:true, once:true", cuerpo)


class TestCarruselMuestraCuatroSinTruncar(unittest.TestCase):
    """Puntos 5 y 8 de la ronda de unificación visual: el carrusel muestra
    4 destacados (no 7) en el orden actual, sin inventar ni reordenar
    productos, y sus tarjetas muestran categoría + nombre + precio en vez
    de una descripción cortada con -webkit-line-clamp."""

    def setUp(self):
        self.js = MENU_JS.read_text(encoding="utf-8")

    def test_recorta_a_cuatro_en_el_orden_actual_sin_reordenar(self):
        match = re.search(
            r"const MAX_DESTACADOS_CARRUSEL\s*=\s*(\d+);", self.js,
        )
        self.assertIsNotNone(match, "falta la constante MAX_DESTACADOS_CARRUSEL")
        self.assertEqual(match.group(1), "4")
        self.assertRegex(
            self.js,
            r"PRODS\.filter\(p=>p\.dest\)\.slice\(0,\s*MAX_DESTACADOS_CARRUSEL\)",
            "debe recortar con .slice(0, N) sobre el mismo filtro/orden existente, "
            "nunca .sort() ni una lista escrita a mano",
        )

    def test_tarjeta_no_incluye_la_descripcion_completa_del_producto(self):
        match = re.search(
            r"\$\('carrusel'\)\.innerHTML=PRODS\.filter.*?\}\)\.join\(''\);",
            self.js, re.S,
        )
        self.assertIsNotNone(match, "no se encontró el render del carrusel")
        bloque = match.group(0)
        # p.d[lang] es la descripción del producto -- no debe imprimirse acá
        # (sigue completa en la ficha, vía abrirDetalle -> $('sheetDesc')).
        self.assertNotIn("p.d[lang]", bloque)
        self.assertIn("dcard-cat", bloque)
        self.assertIn("PRECIOS[p.id]", bloque)

    def test_css_del_carrusel_ya_no_trunca_con_line_clamp(self):
        css = (ROOT / "assets" / "css" / "menu.css").read_text(encoding="utf-8")
        # busca la propiedad real (con ":"), no la mención en un comentario
        self.assertNotIn("-webkit-line-clamp:", css)

    def test_indicador_numerico_reemplaza_los_puntos_de_navegacion(self):
        self.assertIn("carIndicador", self.js)
        self.assertRegex(self.js, r"pad2\(idx\+1\).*pad2\(carruselCards\.length\)")
        self.assertNotIn("car-puntos", self.js)
        self.assertNotIn("carPuntos", self.js)


class TestFichaDeDetalleFoco(unittest.TestCase):
    """El resto de los requisitos de accesibilidad del punto 1 (Escape,
    botón cerrar, CTA Pedir, devolución de foco) ya existían antes de
    este fix y no se tocaron -- se verifican igual acá para que una
    futura regresión en esas partes quede cubierta."""

    def setUp(self):
        self.js = MENU_JS.read_text(encoding="utf-8")

    def test_escape_cierra_el_detalle(self):
        match = re.search(r"function onSheetKeydown\(e\)\{(.*?)\n\}", self.js, re.S)
        self.assertIsNotNone(match)
        self.assertIn("e.key==='Escape'", match.group(1))
        self.assertIn("cerrarDetalle()", match.group(1))

    def test_cerrar_devuelve_el_foco_al_elemento_previo(self):
        match = re.search(r"function cerrarDetalle\(\)\{(.*?)\n\}", self.js, re.S)
        self.assertIsNotNone(match)
        cuerpo = match.group(1)
        self.assertIn("focoPrevio && focoPrevio.focus", cuerpo)

    def test_abrir_guarda_el_elemento_activo_como_foco_previo(self):
        match = re.search(r"function abrirDetalle\(id\)\{(.*?)\n\}", self.js, re.S)
        self.assertIsNotNone(match)
        self.assertIn("focoPrevio = document.activeElement", match.group(1))


if __name__ == "__main__":
    unittest.main()
