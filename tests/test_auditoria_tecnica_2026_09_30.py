"""Pruebas de assets/js/menu.js para los cuatro defectos técnicos
confirmados en la auditoría del 30/09/2026.

No hay Selenium/Playwright en este proyecto (ver requirements.txt: la
única dependencia real es openpyxl, y CI no instala nada más) -- así
que, igual que los tests de objetivos táctiles en
web/tests/test_build_site.py y los de tests/test_carrusel_destacados.py,
estas pruebas son estáticas: leen assets/js/menu.js y assets/css/menu.css
de verdad y verifican, con expresiones regulares, las propiedades
estructurales que hacen que el comportamiento en el navegador sea
correcto.

Los cuatro defectos:
1. Un producto oculto por el filtro (mood/búsqueda) solo se ocultaba
   con CSS (grid-template-rows:0fr + opacity:0) -- seguía alcanzable
   con Tab, clickeable si algo lo superponía, y presente en el árbol
   accesible. Fix: inert + aria-hidden + tabindex=-1 explícitos,
   restaurados a su estado original (tabindex=0) al volver a mostrarse.
2. Los botones de "momento" (chips) no anunciaban su estado activo/
   inactivo a un lector de pantalla -- sin aria-pressed.
3-4. El carrusel de destacados podía mostrar flechas activas y un
   indicador incoherente ("03 / 04" con scrollLeft=0) cuando las 4
   tarjetas ya entraban enteras en pantalla y no había nada para
   desplazar."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MENU_JS = ROOT / "assets" / "js" / "menu.js"
MENU_CSS = ROOT / "assets" / "css" / "menu.css"


class TestFiltroSacaProductosOcultosDeTodo(unittest.TestCase):
    """Punto 2 de la auditoría: un producto oculto por el filtro debe
    quedar fuera del foco, del puntero y del árbol accesible -- no solo
    invisible en pantalla."""

    def setUp(self):
        self.js = MENU_JS.read_text(encoding="utf-8")
        self.css = MENU_CSS.read_text(encoding="utf-8")
        match = re.search(r"function aplicarFiltro\(\)\{(.*?)\n\}", self.js, re.S)
        self.assertIsNotNone(match, "no se encontró aplicarFiltro()")
        self.cuerpo = match.group(1)

    def test_producto_oculto_recibe_inert_aria_hidden_y_tabindex_negativo(self):
        rama_oculto = re.search(r"\}\s*else\s*\{(.*?)\}", self.cuerpo, re.S)
        self.assertIsNotNone(rama_oculto, "no se encontró la rama 'else' (producto no visible)")
        cuerpo_else = rama_oculto.group(1)
        self.assertIn("setAttribute('inert','')", cuerpo_else)
        self.assertIn("setAttribute('aria-hidden','true')", cuerpo_else)
        self.assertIn("setAttribute('tabindex','-1')", cuerpo_else)

    def test_producto_visible_restaura_tabindex_original_no_inventado(self):
        rama_visible = re.search(r"if\(visible\)\{(.*?)\}\s*else", self.cuerpo, re.S)
        self.assertIsNotNone(rama_visible, "no se encontró la rama 'if(visible)'")
        cuerpo_if = rama_visible.group(1)
        self.assertIn("removeAttribute('inert')", cuerpo_if)
        self.assertIn("removeAttribute('aria-hidden')", cuerpo_if)
        # "0" es el tabindex real con el que renderCardCompacta/
        # renderDestacadoCategoria ya marcan estas tarjetas -- restaurar
        # cualquier otro valor sería inventar un dato que no viene del
        # markup original.
        self.assertIn("setAttribute('tabindex','0')", cuerpo_if)
        self.assertIn('tabindex="0"', self.js)

    def test_pointer_events_none_como_respaldo_visual_en_css(self):
        """inert ya bloquea el puntero por sí solo, pero se agrega
        pointer-events:none en la regla .prod.oculto como respaldo --
        no depender de un único mecanismo."""
        regla = re.search(r"\.prod\.oculto\{([^}]*)\}", self.css)
        self.assertIsNotNone(regla, "no se encontró la regla .prod.oculto")
        self.assertIn("pointer-events:none", regla.group(1))

    def test_categorias_sin_resultados_no_dejan_controles_ocultos_alcanzables(self):
        """La marca 'sin-resultados' de la sección sigue funcionando
        igual que antes (cuenta .prod:not(.oculto)), pero ahora cada uno
        de esos .prod ocultos individualmente ya quedó inert/tabindex=-1
        arriba -- no hace falta lógica aparte a nivel de sección."""
        self.assertIn("sin-resultados", self.cuerpo)
        self.assertIn(".prod:not(.oculto)", self.cuerpo)


class TestChipsAnuncianEstadoPresionado(unittest.TestCase):
    """Punto 3 de la auditoría: cada botón de "momento" debe llevar
    aria-pressed sincronizado con su estado visual (.activo), incluso
    después de cambiar de idioma, activar, desactivar o limpiar el
    filtro."""

    def setUp(self):
        self.js = MENU_JS.read_text(encoding="utf-8")

    def test_boton_de_chip_incluye_aria_pressed_booleano(self):
        match = re.search(r"\$\('chips'\)\.innerHTML=CHIPS\.map\(ch=>`([^`]*)`\)", self.js)
        self.assertIsNotNone(match, "no se encontró el template de los chips")
        template = match.group(1)
        self.assertIn('aria-pressed="${moodActivo===ch.m}"', template)

    def test_aria_pressed_se_recalcula_en_las_tres_acciones_que_tocan_moodactivo(self):
        """Los chips se regeneran enteros (innerHTML) en cada render(),
        así que aria-pressed queda al día automáticamente en cualquier
        camino que actualice moodActivo y después llame a render() --
        se verifica que los tres caminos reales sigan haciendo eso."""
        # 1) click de un chip
        self.assertRegex(
            self.js,
            r"moodActivo\s*=\s*moodActivo===ch\.dataset\.mood\s*\?\s*null\s*:\s*ch\.dataset\.mood;\s*\n\s*render\(\);",
        )
        # 2) botón "limpiar"
        self.assertRegex(self.js, r"\$\('limpiar'\)\.onclick=\(\)=>\{moodActivo=null;render\(\);")
        # 3) cambio de idioma (moodActivo no cambia, pero el chip se re-renderiza igual)
        self.assertRegex(self.js, r"lang=b\.dataset\.l;\s*cerrarLangs\(\);\s*render\(\);")


class TestCarruselEstadoCoherenteSinScroll(unittest.TestCase):
    """Puntos 4 de la auditoría: si scrollWidth<=clientWidth no hay
    nada para desplazar -- las flechas deben quedar deshabilitadas y el
    indicador de posición no debe mostrar un valor incoherente (por
    ejemplo "03 / 04" con scrollLeft=0 cuando las 4 tarjetas ya entran
    enteras en pantalla)."""

    def setUp(self):
        self.js = MENU_JS.read_text(encoding="utf-8")
        self.css = MENU_CSS.read_text(encoding="utf-8")
        match = re.search(r"function actualizarEstadoCarrusel\(\)\{(.*?)\n\}", self.js, re.S)
        self.assertIsNotNone(match, "no se encontró actualizarEstadoCarrusel()")
        self.cuerpo = match.group(1)

    def test_detecta_scrollwidth_menor_o_igual_a_clientwidth(self):
        self.assertRegex(self.cuerpo, r"scrollWidth\s*<=\s*car\.clientWidth")

    def test_flechas_quedan_disabled_de_verdad_no_solo_atenuadas(self):
        self.assertRegex(self.cuerpo, r"\$\('carPrev'\)\.disabled\s*=\s*sinScroll")
        self.assertRegex(self.cuerpo, r"\$\('carNext'\)\.disabled\s*=\s*sinScroll")
        # atributo HTML real (fuera de tabulación, sin click, anunciado
        # como no disponible) -- no una clase CSS que solo cambie el color.
        regla = re.search(r"\.car-flecha\[disabled\]\{([^}]*)\}", self.css)
        self.assertIsNotNone(regla, "falta el estilo .car-flecha[disabled] en menu.css")

    def test_indicador_se_oculta_cuando_no_hay_nada_para_desplazar(self):
        self.assertRegex(self.cuerpo, r"\$\('carIndicador'\)\.hidden\s*=\s*sinScroll")
        self.assertIn(".car-indicador[hidden]{display:none}", self.css)

    def test_no_calcula_posicion_cuando_esta_sin_scroll(self):
        """El cálculo de 'tarjeta más cercana al centro del viewport'
        (la causa original del "03 / 04" incoherente) debe cortarse
        ANTES de llegar a ese cálculo cuando sinScroll es true."""
        idx_return = self.cuerpo.find("if(sinScroll) return;")
        idx_calculo = self.cuerpo.find("offsetLeft+c.clientWidth/2")
        self.assertNotEqual(idx_return, -1, "falta el corte temprano 'if(sinScroll) return;'")
        self.assertNotEqual(idx_calculo, -1, "no se encontró el cálculo de la tarjeta más cercana")
        self.assertLess(idx_return, idx_calculo)

    def test_mobile_conserva_drag_y_recalculo_en_scroll(self):
        """En mobile scrollWidth siempre es mayor que clientWidth con
        estas tarjetas, así que sinScroll da false y el indicador se
        recalcula normalmente -- el listener de scroll (que dispara el
        recálculo) y el arrastre táctil nativo (touch-action:pan-y en
        .carrusel, sin cambios en esta ronda) siguen intactos."""
        self.assertIn("car.addEventListener('scroll'", self.js)
        self.assertIn("actualizarEstadoCarrusel(); ticking=false;", self.js)
        self.assertIn("touch-action:pan-y", self.css)

    def test_recalcula_en_resize_para_cruzar_el_limite_768px_en_vivo(self):
        self.assertIn("window.addEventListener('resize'", self.js)
        self.assertIn("actualizarEstadoCarrusel, 120", self.js)


if __name__ == "__main__":
    unittest.main()
