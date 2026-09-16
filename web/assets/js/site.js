/*
  Amelí — panel de accesibilidad. JavaScript propio, sin librerías ni
  CDN (coherente con la CSP: script-src 'self'). Mismo mecanismo que el
  panel del menú real: un multiplicador --afs de tamaño de texto y tres
  atributos data-* en <html> (contraste, movimiento, lectura), todo
  guardado en localStorage de este navegador. Nada de esto sale del
  dispositivo: no hay red (connect-src 'none' en la CSP), no hay
  cookies, no hay analítica.

  ATENCIÓN A CUÁNDO SE APLICA: este <script> se carga al final del
  documento (no en <head>, no con `defer`), así que la preferencia
  guardada se aplica recién cuando el navegador llega a ejecutarlo --
  es decir, al cargar la página, no necesariamente antes del primer
  render. En una conexión lenta o con el CSS/las fuentes tardando en
  llegar, es posible que se alcance a pintar un instante con el
  tamaño de texto o el contraste todavía sin ajustar. No se afirma acá
  ni en el README que esto esté garantizado "antes del primer render"
  o "sin parpadeo" en todos los navegadores. Una alternativa a futuro
  -- no implementada ahora -- sería mover este <script> a <head> con
  `defer` (que sigue siendo compatible con script-src 'self', sin
  'unsafe-inline'); reduciría la ventana de parpadeo pero tampoco la
  elimina con garantía total en cualquier navegador.

  Además: este panel es una ayuda complementaria, no la base principal
  de accesibilidad del sitio. Esa base sigue siendo HTML semántico,
  navegación completa por teclado, foco visible, contraste suficiente
  en el diseño por defecto, zoom y reflow del navegador, y las
  preferencias de accesibilidad del sistema operativo y del navegador
  (prefers-reduced-motion, prefers-contrast, zoom de página, etc.).
  Si este script no carga, está bloqueado o falla durante la
  inicialización, el contenido esencial de la página (texto, enlaces,
  menú, contacto) sigue siendo completamente usable. El botón "Aa"
  mismo es mejora progresiva real, no solo funcional: arranca oculto e
  inhabilitado (atributo `data-a11y-pending` + `visibility:hidden` en
  site.css) y este script lo revela recién al final, después de
  encontrar todos los elementos del panel y registrar todos sus
  eventos con éxito. Si algo de eso falla, el botón se queda oculto e
  inenfocable para siempre -- nunca visible pero inerte (ver README,
  sección de accesibilidad).
*/
(function () {
  'use strict';

  var CLAVE = 'ameli_a11y';
  var raiz = document.documentElement;

  function leerGuardado() {
    try {
      var crudo = window.localStorage.getItem(CLAVE);
      if (!crudo) return {};
      var datos = JSON.parse(crudo);
      return datos && typeof datos === 'object' ? datos : {};
    } catch (err) {
      return {};
    }
  }

  function guardar(estado) {
    try {
      window.localStorage.setItem(CLAVE, JSON.stringify(estado));
    } catch (err) {
      /* localStorage no disponible (privado/bloqueado): el panel sigue
         funcionando para la sesión actual, solo no persiste. */
    }
  }

  /* '2' (200%) y no '1.6' (160%) a propósito -- WCAG 1.4.4 "Resize
     text" exige que el contenido siga siendo usable con el texto al
     200%, así que el control propio del panel tiene que poder llegar
     ahí, no quedarse corto en un valor intermedio. */
  var AFS_VALIDOS = ['1', '1.3', '2'];

  function aplicarEstado(estado) {
    if (AFS_VALIDOS.indexOf(String(estado.afs)) !== -1) {
      raiz.style.setProperty('--afs', String(estado.afs));
    } else {
      raiz.style.removeProperty('--afs');
    }
    if (estado.contraste) {
      raiz.setAttribute('data-contraste', 'alto');
    } else {
      raiz.removeAttribute('data-contraste');
    }
    if (estado.movimiento) {
      raiz.setAttribute('data-movimiento', 'reducido');
    } else {
      raiz.removeAttribute('data-movimiento');
    }
    if (estado.lectura) {
      raiz.setAttribute('data-lectura', 'simple');
    } else {
      raiz.removeAttribute('data-lectura');
    }
  }

  var estadoActual = leerGuardado();
  aplicarEstado(estadoActual);

  document.addEventListener('DOMContentLoaded', function () {
    var boton = document.getElementById('a11yBtn');
    var panel = document.getElementById('a11yPanel');
    var botonCerrar = document.getElementById('a11yCerrar');
    var botonReset = document.getElementById('a11yReset');
    var botonesAfs = panel.querySelectorAll('[data-afs]');
    var casilleroContraste = document.getElementById('a11yContraste');
    var casilleroMovimiento = document.getElementById('a11yMovimiento');
    var casilleroLectura = document.getElementById('a11yLectura');

    /* Menú de navegación (tres rayas) -- mismo patrón exacto que el
       panel de accesibilidad de arriba: <dialog> nativo, mejora
       progresiva real (data-nav-pending nunca se saca si falta algún
       elemento), Escape y foco contenido los maneja el navegador. Se
       registra en un bloque aparte, independiente del de accesibilidad
       -- si uno de los dos paneles no encuentra sus elementos, el otro
       igual queda funcional. */
    (function () {
      var botonNav = document.getElementById('navBtn');
      var panelNav = document.getElementById('navPanel');
      var botonCerrarNav = document.getElementById('navCerrar');
      if (!botonNav || !panelNav || !botonCerrarNav) return;

      function abrirNav() {
        panelNav.showModal();
        botonNav.setAttribute('aria-expanded', 'true');
      }
      function alCerrarNav() {
        botonNav.setAttribute('aria-expanded', 'false');
        botonNav.focus();
      }
      panelNav.addEventListener('close', alCerrarNav);
      panelNav.addEventListener('click', function (evento) {
        if (evento.target !== panelNav) return;
        var rect = panelNav.getBoundingClientRect();
        var dentro = evento.clientX >= rect.left && evento.clientX <= rect.right &&
                     evento.clientY >= rect.top && evento.clientY <= rect.bottom;
        if (!dentro) {
          panelNav.close();
          alCerrarNav();
        }
      });
      botonNav.addEventListener('click', function () {
        if (!panelNav.open) abrirNav();
      });
      botonCerrarNav.addEventListener('click', function () {
        panelNav.close();
        alCerrarNav();
      });
      panelNav.addEventListener('keydown', function (evento) {
        if (evento.key === 'Escape' || evento.key === 'Esc') {
          panelNav.close();
          alCerrarNav();
        }
      });
      /* Cerrar el panel al tocar un enlace real de la navegación --
         si no, el <dialog> se queda abierto tapando la sección a la
         que se acaba de navegar. */
      panelNav.querySelectorAll('.nav-principal a').forEach(function (enlace) {
        enlace.addEventListener('click', function () {
          panelNav.close();
          alCerrarNav();
        });
      });

      botonNav.removeAttribute('data-nav-pending');
    })();

    /* Pestañas de la maqueta "Sumate". No hay envío de formularios:
       solo alternan dos paneles locales y accesibles. */
    var tabsSumate = Array.prototype.slice.call(
      document.querySelectorAll('.tab-lista [role="tab"]')
    );
    function activarTabSumate(tab) {
      tabsSumate.forEach(function (item) {
        var activo = item === tab;
        var panelId = item.getAttribute('aria-controls');
        var panelTab = document.getElementById(panelId);
        item.setAttribute('aria-selected', activo ? 'true' : 'false');
        item.tabIndex = activo ? 0 : -1;
        if (panelTab) panelTab.hidden = !activo;
      });
    }
    tabsSumate.forEach(function (tab, indice) {
      tab.addEventListener('click', function () { activarTabSumate(tab); });
      tab.addEventListener('keydown', function (evento) {
        if (evento.key !== 'ArrowLeft' && evento.key !== 'ArrowRight') return;
        evento.preventDefault();
        var paso = evento.key === 'ArrowRight' ? 1 : -1;
        var siguiente = (indice + paso + tabsSumate.length) % tabsSumate.length;
        activarTabSumate(tabsSumate[siguiente]);
        tabsSumate[siguiente].focus();
      });
    });

    /* Mejora progresiva real: si falta cualquier elemento que este
       script necesita, no se registra nada y el botón se queda con
       data-a11y-pending -- oculto, inhabilitado, invisible para el
       árbol de accesibilidad -- para siempre. Recién se saca ese
       atributo al final de esta función, después de que todos los
       listeners quedaron registrados con éxito. */
    if (!boton || !panel || !botonCerrar || !botonReset ||
        !botonesAfs.length || !casilleroContraste ||
        !casilleroMovimiento || !casilleroLectura) {
      return;
    }

    function sincronizarControles() {
      var afsGuardado = AFS_VALIDOS.indexOf(String(estadoActual.afs)) !== -1
        ? String(estadoActual.afs)
        : '1';
      botonesAfs.forEach(function (b) {
        var activo = b.getAttribute('data-afs') === afsGuardado;
        b.setAttribute('aria-pressed', activo ? 'true' : 'false');
      });
      casilleroContraste.checked = Boolean(estadoActual.contraste);
      casilleroMovimiento.checked = Boolean(estadoActual.movimiento);
      casilleroLectura.checked = Boolean(estadoActual.lectura);
    }

    function actualizar(cambios) {
      estadoActual = Object.assign({}, estadoActual, cambios);
      aplicarEstado(estadoActual);
      guardar(estadoActual);
      sincronizarControles();
    }

    function abrirPanel() {
      panel.showModal();
      boton.setAttribute('aria-expanded', 'true');
    }

    /* <dialog>.showModal() vuelve inerte automáticamente todo lo que
       queda fuera del panel (no es focuseable ni clickeable mientras
       está abierto) y contiene el foco de Tab/Shift+Tab dentro del
       panel -- eso lo hace el navegador, no este script. Devolver el
       foco al botón "Aa" al cerrar también lo hace el navegador por
       defecto (restaura el foco al elemento que lo tenía antes de
       showModal()) -- por eso boton.focus() de acá abajo es
       redundante en un navegador que cumple el estándar, pero se deja
       como refuerzo explícito. */
    function alCerrar() {
      boton.setAttribute('aria-expanded', 'false');
      boton.focus();
    }

    /* aria-expanded se actualiza en cada camino que cierra el panel
       (botón cerrar, click afuera) en vez de depender únicamente del
       evento 'close' del <dialog> -- se comprobó que ese evento no se
       dispara en todos los navegadores al llamar close() (verificado
       en el entorno de prueba con un <dialog> mínimo, sin relación con
       este código). El listener de 'close' se conserva igual, porque
       es el único lugar que se entera de un cierre por Escape (nativo
       del <dialog>, sin código propio) en los navegadores donde si
       dispara ese evento -- así queda cubierto de las dos formas. */
    panel.addEventListener('close', alCerrar);

    /* Cerrar al clickear fuera del contenido del panel. El fondo
       oscurecido (::backdrop) no es un nodo del DOM aparte -- un click
       ahí llega con el propio <dialog> como target, así que se
       distingue de un click dentro comparando la posición contra el
       rectángulo real del panel. */
    panel.addEventListener('click', function (evento) {
      if (evento.target !== panel) return;
      var rect = panel.getBoundingClientRect();
      var dentro = evento.clientX >= rect.left && evento.clientX <= rect.right &&
                   evento.clientY >= rect.top && evento.clientY <= rect.bottom;
      if (!dentro) {
        panel.close();
        alCerrar();
      }
    });

    boton.addEventListener('click', function () {
      if (!panel.open) abrirPanel();
    });
    botonCerrar.addEventListener('click', function () {
      panel.close();
      alCerrar();
    });

    /* Refuerzo explícito de Escape -- el <dialog> nativo ya debería
       cerrarse solo con Escape (evento 'cancel' + 'close', cubiertos
       arriba), pero esto no depende únicamente de ese comportamiento
       por defecto del navegador: si por lo que sea no se disparara,
       este listener cierra el panel igual. Idempotente si el navegador
       además dispara su propio cierre nativo: panel.close() en un
       <dialog> ya cerrado no hace nada. */
    panel.addEventListener('keydown', function (evento) {
      if (evento.key === 'Escape' || evento.key === 'Esc') {
        panel.close();
        alCerrar();
      }
    });

    botonesAfs.forEach(function (b) {
      b.addEventListener('click', function () {
        actualizar({ afs: b.getAttribute('data-afs') });
      });
    });
    casilleroContraste.addEventListener('change', function () {
      actualizar({ contraste: casilleroContraste.checked });
    });
    casilleroMovimiento.addEventListener('change', function () {
      actualizar({ movimiento: casilleroMovimiento.checked });
    });
    casilleroLectura.addEventListener('change', function () {
      actualizar({ lectura: casilleroLectura.checked });
    });
    botonReset.addEventListener('click', function () {
      estadoActual = {};
      aplicarEstado(estadoActual);
      guardar(estadoActual);
      sincronizarControles();
    });

    sincronizarControles();

    /* Recién acá, con todo encontrado y todos los eventos registrados
       sin errores, se revela el botón. Si cualquier línea anterior de
       esta función hubiera lanzado (un elemento inesperadamente nulo,
       por ejemplo), esta línea nunca se ejecuta y el botón se queda
       oculto e inhabilitado -- nunca a medias. */
    boton.removeAttribute('data-a11y-pending');
  });
})();
