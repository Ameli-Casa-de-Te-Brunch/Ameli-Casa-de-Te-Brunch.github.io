/* Temas por calendario (Halloween, Navidad, etc.).
   Lee el calendario embebido en el HTML (<script type="application/json"
   id="ameli-calendario">, ver build/calendario.py) y, si hoy cae dentro de
   un evento de tipo "tema", pone html[data-tema="..."]. Todo el aspecto del
   tema vive en assets/css/temas.css, siempre bajo ese atributo: sin el
   atributo (fuera de fechas, interruptor apagado) el sitio es el diseño
   original, sin ninguna regla del tema aplicándose.

   Va en el <head>, sin defer, para que el atributo exista antes del primer
   pintado (si no, se vería un destello del diseño normal). Es lo único que
   hace: sin fetch (la CSP del sitio lo bloquea), sin estilos inline.

   Previsualizar antes de la fecha: ?tema=encantada. Ver el diseño normal
   aunque haya un tema activo: ?tema=ninguno. Si "activo" es false en el
   calendario, no hay tema ni previsualización (interruptor general).

   Este archivo es idéntico en web/assets/js/ y assets/js/ (cada sitio se
   publica con sus propios assets); un test verifica que no se desalineen. */
(function () {
  var el = document.getElementById('ameli-calendario');
  if (!el) return;
  var cal;
  try { cal = JSON.parse(el.textContent); } catch (e) { return; }
  if (!cal || cal.activo !== true || !Array.isArray(cal.eventos) || !Array.isArray(cal.temas)) return;

  /* Fecha de hoy en Mendoza, AAAA-MM-DD. Argentina no usa horario de
     verano, así que UTC-3 fijo es un respaldo exacto si Intl no está. */
  function hoyEnMendoza() {
    try {
      return new Intl.DateTimeFormat('en-CA', {
        timeZone: cal.zona, year: 'numeric', month: '2-digit', day: '2-digit'
      }).format(new Date());
    } catch (e) {
      return new Date(Date.now() - 3 * 3600 * 1000).toISOString().slice(0, 10);
    }
  }

  var pedido = null;
  try { pedido = new URLSearchParams(window.location.search).get('tema'); } catch (e) {}
  if (pedido === 'ninguno') return;

  var tema = null;
  if (pedido && cal.temas.indexOf(pedido) !== -1) {
    tema = pedido;
  } else {
    var hoy = hoyEnMendoza();
    var mejor = null;
    cal.eventos.forEach(function (ev) {
      if (ev.tipo !== 'tema' || cal.temas.indexOf(ev.tema) === -1) return;
      if (hoy < ev.desde || hoy > ev.hasta) return; /* AAAA-MM-DD se ordena como texto */
      if (!mejor || ev.prioridad > mejor.prioridad ||
          (ev.prioridad === mejor.prioridad && ev.desde > mejor.desde)) mejor = ev;
    });
    if (mejor) tema = mejor.tema;
  }
  if (tema) document.documentElement.setAttribute('data-tema', tema);
})();
