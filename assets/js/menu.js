const LANGS = ['es','en','pt'];
const UI = {
 sub:{es:'Casa de Té · Brunch',en:'Tea House · Brunch',pt:'Casa de Chá · Brunch'},
 lugar:{es:'Malargüe, Mendoza — hecho en casa, todos los días.',en:'Malargüe, Mendoza — homemade, every day.',pt:'Malargüe, Mendoza — feito em casa, todos os dias.'},
 momTitle:{es:'Elegí tu <em>momento</em> Amelí',en:'Choose your Amelí <em>moment</em>',pt:'Escolha o seu <em>momento</em> Amelí'},
 momHint:{es:'Tocá uno y el menú se acomoda a tu antojo',en:'Tap one and the menu adapts to your craving',pt:'Toque em um e o menu se adapta à sua vontade'},
 limpiar:{es:'✕ Ver todo el menú',en:'✕ See the full menu',pt:'✕ Ver o menu completo'},
 destEyebrow:{es:'Hoy en Amelí',en:'Today at Amelí',pt:'Hoje na Amelí'},
 destTitle:{es:'Los destacados de la casa',en:'House highlights',pt:'Os destaques da casa'},
 vacio:{es:'Nada por acá para este momento… probá otro antojo ❧',en:'Nothing here for this moment… try another craving ❧',pt:'Nada por aqui para este momento… tente outra vontade ❧'},
 adicEyebrow:{es:'Personalizá tu bebida',en:'Customise your drink',pt:'Personalize a sua bebida'},
 grx:{es:'Gracias por elegirnos ❧',en:'Thank you for choosing us ❧',pt:'Obrigado por nos escolher ❧'},
 maps:{es:'◈ Cómo llegar',en:'◈ Find us',pt:'◈ Como chegar'},
 datos:{es:'Martes a sábado · 9:00–13:00 y 17:30–21:00<br>Domingo · 17:30–21:00',
        en:'Tuesday–Saturday · 9 am–1 pm & 5:30–9 pm<br>Sunday · 5:30–9 pm',
        pt:'Terça a sábado · 9h–13h e 17h30–21h<br>Domingo · 17h30–21h'},
 wsp:{es:'Pedir',en:'Order',pt:'Pedir'},
 title:{es:'Amelí · Casa de Té & Brunch — Menú',en:'Amelí · Tea House & Brunch — Menu',pt:'Amelí · Casa de Chá & Brunch — Menu'},
 abierto:{es:'Abierto ahora',en:'Open now',pt:'Aberto agora'},
 cerrado:{es:'Cerrado ahora',en:'Closed now',pt:'Fechado agora'},
 abreALas:{es:'Abre a las',en:'Opens at',pt:'Abre às'},
 cerrarSheet:{es:'Cerrar',en:'Close',pt:'Fechar'},
 pedirMensaje:{es:'Hola Amelí! Quiero pedir: ',en:'Hi Amelí! I’d like to order: ',pt:'Olá Amelí! Quero pedir: '},
 verDetalle:{es:'Ver detalle de',en:'View details for',pt:'Ver detalhes de'},
 anterior:{es:'Anterior',en:'Previous',pt:'Anterior'},
 siguiente:{es:'Siguiente',en:'Next',pt:'Próximo'},
 irA:{es:'Ir al destacado',en:'Go to highlight',pt:'Ir para o destaque'},
};
const IDIOMA_LABEL = {es:'Español',en:'English',pt:'Português'};
const CHIPS = [
 {m:'dulce', em:'🍰', t:{es:'Algo dulce',en:'Something sweet',pt:'Algo doce'}},
 {m:'fresco', em:'🌿', t:{es:'Algo fresco',en:'Something fresh',pt:'Algo fresco'}},
 {m:'compartir', em:'🫶', t:{es:'Para compartir',en:'To share',pt:'Para compartilhar'}},
 {m:'calentito', em:'☕', t:{es:'Algo calentito',en:'Something warm',pt:'Algo quentinho'}},
 {m:'llevar', em:'🧺', t:{es:'Para llevar',en:'To go',pt:'Para levar'}},
];
const BADGES = {
 fav:{c:'fav', t:{es:'Favorito de la casa',en:'House favourite',pt:'Favorito da casa'}},
 reco:{c:'reco', t:{es:'Recomendado',en:'Recommended',pt:'Recomendado'}},
 pedido:{c:'pedido', t:{es:'Más pedido',en:'Most ordered',pt:'Mais pedido'}},
 nuevo:{c:'nuevo', t:{es:'Nuevo',en:'New',pt:'Novo'}},
 sintacc:{c:'sintacc', t:{es:'Sin TACC',en:'Gluten free',pt:'Sem glúten'}},
};
const CAT_NOTAS = {
 BYJ:{es:'Vaso o jarra',en:'By the glass or by the jug',pt:'Copo ou jarra'},
 STC:{es:'Producto tercerizado',en:'Outsourced product',pt:'Produto terceirizado'},
};
const GRADIENTES=['linear-gradient(135deg,#536039,#8B966E)','linear-gradient(135deg,#8B2F2F,#A85450)','linear-gradient(135deg,#3E4829,#536039)'];
/* horario: 0=domingo ... 6=sábado. Cada rango es [horaIni,minIni,horaFin,minFin]. */
const HORARIO = {
  0:[[17,30,21,0]], 1:[], 2:[[9,0,13,0],[17,30,21,0]], 3:[[9,0,13,0],[17,30,21,0]],
  4:[[9,0,13,0],[17,30,21,0]], 5:[[9,0,13,0],[17,30,21,0]], 6:[[9,0,13,0],[17,30,21,0]],
};
/* banderas SVG minimalistas — círculo con las franjas esenciales de cada bandera */
const BANDERAS = {
 es:`<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" focusable="false"><clipPath id="cAR"><circle cx="10" cy="10" r="9.5"/></clipPath><g clip-path="url(#cAR)"><rect width="20" height="20" fill="#FFFFFF"/><rect width="20" height="6.7" fill="#75AADB"/><rect y="13.3" width="20" height="6.7" fill="#75AADB"/></g><circle cx="10" cy="10" r="9.2" fill="none" stroke="currentColor" stroke-width="1" opacity=".4"/></svg>`,
 en:`<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" focusable="false"><clipPath id="cGB"><circle cx="10" cy="10" r="9.5"/></clipPath><g clip-path="url(#cGB)"><rect width="20" height="20" fill="#274B8C"/><rect x="8.2" width="3.6" height="20" fill="#FFFFFF"/><rect y="8.2" width="20" height="3.6" fill="#FFFFFF"/><rect x="9" width="2" height="20" fill="#C8283C"/><rect y="9" width="20" height="2" fill="#C8283C"/></g><circle cx="10" cy="10" r="9.2" fill="none" stroke="currentColor" stroke-width="1" opacity=".4"/></svg>`,
 pt:`<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" focusable="false"><clipPath id="cBR"><circle cx="10" cy="10" r="9.5"/></clipPath><g clip-path="url(#cBR)"><rect width="20" height="20" fill="#2E9B4F"/><polygon points="10,3.3 17,10 10,16.7 3,10" fill="#F5D948"/><circle cx="10" cy="10" r="2.8" fill="#2B4B8C"/></g><circle cx="10" cy="10" r="9.2" fill="none" stroke="currentColor" stroke-width="1" opacity=".4"/></svg>`,
};

let lang='es', moodActivo=null, sheetProdId=null;
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

/* ---------- estado abierto/cerrado (America/Argentina/Mendoza) ---------- */
function ahoraMendoza(){
  const fmt = new Intl.DateTimeFormat('en-US',{timeZone:'America/Argentina/Mendoza',hour12:false,weekday:'short',hour:'2-digit',minute:'2-digit'});
  const partes = Object.fromEntries(fmt.formatToParts(new Date()).map(p=>[p.type,p.value]));
  const dias = {Sun:0,Mon:1,Tue:2,Wed:3,Thu:4,Fri:5,Sat:6};
  return {dia:dias[partes.weekday], min: Number(partes.hour)*60 + Number(partes.minute)};
}
function estadoNegocio(){
  const {dia,min} = ahoraMendoza();
  const rangos = HORARIO[dia]||[];
  for(const [h1,m1,h2,m2] of rangos){
    const ini=h1*60+m1, fin=h2*60+m2;
    if(min>=ini && min<fin) return {abierto:true};
    if(min<ini) return {abierto:false, proximaApertura:ini};
  }
  return {abierto:false};
}
function pintarEstado(){
  const est = estadoNegocio();
  const chip = $('estadoChip');
  chip.classList.toggle('cerrado', !est.abierto);
  if(est.abierto){
    $('estadoTexto').textContent = UI.abierto[lang];
  } else if(est.proximaApertura!=null){
    const hh=String(Math.floor(est.proximaApertura/60)).padStart(2,'0');
    const mm=String(est.proximaApertura%60).padStart(2,'0');
    $('estadoTexto').textContent = `${UI.cerrado[lang]} · ${UI.abreALas[lang]} ${hh}:${mm}`;
  } else {
    $('estadoTexto').textContent = UI.cerrado[lang];
  }
}

/* ---------- bottom sheet de detalle ---------- */
let focoPrevio=null;
function abrirDetalle(id){
  const p = PRODS.find(x=>x.id===id);
  if(!p) return;
  sheetProdId=id;
  focoPrevio = document.activeElement;
  $('sheetNombre').textContent = p.n[lang];
  $('sheetDesc').textContent = p.d[lang];
  $('sheetEtiquetas').innerHTML = p.b.map(k=>`<span class="badge ${BADGES[k].c}">${BADGES[k].t[lang]}</span>`).join('');
  const foto=$('sheetFoto');
  foto.className = 'sheet-foto';
  foto.querySelector('img')?.remove();
  if(p.img){
    const img = document.createElement('img');
    img.src = p.img; img.alt = '';
    foto.appendChild(img);
    $('sheetInicial').hidden = true;
  } else {
    foto.classList.add(`grad-${Math.abs(hashId(p.id))%3}`);
    $('sheetInicial').hidden = false;
    $('sheetInicial').textContent=p.n[lang].charAt(0);
  }
  if(WSP_NUMBER){
    const msg = encodeURIComponent(UI.pedirMensaje[lang]+p.n[lang]);
    $('sheetPedir').href = `https://wa.me/${WSP_NUMBER}?text=${msg}`;
    $('sheetPedirTxt').textContent = UI.wsp[lang];
    $('sheetPedir').hidden = false;
  } else {
    $('sheetPedir').hidden = true;
  }
  $('sheetCerrar').setAttribute('aria-label', UI.cerrarSheet[lang]);

  $('sheetBackdrop').hidden=false; $('sheet').hidden=false;
  requestAnimationFrame(()=>{ $('sheetBackdrop').classList.add('abierto'); $('sheet').classList.add('abierto'); });
  document.body.classList.add('sheet-abierto');
  $('sheet').focus();
  document.addEventListener('keydown', onSheetKeydown);
}
function hashId(id){ let h=0; for(const c of id) h=(h*31+c.charCodeAt(0))|0; return h; }
function cerrarDetalle(){
  $('sheetBackdrop').classList.remove('abierto');
  $('sheet').classList.remove('abierto');
  document.body.classList.remove('sheet-abierto');
  document.removeEventListener('keydown', onSheetKeydown);
  setTimeout(()=>{ $('sheetBackdrop').hidden=true; $('sheet').hidden=true; },320);
  if(focoPrevio && focoPrevio.focus) focoPrevio.focus();
  sheetProdId=null;
}
function onSheetKeydown(e){
  if(e.key==='Escape'){ cerrarDetalle(); return; }
  if(e.key==='Tab'){
    const focosables = $('sheet').querySelectorAll('button, a[href]');
    if(!focosables.length) return;
    const primero=focosables[0], ultimo=focosables[focosables.length-1];
    if(e.shiftKey && document.activeElement===primero){ e.preventDefault(); ultimo.focus(); }
    else if(!e.shiftKey && document.activeElement===ultimo){ e.preventDefault(); primero.focus(); }
  }
}
/* swipe-down para cerrar */
(function initSwipe(){
  let arrancoY=null, deltaY=0;
  const sheet=()=>$('sheet');
  $('sheetDrag').addEventListener('pointerdown', e=>{
    arrancoY=e.clientY; deltaY=0;
    sheet().classList.add('sin-transicion');
    e.target.setPointerCapture(e.pointerId);
  });
  $('sheetDrag').addEventListener('pointermove', e=>{
    if(arrancoY===null) return;
    deltaY=Math.max(0, e.clientY-arrancoY);
    /* cuantizado a pasos de 8px: la CSP no permite fijar transform por
       style="" desde JS sin 'unsafe-inline', asi que en vez de un valor
       continuo se usa una clase de una lista fija predefinida en el CSS. */
    sheet().className = sheet().className.replace(/\bdrag-\d+\b/g, '').trim();
    sheet().classList.add(`drag-${Math.min(600, Math.round(deltaY/8)*8)}`);
  });
  function soltar(){
    if(arrancoY===null) return;
    sheet().classList.remove('sin-transicion');
    sheet().className = sheet().className.replace(/\bdrag-\d+\b/g, '').trim();
    if(deltaY>90) cerrarDetalle();
    arrancoY=null; deltaY=0;
  }
  $('sheetDrag').addEventListener('pointerup', soltar);
  $('sheetDrag').addEventListener('pointercancel', soltar);
})();
$('sheetCerrar').addEventListener('click', cerrarDetalle);
$('sheetBackdrop').addEventListener('click', cerrarDetalle);

/* ---------- carrusel: flechas, puntos, drag desktop ---------- */
function initCarrusel(){
  const car=$('carrusel');
  const cards=[...car.querySelectorAll('.dcard')];
  $('carPuntos').innerHTML = cards.map((_,i)=>`<button aria-label="${esc(UI.irA[lang])} ${i+1}"></button>`).join('');
  const puntos=[...$('carPuntos').querySelectorAll('button')];
  function actualizarPuntos(){
    const centro=car.scrollLeft+car.clientWidth/2;
    let idx=0, mejor=Infinity;
    cards.forEach((c,i)=>{ const d=Math.abs((c.offsetLeft+c.clientWidth/2)-centro); if(d<mejor){mejor=d;idx=i;} });
    puntos.forEach((p,i)=>p.classList.toggle('actual', i===idx));
  }
  let ticking=false;
  car.addEventListener('scroll', ()=>{
    if(ticking) return; ticking=true;
    requestAnimationFrame(()=>{ actualizarPuntos(); ticking=false; });
  }, {passive:true});
  puntos.forEach((p,i)=>p.addEventListener('click', ()=>cards[i].scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'})));
  $('carPrev').onclick=()=>car.scrollBy({left:-car.clientWidth*.8, behavior:'smooth'});
  $('carNext').onclick=()=>car.scrollBy({left:car.clientWidth*.8, behavior:'smooth'});
  actualizarPuntos();

  /* arrastre con mouse en desktop (touch ya funciona nativo con scroll-snap) */
  let arrastrando=false, inicioX=0, scrollInicio=0, velocidad=0, ultimoX=0, ultimoT=0;
  car.addEventListener('pointerdown', e=>{
    if(e.pointerType==='touch') return;
    arrastrando=true; car.classList.add('arrastrando');
    inicioX=e.clientX; scrollInicio=car.scrollLeft; ultimoX=e.clientX; ultimoT=performance.now();
    car.setPointerCapture(e.pointerId);
  });
  car.addEventListener('pointermove', e=>{
    if(!arrastrando) return;
    const ahora=performance.now();
    car.scrollLeft = scrollInicio-(e.clientX-inicioX);
    const dt=ahora-ultimoT || 16;
    velocidad = (e.clientX-ultimoX)/dt;
    ultimoX=e.clientX; ultimoT=ahora;
  });
  function terminarArrastre(){
    if(!arrastrando) return;
    arrastrando=false; car.classList.remove('arrastrando');
    let v=velocidad*16;
    function inercia(){
      if(Math.abs(v)<0.5) return;
      car.scrollLeft -= v; v*=.94;
      requestAnimationFrame(inercia);
    }
    if(!window.matchMedia('(prefers-reduced-motion: reduce)').matches) inercia();
  }
  car.addEventListener('pointerup', terminarArrastre);
  car.addEventListener('pointercancel', terminarArrastre);
  car.addEventListener('pointerleave', terminarArrastre);
}

/* ---------- render principal ---------- */
function render(){
  document.documentElement.lang=lang;
  document.title=UI.title[lang];
  $('heroSub').textContent=UI.sub[lang];
  $('heroLugar').textContent=UI.lugar[lang];
  $('momTitle').innerHTML=UI.momTitle[lang];
  $('momHint').textContent=UI.momHint[lang];
  $('limpiar').textContent=UI.limpiar[lang];
  $('destEyebrow').textContent=UI.destEyebrow[lang];
  $('destTitle').textContent=UI.destTitle[lang];
  $('footGrx').textContent=UI.grx[lang];
  if($('footMaps')) $('footMaps').textContent=UI.maps[lang];
  $('footDatos').innerHTML=UI.datos[lang];
  if($('wspTxt')) $('wspTxt').textContent=UI.wsp[lang];
  $('carPrev').setAttribute('aria-label', UI.anterior[lang]);
  $('carNext').setAttribute('aria-label', UI.siguiente[lang]);
  pintarEstado();
  /* selector de idioma */
  $('langs').innerHTML=LANGS.map(l=>`<button data-l="${l}" class="${l===lang?'activo':''}" aria-pressed="${l===lang}" aria-label="${esc(IDIOMA_LABEL[l])}">${BANDERAS[l]}<span>${l.toUpperCase()}</span></button>`).join('');
  document.querySelectorAll('#langs button').forEach(b=>b.addEventListener('click',()=>{lang=b.dataset.l;render();aplicarFiltro();}));
  /* chips */
  $('chips').innerHTML=CHIPS.map(ch=>`<button class="chip ${moodActivo===ch.m?'activo':''}" data-mood="${ch.m}"><span class="em">${ch.em}</span>${ch.t[lang]}</button>`).join('');
  document.querySelectorAll('.chip').forEach(ch=>ch.addEventListener('click',()=>{
    moodActivo = moodActivo===ch.dataset.mood ? null : ch.dataset.mood;
    render(); aplicarFiltro();
    if(moodActivo) $('menu').scrollIntoView({behavior:'smooth',block:'start'});
  }));
  $('limpiar').onclick=()=>{moodActivo=null;render();aplicarFiltro();};
  /* nav — Adicionales se muestra como banda, no en nav */
  const catsNav=CATS.filter(c=>c.cod!=='ADI');
  $('navcat').innerHTML=catsNav.map(c=>`<a href="#${esc(c.cod)}">${esc(c.nom[lang])}</a>`).join('');
  /* carrusel destacados */
  $('carrusel').innerHTML=PRODS.filter(p=>p.dest).map((p,i)=>{
    const bd=p.b.map(k=>`<span class="pill">${BADGES[k].t[lang]}</span>`).join('');
    const fotoContenido = p.img
      ? `<img src="${esc(p.img)}" alt="" loading="lazy">`
      : `<span class="inicial">${esc(p.n[lang].charAt(0))}</span>`;
    return `<article class="dcard" data-id="${esc(p.id)}" role="button" tabindex="0" aria-label="${esc(UI.verDetalle[lang])} ${esc(p.n[lang])}">
      <div class="foto ${p.img?'':`grad-${i%3}`}">${fotoContenido}</div>
      <div class="cuerpo">${bd}<h4>${esc(p.n[lang])}</h4><p>${esc(p.d[lang])}</p></div></article>`;
  }).join('');
  document.querySelectorAll('.dcard').forEach(card=>{
    card.addEventListener('click', ()=>abrirDetalle(card.dataset.id));
    card.addEventListener('keydown', e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); abrirDetalle(card.dataset.id); } });
  });
  initCarrusel();
  /* secciones */
  $('menu').innerHTML=catsNav.map(cat=>{
    const items=PRODS.filter(p=>p.cat===cat.cod);
    if(!items.length) return '';
    const nota=CAT_NOTAS[cat.cod]?`<p class="desc-cat">${CAT_NOTAS[cat.cod][lang]}</p>`:'';
    const cards=items.map((p,i)=>{
      const bd=p.b.map(k=>`<span class="badge ${BADGES[k].c}">${BADGES[k].t[lang]}</span>`).join('');
      const et=bd?`<div class="etiquetas">${bd}</div>`:'';
      const precio=PRECIOS[p.id]?`<span class="precio">${esc(PRECIOS[p.id])}</span>`:'';
      return `<article class="prod ${p.dest?'destacada':''} stagger-${Math.min(i,9)}" data-moods="${p.m.join(',')}" data-id="${esc(p.id)}" role="button" tabindex="0" aria-label="${esc(UI.verDetalle[lang])} ${esc(p.n[lang])}">
        <div class="prod-inner">${et}<div class="fila"><h4>${esc(p.n[lang])}</h4>${precio}</div><p>${esc(p.d[lang])}</p></div></article>`;
    }).join('');
    return `<section class="cat" id="${esc(cat.cod)}"><header><h3>${esc(cat.nom[lang])}</h3>${nota}</header>
      <div class="lista">${cards}</div><p class="vacio">${UI.vacio[lang]}</p></section>`;
  }).join('');
  document.querySelectorAll('main .prod').forEach(card=>{
    card.addEventListener('click', ()=>abrirDetalle(card.dataset.id));
    card.addEventListener('keydown', e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); abrirDetalle(card.dataset.id); } });
  });
  /* banda adicionales */
  const adi=PRODS.filter(p=>p.cat==='ADI');
  const catAdi=CATS.find(c=>c.cod==='ADI');
  $('adicEyebrow').textContent=UI.adicEyebrow[lang];
  $('adicTitle').textContent=catAdi?catAdi.nom[lang]:'';
  $('adicLista').innerHTML=adi.map(p=>`<li><b>${esc(p.n[lang])}</b><span class="det">${esc(p.d[lang])}</span></li>`).join('');
  observarNav();
  observarCategorias();
}
function aplicarFiltro(){
  document.querySelectorAll('.prod').forEach(p=>{
    const moods=(p.dataset.moods||'').split(',');
    p.classList.toggle('oculto', !!moodActivo && !moods.includes(moodActivo));
  });
  document.querySelectorAll('section.cat').forEach(sec=>{
    sec.classList.toggle('sin-resultados', sec.querySelectorAll('.prod:not(.oculto)').length===0);
  });
  $('limpiar').classList.toggle('visible', !!moodActivo);
}
let observer;
function observarNav(){
  if(observer) observer.disconnect();
  const links=document.querySelectorAll('.navcat a');
  observer=new IntersectionObserver(entries=>{
    entries.forEach(en=>{
      if(en.isIntersecting){
        links.forEach(l=>l.classList.toggle('actual', l.getAttribute('href')==='#'+en.target.id));
        const a=document.querySelector('.navcat a.actual');
        if(a) a.scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'});
      }
    });
  },{rootMargin:'-30% 0px -60% 0px'});
  document.querySelectorAll('section.cat').forEach(s=>observer.observe(s));
}
let observerCats;
function observarCategorias(){
  if(observerCats) observerCats.disconnect();
  observerCats=new IntersectionObserver(entries=>{
    entries.forEach(en=>{
      if(en.isIntersecting){ en.target.classList.add('visible'); observerCats.unobserve(en.target); }
    });
  },{threshold:.12});
  document.querySelectorAll('section.cat').forEach(s=>observerCats.observe(s));
}
window.addEventListener('scroll', ()=>{ $('navcat').classList.toggle('scrolled', window.scrollY>4); }, {passive:true});

render(); aplicarFiltro();
