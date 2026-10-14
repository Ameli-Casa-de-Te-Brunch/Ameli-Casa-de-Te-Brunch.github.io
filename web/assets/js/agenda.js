/* Cierres, horarios especiales y avisos del día.
   Lee el calendario embebido en el HTML (<script type="application/json"
   id="ameli-calendario">, ver build/calendario.py) y expone window.AmeliAgenda
   para que el cartel "Abierto/Cerrado" del menú (assets/js/menu.js) y el
   aviso del día de los dos sitios sepan qué pasa HOY en Mendoza.

   Reglas (las mismas que en docs/operations/TEMAS_Y_CALENDARIO.md):
   - cierre: el local no abre. Si hay varios hoy, manda el de mayor prioridad
     (si empatan, el que empieza más tarde).
   - horario_especial: reemplaza el horario habitual de hoy. Un cierre le gana.
   - aviso: se muestran hasta 3 en total, de mayor a menor prioridad.
   - campana: un bloque destacado (#campanaDia) con título, texto y un botón
     de pedido por WhatsApp. Se muestra la de mayor prioridad.
   - Un evento con mensaje muestra ese texto (mensaje_en si el idioma es
     inglés y existe); sin mensaje se usa un texto automático en 5 idiomas.
   Los mensajes se escriben SIEMPRE con textContent, nunca como HTML.

   El interruptor "activo" del calendario es solo de los temas: los cierres y
   avisos se apagan poniendo "No" en su fila de la hoja.

   Va en el <head> (síncrono, sin defer) porque menu.js, al final del body, lo
   necesita ya cargado. No hace nada hasta que alguien lo llama, salvo pintar
   el aviso en los contenedores #avisoDia con data-auto (la web institucional).
   Es idéntico en web/assets/js/ y assets/js/ (un test verifica que no se
   desalineen). Sin red, sin estilos inline. */
(function () {
  var el = document.getElementById('ameli-calendario');
  var cal = null;
  try { cal = el ? JSON.parse(el.textContent) : null; } catch (e) { cal = null; }
  var eventos = (cal && Array.isArray(cal.eventos)) ? cal.eventos : [];
  var zona = (cal && cal.zona) || 'America/Argentina/Mendoza';

  var TEXTOS = {
    cierre: {
      es: 'Hoy estamos cerrados.', en: 'We are closed today.', pt: 'Hoje estamos fechados.',
      fr: 'Nous sommes fermés aujourd’hui.', it: 'Oggi siamo chiusi.'
    },
    pedir: {
      es: 'Hacer mi pedido', en: 'Place my order', pt: 'Fazer meu pedido',
      fr: 'Passer ma commande', it: 'Fai il tuo ordine'
    },
    ahora: {
      es: 'Ahora en Amelí', en: 'Now at Amelí', pt: 'Agora na Amelí',
      fr: 'En ce moment chez Amelí', it: 'Ora da Amelí'
    },
    especial: {
      es: 'Hoy: horario especial', en: 'Today: special hours', pt: 'Hoje: horário especial',
      fr: 'Aujourd’hui : horaire spécial', it: 'Oggi: orario speciale'
    }
  };

  /* Fecha de hoy en Mendoza, AAAA-MM-DD. Argentina no usa horario de verano,
     así que UTC-3 fijo es un respaldo exacto si Intl no está. */
  function hoyEnMendoza() {
    try {
      return new Intl.DateTimeFormat('en-CA', {
        timeZone: zona, year: 'numeric', month: '2-digit', day: '2-digit'
      }).format(new Date());
    } catch (e) {
      return new Date(Date.now() - 3 * 3600 * 1000).toISOString().slice(0, 10);
    }
  }

  function activos(tipo, hoy) {
    return eventos.filter(function (ev) {
      return ev.tipo === tipo && hoy >= ev.desde && hoy <= ev.hasta; /* AAAA-MM-DD se ordena como texto */
    });
  }
  function masImportante(a, b) {
    if (a.prioridad !== b.prioridad) return b.prioridad - a.prioridad;
    return a.desde < b.desde ? 1 : (a.desde > b.desde ? -1 : 0);
  }
  function elegir(lista) {
    return lista.length ? lista.slice().sort(masImportante)[0] : null;
  }

  /* Qué pasa hoy: { fecha, cierre, especial, franjas, avisos }. franjas es
     [[h1,m1,h2,m2], ...] (el mismo formato que HORARIO de menu.js) o null. */
  function hoy() {
    var fecha = hoyEnMendoza();
    var cierre = elegir(activos('cierre', fecha));
    var especial = cierre ? null : elegir(activos('horario_especial', fecha));
    return {
      fecha: fecha,
      cierre: cierre,
      especial: especial,
      franjas: especial ? especial.franjas : null,
      avisos: activos('aviso', fecha).sort(masImportante),
      campana: elegir(activos('campana', fecha))
    };
  }

  function dos(n) { return (n < 10 ? '0' : '') + n; }
  function franjasTexto(franjas) {
    return franjas.map(function (f) { return dos(f[0]) + ':' + dos(f[1]) + '–' + dos(f[2]) + ':' + dos(f[3]); }).join(' · ');
  }
  function mensajeDe(ev, lang) {
    if (lang === 'en' && ev.mensaje_en) return ev.mensaje_en;
    return ev.mensaje || null;
  }

  /* Textos a mostrar hoy, en el idioma pedido: [{texto, cierre}], máximo 3. */
  function textosDeHoy(lang) {
    var idioma = TEXTOS.cierre[lang] ? lang : 'es';
    var d = hoy();
    var salida = [];
    if (d.cierre) salida.push({ cierre: true, texto: mensajeDe(d.cierre, idioma) || TEXTOS.cierre[idioma] });
    if (d.especial) {
      salida.push({ cierre: false, texto: mensajeDe(d.especial, idioma) ||
        (TEXTOS.especial[idioma] + ' ' + franjasTexto(d.franjas)) });
    }
    d.avisos.forEach(function (ev) {
      var t = mensajeDe(ev, idioma);
      if (t) salida.push({ cierre: false, texto: t });
    });
    return salida.slice(0, 3);
  }

  /* Escribe los textos de hoy en #avisoDia (uno por <p>) y lo oculta si no hay. */
  function pintar(lang) {
    pintarCampana(lang);
    var cont = document.getElementById('avisoDia');
    if (!cont) return;
    var textos = textosDeHoy(lang);
    cont.textContent = '';
    textos.forEach(function (t) {
      var p = document.createElement('p');
      p.textContent = t.texto;
      if (t.cierre) p.className = 'cierre';
      cont.appendChild(p);
    });
    cont.hidden = textos.length === 0;
  }

  /* Campaña de hoy en el idioma pedido: { titulo, mensaje, tituloOriginal } o null.
     El mensaje de WhatsApp usa siempre el título en español (así lo lee el local). */
  function campanaDeHoy(lang) {
    var ev = hoy().campana;
    if (!ev) return null;
    var idioma = TEXTOS.cierre[lang] ? lang : 'es';
    return {
      titulo: (idioma === 'en' && ev.titulo_en) ? ev.titulo_en : ev.titulo,
      mensaje: mensajeDe(ev, idioma) || '',
      tituloOriginal: ev.titulo
    };
  }

  /* Rellena #campanaDia (con textContent) y lo oculta si hoy no hay campaña.
     El botón es un enlace de WhatsApp ya escrito en el HTML: acá solo se le
     agrega el texto del mensaje. */
  function pintarCampana(lang) {
    var cont = document.getElementById('campanaDia');
    if (!cont) return;
    var idioma = TEXTOS.cierre[lang] ? lang : 'es';
    var c = campanaDeHoy(idioma);
    if (!c) { cont.hidden = true; return; }
    var poner = function (sel, texto) {
      var nodo = cont.querySelector(sel);
      if (nodo) { nodo.textContent = texto; if (nodo.tagName === 'P') nodo.hidden = !texto; }
    };
    poner('.campana-etiqueta', TEXTOS.ahora[idioma]);
    poner('.campana-titulo', c.titulo);
    poner('.campana-mensaje', c.mensaje);
    poner('.campana-cta-texto', TEXTOS.pedir[idioma]);
    var enlace = cont.querySelector('.campana-cta');
    if (enlace) {
      if (!enlace.dataset.base) enlace.dataset.base = enlace.href.split('?')[0];
      if (enlace.dataset.base.indexOf('https://wa.me/') === 0) {
        enlace.href = enlace.dataset.base + '?text=' +
          encodeURIComponent('Hola Amelí! Quiero hacer un pedido: ' + c.tituloOriginal);
      }
    }
    cont.hidden = false;
  }

  window.AmeliAgenda = { hoy: hoy, textosDeHoy: textosDeHoy, pintar: pintar,
                         campanaDeHoy: campanaDeHoy, pintarCampana: pintarCampana };

  function automatico() {
    var cont = document.getElementById('avisoDia');
    var camp = document.getElementById('campanaDia');
    if (cont && cont.hasAttribute('data-auto')) pintar('es');
    else if (camp && camp.hasAttribute('data-auto')) pintarCampana('es');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', automatico);
  else automatico();
})();
