/* GitHub Pages no permite mandar cabeceras HTTP propias, así que
   frame-ancestors del CSP (declarado vía <meta>) queda sin efecto —
   el navegador lo ignora fuera de una respuesta HTTP real. Intentar
   navegar la ventana de arriba (el framebuster clásico) tampoco sirve:
   Chrome lo bloquea si el iframe no es del mismo origen o no hubo un
   gesto del usuario (probado: tira SecurityError). En cambio, ocultar
   el contenido si detectamos que estamos embebidos sí funciona siempre
   — mitiga clickjacking sin depender de una API que puede estar bloqueada. */
if (window.top !== window.self) {
  document.documentElement.style.display = 'none';
}

/* Preferencias de accesibilidad guardadas localmente (nunca salen del
   dispositivo, no es tracking) -- se aplican ya, antes del primer render,
   para que no haya un parpadeo con el tamaño/contraste por defecto. */
const A11Y_KEY = 'ameli_a11y';
function leerA11y(){
  try{ return JSON.parse(localStorage.getItem(A11Y_KEY) || '{}'); }catch(e){ return {}; }
}
function guardarA11y(p){
  try{ localStorage.setItem(A11Y_KEY, JSON.stringify(p)); }catch(e){}
}
let a11yPrefs = leerA11y();
(function aplicarA11yInicial(){
  const html = document.documentElement;
  html.style.setProperty('--afs', a11yPrefs.afs || 1);
  if(a11yPrefs.contraste) html.setAttribute('data-contraste','alto');
  if(a11yPrefs.movimiento) html.setAttribute('data-movimiento','reducido');
  if(a11yPrefs.lectura) html.setAttribute('data-lectura','simple');
})();

const LANGS = ['es','en','pt','fr','it'];
const UI = {
 sub:{es:'Casa de Té · Brunch',en:'Tea House · Brunch',pt:'Casa de Chá · Brunch',fr:'Maison de thé · Brunch',it:'Casa del tè · Brunch'},
 lugar:{es:'Malargüe, Mendoza — hecho en casa, todos los días.',en:'Malargüe, Mendoza — homemade, every day.',pt:'Malargüe, Mendoza — feito em casa, todos os dias.',fr:'Malargüe, Mendoza — fait maison, tous les jours.',it:'Malargüe, Mendoza — fatto in casa, tutti i giorni.'},
 buenosDias:{es:'Buenos días',en:'Good morning',pt:'Bom dia',fr:'Bonjour',it:'Buongiorno'},
 buenasTardes:{es:'Buenas tardes',en:'Good afternoon',pt:'Boa tarde',fr:'Bon après-midi',it:'Buon pomeriggio'},
 buenasNoches:{es:'Buenas noches',en:'Good evening',pt:'Boa noite',fr:'Bonsoir',it:'Buonasera'},
 antojoHoy:{es:'¿Qué se te antoja hoy?',en:'What are you craving today?',pt:'O que você está com vontade hoje?',fr:'Qu’avez-vous envie de déguster aujourd’hui ?',it:'Cosa ti va di gustare oggi?'},
 momTitle:{es:'Elegí tu <em>momento</em> Amelí',en:'Choose your Amelí <em>moment</em>',pt:'Escolha o seu <em>momento</em> Amelí',fr:'Choisissez votre <em>moment</em> Amelí',it:'Scegli il tuo <em>momento</em> Amelí'},
 momHint:{es:'Tocá uno y el menú se acomoda a tu antojo',en:'Tap one and the menu adapts to your craving',pt:'Toque em um e o menu se adapta à sua vontade',fr:'Touchez-en un et le menu s’adapte à votre envie',it:'Tocca uno e il menu si adatta alla tua voglia'},
 limpiar:{es:'✕ Ver todo el menú',en:'✕ See the full menu',pt:'✕ Ver o menu completo',fr:'✕ Voir tout le menu',it:'✕ Vedi tutto il menu'},
 destEyebrow:{es:'Hoy en Amelí',en:'Today at Amelí',pt:'Hoje na Amelí',fr:'Aujourd’hui chez Amelí',it:'Oggi da Amelí'},
 destTitle:{es:'Los destacados de la casa',en:'House highlights',pt:'Os destaques da casa',fr:'Les incontournables de la maison',it:'Le specialità della casa'},
 productoDestacado:{es:'Producto destacado',en:'Featured product',pt:'Produto em destaque',fr:'Produit vedette',it:'Prodotto in evidenza'},
 vacio:{es:'Nada por acá para este momento… probá otro antojo ❧',en:'Nothing here for this moment… try another craving ❧',pt:'Nada por aqui para este momento… tente outra vontade ❧',fr:'Rien par ici pour ce moment… essayez une autre envie ❧',it:'Niente qui per questo momento… prova un’altra voglia ❧'},
 grx:{es:'Gracias por elegirnos ❧',en:'Thank you for choosing us ❧',pt:'Obrigado por nos escolher ❧',fr:'Merci de nous avoir choisis ❧',it:'Grazie per averci scelto ❧'},
 googleReview:{es:'Reseña en Google',en:'Review on Google',pt:'Avaliação no Google',fr:'Avis sur Google',it:'Recensione su Google'},
 datos:{es:'Martes a sábado · 9:00–13:00 y 17:30–21:00<br>Domingo · 17:30–21:00',
        en:'Tuesday–Saturday · 9 am–1 pm & 5:30–9 pm<br>Sunday · 5:30–9 pm',
        pt:'Terça a sábado · 9h–13h e 17h30–21h<br>Domingo · 17h30–21h',
        fr:'Mardi à samedi · 9h–13h et 17h30–21h<br>Dimanche · 17h30–21h',
        it:'Martedì a sabato · 9:00–13:00 e 17:30–21:00<br>Domenica · 17:30–21:00'},
 wsp:{es:'Pedir',en:'Order',pt:'Pedir',fr:'Commander',it:'Ordina'},
 title:{es:'Menú | Amelí Casa de Té & Brunch · Malargüe',en:'Menu | Amelí Tea House & Brunch · Malargüe',pt:'Menu | Amelí Casa de Chá & Brunch · Malargüe',fr:'Menu | Amelí Maison de thé & Brunch · Malargüe',it:'Menu | Amelí Casa del tè & Brunch · Malargüe'},
 abierto:{es:'Abierto ahora',en:'Open now',pt:'Aberto agora',fr:'Ouvert maintenant',it:'Aperto ora'},
 cerrado:{es:'Cerrado ahora',en:'Closed now',pt:'Fechado agora',fr:'Fermé maintenant',it:'Chiuso ora'},
 abreALas:{es:'Abre a las',en:'Opens at',pt:'Abre às',fr:'Ouvre à',it:'Apre alle'},
 cerrarSheet:{es:'Cerrar',en:'Close',pt:'Fechar',fr:'Fermer',it:'Chiudi'},
 pedirMensaje:{es:'Hola Amelí! Quiero pedir: ',en:'Hi Amelí! I’d like to order: ',pt:'Olá Amelí! Quero pedir: ',fr:'Bonjour Amelí ! Je voudrais commander : ',it:'Ciao Amelí! Vorrei ordinare: '},
 verDetalle:{es:'Ver detalle de',en:'View details for',pt:'Ver detalhes de',fr:'Voir le détail de',it:'Vedi dettagli di'},
 anterior:{es:'Anterior',en:'Previous',pt:'Anterior',fr:'Précédent',it:'Precedente'},
 siguiente:{es:'Siguiente',en:'Next',pt:'Próximo',fr:'Suivant',it:'Successivo'},
 irA:{es:'Ir al destacado',en:'Go to highlight',pt:'Ir para o destaque',fr:'Aller à la spécialité',it:'Vai alla specialità'},
 leche:{es:'Disponible con leche vegetal o sin lactosa',en:'Available with plant-based or lactose-free milk',pt:'Disponível com leite vegetal ou sem lactose',fr:'Disponible avec du lait végétal ou sans lactose',it:'Disponibile con latte vegetale o senza lattosio'},
 lecheVeg:{es:'Disponible con leche vegetal',en:'Available with plant-based milk',pt:'Disponível com leite vegetal',fr:'Disponible avec du lait végétal',it:'Disponibile con latte vegetale'},
 lecheLac:{es:'Disponible con leche sin lactosa',en:'Available with lactose-free milk',pt:'Disponível com leite sem lactose',fr:'Disponible avec du lait sans lactose',it:'Disponibile con latte senza lattosio'},
 a11yBtn:{es:'Accesibilidad',en:'Accessibility',pt:'Acessibilidade',fr:'Accessibilité',it:'Accessibilità'},
 a11yTitle:{es:'Accesibilidad',en:'Accessibility',pt:'Acessibilidade',fr:'Accessibilité',it:'Accessibilità'},
 a11yTexto:{es:'Tamaño de texto',en:'Text size',pt:'Tamanho do texto',fr:'Taille du texte',it:'Dimensione del testo'},
 a11yContraste:{es:'Alto contraste',en:'High contrast',pt:'Alto contraste',fr:'Contraste élevé',it:'Alto contrasto'},
 a11yMovimiento:{es:'Reducir movimiento',en:'Reduce motion',pt:'Reduzir movimento',fr:'Réduire les animations',it:'Riduci movimento'},
 a11yLectura:{es:'Lectura simple',en:'Simple reading',pt:'Leitura simples',fr:'Lecture simplifiée',it:'Lettura semplice'},
 idioma:{es:'Idioma',en:'Language',pt:'Idioma',fr:'Langue',it:'Lingua'},
 avisoAlergias:{es:'Si tenés alguna alergia o intolerancia alimentaria, informanos antes de realizar tu pedido.',en:'If you have any food allergy or intolerance, please let us know before ordering.',pt:'Se você tem alguma alergia ou intolerância alimentar, avise-nos antes de pedir.',fr:'Si vous avez une allergie ou une intolérance alimentaire, informez-nous avant de commander.',it:'Se hai un’allergia o un’intolleranza alimentare, informaci prima di ordinare.'},
 avisoMoneda:{es:'Precios expresados en pesos argentinos (ARS). Las conversiones a otras monedas son orientativas.',en:'Prices shown in Argentine pesos (ARS). Conversions to other currencies are approximate.',pt:'Preços em pesos argentinos (ARS). As conversões para outras moedas são apenas orientativas.',fr:'Prix indiqués en pesos argentins (ARS). Les conversions dans d’autres devises sont indicatives.',it:'Prezzi in pesos argentini (ARS). Le conversioni in altre valute sono indicative.'},
 buscarLabel:{es:'Buscar en el menú',en:'Search the menu',pt:'Buscar no menu',fr:'Rechercher dans le menu',it:'Cerca nel menu'},
 buscarPlaceholder:{es:'¿Qué estás buscando?',en:'What are you looking for?',pt:'O que você está procurando?',fr:'Que recherchez-vous ?',it:'Cosa stai cercando?'},
 buscarLimpiar:{es:'Limpiar búsqueda',en:'Clear search',pt:'Limpar busca',fr:'Effacer la recherche',it:'Cancella ricerca'},
 buscarSinResultados:{es:'Sin resultados para tu búsqueda',en:'No results for your search',pt:'Nenhum resultado para sua busca',fr:'Aucun résultat pour votre recherche',it:'Nessun risultato per la tua ricerca'},
 buscarResultados:{es:'resultados encontrados',en:'results found',pt:'resultados encontrados',fr:'résultats trouvés',it:'risultati trovati'},
 volverCategorias:{es:'Categorías',en:'Categories',pt:'Categorias',fr:'Catégories',it:'Categorie'},
 agotadoHoy:{es:'Agotado por hoy',en:'Sold out today',pt:'Esgotado por hoje',fr:'Épuisé pour aujourd’hui',it:'Esaurito per oggi'},
 noDisponible:{es:'No disponible temporalmente',en:'Temporarily unavailable',pt:'Temporariamente indisponível',fr:'Temporairement indisponible',it:'Temporaneamente non disponibile'},
 ultimasPorciones:{es:'Últimas porciones',en:'Last portions',pt:'Últimas porções',fr:'Dernières portions',it:'Ultime porzioni'},
};
const IDIOMA_LABEL = {es:'Español',en:'English',pt:'Português',fr:'Français',it:'Italiano'};
const CHIPS = [
 {m:'dulce', t:{es:'Algo dulce',en:'Something sweet',pt:'Algo doce',fr:'Quelque chose de sucré',it:'Qualcosa di dolce'}},
 {m:'fresco', t:{es:'Algo fresco',en:'Something fresh',pt:'Algo fresco',fr:'Quelque chose de frais',it:'Qualcosa di fresco'}},
 {m:'compartir', t:{es:'Para compartir',en:'To share',pt:'Para compartilhar',fr:'À partager',it:'Da condividere'}},
 {m:'calentito', t:{es:'Algo calentito',en:'Something warm',pt:'Algo quentinho',fr:'Quelque chose de chaud',it:'Qualcosa di caldo'}},
 {m:'llevar', t:{es:'Para llevar',en:'To go',pt:'Para levar',fr:'À emporter',it:'Da asporto'}},
];
/* íconos de línea, minimalistas, uno por categoría real (no decorativos
   sin sentido: cada uno referencia el tipo de producto de esa categoría) */
const ICONOS = {
 DYM:'<path d="M4 8h11v3a5.5 5.5 0 0 1-5.5 5.5A5.5 5.5 0 0 1 4 11V8Z"/><path d="M6.5 4.8c-.5.6-.5 1.1 0 1.7M9.5 4.8c-.5.6-.5 1.1 0 1.7"/>',
 TEH:'<path d="M4 16C4 8 10 4 16 4c0 6-4 12-12 12Z"/><path d="M5 15c3-3 6-6 10-10"/>',
 BLE:'<path d="M4 16C4 8 10 4 16 4c0 6-4 12-12 12Z"/><path d="M5 15c3-3 6-6 10-10"/><circle cx="14" cy="6" r="1" fill="currentColor" stroke="none"/>',
 TIS:'<circle cx="10" cy="10" r="1.6" fill="currentColor" stroke="none"/><path d="M10 3.5c1.4 1.4 1.4 3.2 0 4.6-1.4-1.4-1.4-3.2 0-4.6ZM10 16.5c1.4-1.4 1.4-3.2 0-4.6-1.4 1.4-1.4 3.2 0 4.6ZM3.5 10c1.4-1.4 3.2-1.4 4.6 0-1.4 1.4-3.2 1.4-4.6 0ZM16.5 10c-1.4-1.4-3.2-1.4-4.6 0 1.4 1.4 3.2 1.4 4.6 0Z"/>',
 CCL:'<path d="M4 8h10v4a5 5 0 0 1-5 5 5 5 0 0 1-5-5V8Z"/><path d="M14 9.5h1.2a2 2 0 0 1 0 4H14"/>',
 ESP:'<path d="M10 2.5l1.8 5.4 5.7.1-4.6 3.5 1.7 5.5-4.6-3.4-4.6 3.4 1.7-5.5-4.6-3.5 5.7-.1Z"/>',
 CFR:'<path d="M6 4h8l-1 12a2 2 0 0 1-2 1.8H9A2 2 0 0 1 7 16L6 4Z"/><path d="M7 8h6M7.6 11h4.8"/>',
 BYJ:'<path d="M6 6h8l-.9 9.5A2 2 0 0 1 11.1 17H8.9a2 2 0 0 1-2-1.5L6 6Z"/><path d="M12 6 14 2"/>',
 DEL:'<path d="M3 15 10 5l7 10Z"/><path d="M3 15h14"/><circle cx="10" cy="8.5" r="1" fill="currentColor" stroke="none"/>',
 SAT:'<path d="M3 8l7-4 7 4"/><path d="M4 8h12l-1.2 6.5a2 2 0 0 1-2 1.5H7.2a2 2 0 0 1-2-1.5L4 8Z"/><path d="M5.5 11h9"/>',
 TYT:'<path d="M3 15 10 5l7 10Z"/><path d="M3 15h14"/><circle cx="10" cy="8.5" r="1" fill="currentColor" stroke="none"/>',
 STC:'<path d="M10 17V6"/><path d="M10 6c-2 0-3-1-3-3M10 6c2 0 3-1 3-3M10 10c-2 0-3-1-3-3M10 10c2 0 3-1 3-3"/><path d="M4 4l12 12"/>',
};
const BADGES = {
 fav:{c:'fav', t:{es:'Favorito de la casa',en:'House favourite',pt:'Favorito da casa',fr:'Favori de la maison',it:'Preferito della casa'}},
 reco:{c:'reco', t:{es:'Recomendado',en:'Recommended',pt:'Recomendado',fr:'Recommandé',it:'Consigliato'}},
 pedido:{c:'pedido', t:{es:'Más pedido',en:'Most ordered',pt:'Mais pedido',fr:'Le plus commandé',it:'Il più ordinato'}},
 nuevo:{c:'nuevo', t:{es:'Nuevo',en:'New',pt:'Novo',fr:'Nouveau',it:'Nuovo'}},
 sintacc:{c:'sintacc', t:{es:'Sin TACC',en:'Gluten free',pt:'Sem glúten',fr:'Sans gluten',it:'Senza glutine'}},
};
/* alergenos validados por producto: veg/vgn/tacc/lac son afirmaciones
   positivas (se muestran solo si son true); el resto son "contiene X"
   (se muestra solo si es true). Todo esto llega vacio/ausente hasta que
   la cocina valida cada producto en el Excel -- ver extract.py. */
const ALERG_POSITIVOS = ['veg','vgn','tacc','lac'];
const ALERG_TXT = {
 veg:{es:'Vegetariano',en:'Vegetarian',pt:'Vegetariano',fr:'Végétarien',it:'Vegetariano'},
 vgn:{es:'Vegano',en:'Vegan',pt:'Vegano',fr:'Végan',it:'Vegano'},
 tacc:{es:'Sin TACC',en:'Gluten-free',pt:'Sem glúten',fr:'Sans gluten',it:'Senza glutine'},
 lac:{es:'Sin lactosa',en:'Lactose-free',pt:'Sem lactose',fr:'Sans lactose',it:'Senza lattosio'},
 glu:{es:'Gluten',en:'Gluten',pt:'Glúten',fr:'Gluten',it:'Glutine'},
 lech:{es:'Leche',en:'Milk',pt:'Leite',fr:'Lait',it:'Latte'},
 huev:{es:'Huevo',en:'Egg',pt:'Ovo',fr:'Œuf',it:'Uovo'},
 soja:{es:'Soja',en:'Soy',pt:'Soja',fr:'Soja',it:'Soia'},
 mani:{es:'Maní',en:'Peanuts',pt:'Amendoim',fr:'Arachides',it:'Arachidi'},
 fsec:{es:'Frutos secos',en:'Tree nuts',pt:'Frutos secos',fr:'Fruits à coque',it:'Frutta a guscio'},
 ses:{es:'Sésamo',en:'Sesame',pt:'Gergelim',fr:'Sésame',it:'Sesamo'},
 pesc:{es:'Pescado',en:'Fish',pt:'Peixe',fr:'Poisson',it:'Pesce'},
 mar:{es:'Mariscos',en:'Shellfish',pt:'Frutos do mar',fr:'Fruits de mer',it:'Frutti di mare'},
 alc:{es:'Alcohol',en:'Alcohol',pt:'Álcool',fr:'Alcool',it:'Alcol'},
 caf:{es:'Cafeína',en:'Caffeine',pt:'Cafeína',fr:'Caféine',it:'Caffeina'},
};
const ALERG_CONTIENE = {es:'Contiene',en:'Contains',pt:'Contém',fr:'Contient',it:'Contiene'};
const CAT_NOTAS = {
 BYJ:{es:'Vaso o jarra',en:'By the glass or by the jug',pt:'Copo ou jarra',fr:'Verre ou pichet',it:'Bicchiere o caraffa'},
 STC:{es:'Producto tercerizado',en:'Outsourced product',pt:'Produto terceirizado',fr:'Produit d’un tiers',it:'Prodotto di terzi'},
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
 en:`<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" focusable="false"><clipPath id="cEN"><circle cx="10" cy="10" r="9.5"/></clipPath><g clip-path="url(#cEN)">
   <rect x="0" width="10" height="20" fill="#0A247D"/>
   <rect x="0" y="8.5" width="10" height="3" fill="#FFFFFF"/>
   <rect x="0" y="9.3" width="10" height="1.4" fill="#CF142B"/>
   <rect x="4.3" width="1.4" height="20" fill="#FFFFFF"/>
   <rect x="4.65" width="0.7" height="20" fill="#CF142B"/>
   <rect x="10" width="10" height="20" fill="#FFFFFF"/>
   <rect x="10" y="0" width="10" height="2.85" fill="#B22234"/>
   <rect x="10" y="5.7" width="10" height="2.85" fill="#B22234"/>
   <rect x="10" y="11.4" width="10" height="2.85" fill="#B22234"/>
   <rect x="10" y="17.1" width="10" height="2.85" fill="#B22234"/>
   <rect x="10" y="0" width="5" height="8.5" fill="#3C3B6E"/>
   <circle cx="11.3" cy="2.3" r="0.5" fill="#FFFFFF"/><circle cx="13.2" cy="2.3" r="0.5" fill="#FFFFFF"/>
   <circle cx="12.2" cy="4.2" r="0.5" fill="#FFFFFF"/>
   <circle cx="11.3" cy="6.1" r="0.5" fill="#FFFFFF"/><circle cx="13.2" cy="6.1" r="0.5" fill="#FFFFFF"/>
 </g><circle cx="10" cy="10" r="9.2" fill="none" stroke="currentColor" stroke-width="1" opacity=".4"/></svg>`,
 pt:`<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" focusable="false"><clipPath id="cBR"><circle cx="10" cy="10" r="9.5"/></clipPath><g clip-path="url(#cBR)"><rect width="20" height="20" fill="#2E9B4F"/><polygon points="10,3.3 17,10 10,16.7 3,10" fill="#F5D948"/><circle cx="10" cy="10" r="2.8" fill="#2B4B8C"/></g><circle cx="10" cy="10" r="9.2" fill="none" stroke="currentColor" stroke-width="1" opacity=".4"/></svg>`,
 fr:`<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" focusable="false"><clipPath id="cFR"><circle cx="10" cy="10" r="9.5"/></clipPath><g clip-path="url(#cFR)"><rect width="6.7" height="20" fill="#0055A4"/><rect x="6.7" width="6.6" height="20" fill="#FFFFFF"/><rect x="13.3" width="6.7" height="20" fill="#EF4135"/></g><circle cx="10" cy="10" r="9.2" fill="none" stroke="currentColor" stroke-width="1" opacity=".4"/></svg>`,
 it:`<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" focusable="false"><clipPath id="cIT"><circle cx="10" cy="10" r="9.5"/></clipPath><g clip-path="url(#cIT)"><rect width="6.7" height="20" fill="#009246"/><rect x="6.7" width="6.6" height="20" fill="#FFFFFF"/><rect x="13.3" width="6.7" height="20" fill="#CE2B37"/></g><circle cx="10" cy="10" r="9.2" fill="none" stroke="currentColor" stroke-width="1" opacity=".4"/></svg>`,
};

let lang='es', moodActivo=null, sheetProdId=null, terminoBusqueda='';
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

/* precio en pesos siempre; USD como referencia siempre que este cargado
   (lo pidio el dueño para cualquier idioma); EUR ademas solo para FR/IT,
   los idiomas de zona euro. Los dos equivalentes son fijos del ultimo
   build (tasa manual del Excel), no una cotizacion en vivo -- ver README. */
function textoPrecio(entry){
  if(!entry) return '';
  let extra = [];
  if(entry.usd) extra.push(esc(entry.usd));
  if(entry.eur && (lang==='fr' || lang==='it')) extra.push(esc(entry.eur));
  if(entry.brl && lang==='pt') extra.push(esc(entry.brl));
  return extra.length ? `${esc(entry.ars)} <small>(${extra.join(' · ')})</small>` : esc(entry.ars);
}

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
function saludoHorario(){
  const h = Math.floor(ahoraMendoza().min/60);
  if(h<12) return UI.buenosDias[lang];
  if(h<19) return UI.buenasTardes[lang];
  return UI.buenasNoches[lang];
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
  $('sheetEtiquetas').innerHTML = p.b.map(k=>`<span class="badge ${BADGES[k].c}">${BADGES[k].t[lang]}</span>`).join('') + dispBadge(p);
  /* "etiqueta inicial" es un texto editorial libre, cargado solo en
     espanol en el Excel -- se muestra unicamente en ese idioma para no
     mezclar espanol sin traducir con el resto de la ficha. */
  const sheetTag = $('sheetTag');
  if(p.tag && lang==='es'){ sheetTag.textContent = p.tag; sheetTag.hidden = false; }
  else { sheetTag.hidden = true; }
  const alergenos = $('sheetAlergenos');
  if(p.alerg){
    const positivos = ALERG_POSITIVOS.filter(k=>p.alerg[k]);
    const contiene = Object.keys(p.alerg).filter(k=>!ALERG_POSITIVOS.includes(k) && p.alerg[k]);
    let html = positivos.map(k=>`<span class="alerg-tag positivo">${esc(ALERG_TXT[k][lang])}</span>`).join('');
    if(contiene.length){
      html += `<span class="alerg-tag advertencia">${esc(ALERG_CONTIENE[lang])}: ${contiene.map(k=>esc(ALERG_TXT[k][lang])).join(', ')}</span>`;
    }
    alergenos.innerHTML = html;
    alergenos.hidden = !html;
  } else {
    alergenos.innerHTML = ''; alergenos.hidden = true;
  }
  /* opcion de leche vegetal/sin lactosa: agregado para bebidas con leche,
     no es un producto aparte (ver extract.py, load_opciones_leche) */
  const sheetLeche = $('sheetLeche');
  if(p.leche && p.leche.length===2){ sheetLeche.textContent = UI.leche[lang]; sheetLeche.hidden = false; }
  else if(p.leche && p.leche.includes('veg')){ sheetLeche.textContent = UI.lecheVeg[lang]; sheetLeche.hidden = false; }
  else if(p.leche && p.leche.includes('lac')){ sheetLeche.textContent = UI.lecheLac[lang]; sheetLeche.hidden = false; }
  else { sheetLeche.hidden = true; }
  const foto=$('sheetFoto');
  foto.className = 'sheet-foto';
  foto.querySelector('img')?.remove();
  if(p.img){
    const img = document.createElement('img');
    img.src = p.img; img.alt = altProducto(p);
    foto.appendChild(img);
    $('sheetInicial').hidden = true;
  } else {
    foto.classList.add(`grad-${Math.abs(hashId(p.id))%3}`);
    $('sheetInicial').hidden = false;
    $('sheetInicial').textContent=p.n[lang].charAt(0);
  }
  /* si está agotado o no disponible, no tiene sentido ofrecer pedirlo por
     WhatsApp -- el badge ya explica por qué. "Últimas porciones" sigue
     disponible, así que ahí el botón se mantiene. */
  const noPedible = p.disp==='agotado' || p.disp==='no_disp';
  if(WSP_NUMBER && !noPedible){
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

/* ---------- panel de accesibilidad ---------- */
let a11yFocoPrevio=null;
function aplicarA11y(){
  const html=document.documentElement;
  html.style.setProperty('--afs', a11yPrefs.afs || 1);
  if(a11yPrefs.contraste) html.setAttribute('data-contraste','alto'); else html.removeAttribute('data-contraste');
  if(a11yPrefs.movimiento) html.setAttribute('data-movimiento','reducido'); else html.removeAttribute('data-movimiento');
  if(a11yPrefs.lectura) html.setAttribute('data-lectura','simple'); else html.removeAttribute('data-lectura');
  document.querySelectorAll('.a11y-opts button').forEach(b=>{
    b.setAttribute('aria-pressed', String(Number(b.dataset.afs)===Number(a11yPrefs.afs||1)));
  });
  $('a11yContraste').checked = !!a11yPrefs.contraste;
  $('a11yMovimiento').checked = !!a11yPrefs.movimiento;
  $('a11yLectura').checked = !!a11yPrefs.lectura;
}
function abrirA11y(){
  a11yFocoPrevio=document.activeElement;
  $('a11yBackdrop').hidden=false; $('a11yPanel').hidden=false;
  requestAnimationFrame(()=>{ $('a11yBackdrop').classList.add('abierto'); $('a11yPanel').classList.add('abierto'); });
  $('a11yBtn').setAttribute('aria-expanded','true');
  $('a11yPanel').focus();
  document.addEventListener('keydown', onA11yKeydown);
}
function cerrarA11y(){
  $('a11yBackdrop').classList.remove('abierto');
  $('a11yPanel').classList.remove('abierto');
  $('a11yBtn').setAttribute('aria-expanded','false');
  document.removeEventListener('keydown', onA11yKeydown);
  setTimeout(()=>{ $('a11yBackdrop').hidden=true; $('a11yPanel').hidden=true; },220);
  if(a11yFocoPrevio && a11yFocoPrevio.focus) a11yFocoPrevio.focus();
}
function onA11yKeydown(e){
  if(e.key==='Escape'){ cerrarA11y(); return; }
  if(e.key==='Tab'){
    const focosables=$('a11yPanel').querySelectorAll('button, input');
    if(!focosables.length) return;
    const primero=focosables[0], ultimo=focosables[focosables.length-1];
    if(e.shiftKey && document.activeElement===primero){ e.preventDefault(); ultimo.focus(); }
    else if(!e.shiftKey && document.activeElement===ultimo){ e.preventDefault(); primero.focus(); }
  }
}
$('a11yBtn').addEventListener('click', abrirA11y);
$('a11yCerrar').addEventListener('click', cerrarA11y);
$('a11yBackdrop').addEventListener('click', cerrarA11y);
document.querySelectorAll('.a11y-opts button').forEach(b=>{
  b.addEventListener('click', ()=>{ a11yPrefs.afs=Number(b.dataset.afs); guardarA11y(a11yPrefs); aplicarA11y(); });
});
$('a11yContraste').addEventListener('change', e=>{ a11yPrefs.contraste=e.target.checked; guardarA11y(a11yPrefs); aplicarA11y(); });
$('a11yMovimiento').addEventListener('change', e=>{ a11yPrefs.movimiento=e.target.checked; guardarA11y(a11yPrefs); aplicarA11y(); });
$('a11yLectura').addEventListener('change', e=>{ a11yPrefs.lectura=e.target.checked; guardarA11y(a11yPrefs); aplicarA11y(); });
aplicarA11y();

/* ---------- selector de idioma (desplegable) ---------- */
function abrirLangs(){
  $('langsMenu').hidden=false;
  $('langsBtn').setAttribute('aria-expanded','true');
  document.addEventListener('click', onLangsOutsideClick);
  document.addEventListener('keydown', onLangsKeydown);
  const actual=$('langsMenu').querySelector('button[aria-selected="true"]');
  if(actual) actual.focus();
}
function cerrarLangs(){
  $('langsMenu').hidden=true;
  $('langsBtn').setAttribute('aria-expanded','false');
  document.removeEventListener('click', onLangsOutsideClick);
  document.removeEventListener('keydown', onLangsKeydown);
}
function onLangsOutsideClick(e){ if(!$('langs').contains(e.target)) cerrarLangs(); }
function onLangsKeydown(e){
  if(e.key==='Escape'){ cerrarLangs(); $('langsBtn').focus(); return; }
  if(e.key==='Tab'){
    const focosables=$('langsMenu').querySelectorAll('button');
    if(!focosables.length) return;
    const primero=focosables[0], ultimo=focosables[focosables.length-1];
    if(e.shiftKey && document.activeElement===primero){ e.preventDefault(); ultimo.focus(); }
    else if(!e.shiftKey && document.activeElement===ultimo){ e.preventDefault(); primero.focus(); }
  }
}
$('langsBtn').addEventListener('click', ()=>{ $('langsMenu').hidden ? abrirLangs() : cerrarLangs(); });

/* ---------- buscador ---------- */
$('buscarInput').addEventListener('input', e=>{
  terminoBusqueda=e.target.value;
  $('buscarLimpiar').hidden=!terminoBusqueda;
  aplicarFiltro();
});
$('buscarLimpiar').addEventListener('click', ()=>{
  terminoBusqueda=''; $('buscarInput').value=''; $('buscarLimpiar').hidden=true;
  aplicarFiltro(); $('buscarInput').focus();
});

/* ---------- volver a categorías ---------- */
$('btnVolver').addEventListener('click', ()=>{
  const destino=$('navcat');
  destino.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});
  destino.querySelector('a')?.focus({preventScroll:true});
});
window.addEventListener('scroll', ()=>{
  $('btnVolver').classList.toggle('visible', window.scrollY > window.innerHeight*1.4);
}, {passive:true});

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
  $('heroSaludo').textContent=saludoHorario();
  $('heroPregunta').textContent=UI.antojoHoy[lang];
  $('momTitle').innerHTML=UI.momTitle[lang];
  $('momHint').textContent=UI.momHint[lang];
  $('limpiar').textContent=UI.limpiar[lang];
  $('destEyebrow').textContent=UI.destEyebrow[lang];
  $('destTitle').textContent=UI.destTitle[lang];
  $('footGrx').textContent=UI.grx[lang];
  if($('footGoogleTxt')) $('footGoogleTxt').textContent=UI.googleReview[lang];
  $('footDatos').innerHTML=UI.datos[lang];
  $('a11yBtn').setAttribute('aria-label', UI.a11yBtn[lang]);
  $('a11yTitle').textContent=UI.a11yTitle[lang];
  $('a11yTextoLabel').textContent=UI.a11yTexto[lang];
  $('a11yContrasteLabel').textContent=UI.a11yContraste[lang];
  $('a11yMovimientoLabel').textContent=UI.a11yMovimiento[lang];
  $('a11yLecturaLabel').textContent=UI.a11yLectura[lang];
  $('a11yCerrar').setAttribute('aria-label', UI.cerrarSheet[lang]);
  $('carPrev').setAttribute('aria-label', UI.anterior[lang]);
  $('carNext').setAttribute('aria-label', UI.siguiente[lang]);
  pintarEstado();
  /* selector de idioma */
  $('langsBtnTxt').textContent=lang.toUpperCase();
  $('langsBtn').setAttribute('aria-label', `${UI.idioma[lang]}: ${IDIOMA_LABEL[lang]}`);
  $('langsMenu').innerHTML=LANGS.map(l=>`<li><button type="button" role="option" data-l="${l}" aria-selected="${l===lang}">${esc(IDIOMA_LABEL[l])}</button></li>`).join('');
  $('langsMenu').querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{
    lang=b.dataset.l; cerrarLangs(); render(); aplicarFiltro();
    if(sheetProdId) abrirDetalle(sheetProdId);  /* si hay un panel de detalle abierto, refrescarlo tambien */
  }));
  /* aviso de alergias, moneda y buscador */
  $('avisoAlergias').textContent=UI.avisoAlergias[lang];
  $('avisoMoneda').textContent=UI.avisoMoneda[lang];
  $('buscarInput').placeholder=UI.buscarPlaceholder[lang];
  $('buscarLabel').textContent=UI.buscarLabel[lang];
  $('buscarLimpiar').setAttribute('aria-label', UI.buscarLimpiar[lang]);
  $('btnVolverTxt').textContent=UI.volverCategorias[lang];
  /* chips */
  $('chips').innerHTML=CHIPS.map(ch=>`<button class="chip ${moodActivo===ch.m?'activo':''}" data-mood="${ch.m}">${ch.t[lang]}</button>`).join('');
  document.querySelectorAll('.chip').forEach(ch=>ch.addEventListener('click',()=>{
    moodActivo = moodActivo===ch.dataset.mood ? null : ch.dataset.mood;
    render(); aplicarFiltro();
    if(moodActivo) $('menu').scrollIntoView({behavior:'smooth',block:'start'});
  }));
  $('limpiar').onclick=()=>{moodActivo=null;render();aplicarFiltro();};
  $('navcat').innerHTML=CATS.map(c=>`<a href="#${esc(c.cod)}">${esc(c.nom[lang])}</a>`).join('');
  $('catIcons').innerHTML=CATS.map(c=>`<a href="#${esc(c.cod)}"><svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONOS[c.cod]||ICONOS.CCL}</svg><span>${esc(c.nom[lang])}</span></a>`).join('');
  /* carrusel destacados */
  $('carrusel').innerHTML=PRODS.filter(p=>p.dest).map((p,i)=>{
    const bd=p.b.map(k=>`<span class="badge ${BADGES[k].c}">${BADGES[k].t[lang]}</span>`).join('') + dispBadge(p);
    const fotoContenido = p.img
      ? `<img src="${esc(p.img)}" alt="${esc(altProducto(p))}" loading="lazy">`
      : `<span class="inicial">${esc(p.n[lang].charAt(0))}</span>`;
    return `<article class="dcard" data-id="${esc(p.id)}" role="button" tabindex="0" aria-label="${esc(UI.verDetalle[lang])} ${esc(p.n[lang])}">
      <div class="foto ${p.img?'':`grad-${i%3}`}">${fotoContenido}</div>
      <div class="cuerpo">${bd}<h3>${esc(p.n[lang])}</h3><p>${esc(p.d[lang])}</p></div></article>`;
  }).join('');
  document.querySelectorAll('.dcard').forEach(card=>{
    card.addEventListener('click', ()=>abrirDetalle(card.dataset.id));
    card.addEventListener('keydown', e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); abrirDetalle(card.dataset.id); } });
  });
  initCarrusel();
  /* secciones */
  $('menu').innerHTML=CATS.map(cat=>{
    const items=PRODS.filter(p=>p.cat===cat.cod);
    if(!items.length) return '';
    const nota=CAT_NOTAS[cat.cod]?`<p class="desc-cat">${CAT_NOTAS[cat.cod][lang]}</p>`:'';
    /* el primer producto marcado "Destacado" de la categoría se muestra
       como panel grande (foto + descripción); el resto va en la grilla
       compacta de 2 columnas, sin descripción (se ve al abrir la ficha) */
    const destacado=items.find(p=>p.dest);
    const resto=destacado?items.filter(p=>p!==destacado):items;
    const panel=destacado?renderDestacadoCategoria(destacado, cat):'';
    const cards=resto.map((p,i)=>renderCardCompacta(p, cat, i)).join('');
    return `<section class="cat" id="${esc(cat.cod)}"><header><h2>${esc(cat.nom[lang])}</h2>${nota}</header>
      ${panel}<div class="lista">${cards}</div><p class="vacio">${UI.vacio[lang]}</p></section>`;
  }).join('');
  document.querySelectorAll('main .prod').forEach(card=>{
    card.addEventListener('click', ()=>abrirDetalle(card.dataset.id));
    card.addEventListener('keydown', e=>{ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); abrirDetalle(card.dataset.id); } });
  });
  observarNav();
  observarCategorias();
}
function normalizar(s){
  return String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
}
function altProducto(p){
  return (p.alt && p.alt[lang]) || p.n[lang];
}
function fotoOInicial(p){
  return p.img
    ? `<img src="${esc(p.img)}" alt="${esc(altProducto(p))}" loading="lazy">`
    : `<span class="inicial">${esc(p.n[lang].charAt(0))}</span>`;
}
function renderDestacadoCategoria(p, cat){
  const bd=p.b.map(k=>`<span class="badge ${BADGES[k].c}">${BADGES[k].t[lang]}</span>`).join('') + dispBadge(p);
  const precio=PRECIOS[p.id]?`<span class="precio">${textoPrecio(PRECIOS[p.id])}</span>`:'';
  return `<article class="prod destacado-cat" data-moods="${p.m.join(',')}" data-haystack="${esc(haystackProducto(p, cat))}" data-id="${esc(p.id)}" role="button" tabindex="0" aria-label="${esc(UI.verDetalle[lang])} ${esc(p.n[lang])}${p.disp?', '+esc(dispTexto(p)):''}">
    <div class="prod-inner">
      <div class="foto ${p.img?'':`grad-${Math.abs(hashId(p.id))%3}`}">${fotoOInicial(p)}</div>
      <div class="cont"><p class="eyebrow-cat">${esc(UI.productoDestacado[lang])}</p><h3>${esc(p.n[lang])}</h3><p class="desc">${esc(p.d[lang])}</p><div class="fila">${precio}${bd}</div></div>
    </div></article>`;
}
function renderCardCompacta(p, cat, i){
  const bd=p.b.map(k=>`<span class="badge ${BADGES[k].c}">${BADGES[k].t[lang]}</span>`).join('') + dispBadge(p);
  const precio=PRECIOS[p.id]?`<span class="precio">${textoPrecio(PRECIOS[p.id])}</span>`:'';
  return `<article class="prod compacta stagger-${Math.min(i,9)}" data-moods="${p.m.join(',')}" data-haystack="${esc(haystackProducto(p, cat))}" data-id="${esc(p.id)}" role="button" tabindex="0" aria-label="${esc(UI.verDetalle[lang])} ${esc(p.n[lang])}${p.disp?', '+esc(dispTexto(p)):''}">
    <div class="prod-inner">
      <div class="foto ${p.img?'':`grad-${i%3}`}">${fotoOInicial(p)}</div>
      <div class="cont"><h3>${esc(p.n[lang])}</h3>${precio}${bd?`<div class="etiquetas">${bd}</div>`:''}</div>
    </div></article>`;
}
function dispTexto(p){
  if(p.disp==='agotado') return UI.agotadoHoy[lang];
  if(p.disp==='no_disp') return UI.noDisponible[lang];
  if(p.disp==='ultimas') return UI.ultimasPorciones[lang];
  return '';
}
function dispBadge(p){
  if(p.disp==='agotado') return `<span class="badge agotado">${esc(UI.agotadoHoy[lang])}</span>`;
  if(p.disp==='no_disp') return `<span class="badge no-disp">${esc(UI.noDisponible[lang])}</span>`;
  if(p.disp==='ultimas') return `<span class="badge ultimas">${esc(UI.ultimasPorciones[lang])}</span>`;
  return '';
}
function haystackProducto(p, cat){
  const partes=[p.n[lang], p.d[lang], cat?cat.nom[lang]:'', p.b.map(k=>BADGES[k]?BADGES[k].t[lang]:'').join(' ')];
  if(p.alerg){ ALERG_POSITIVOS.forEach(k=>{ if(p.alerg[k]) partes.push(ALERG_TXT[k][lang]); }); }
  return normalizar(partes.join(' '));
}
function aplicarFiltro(){
  const termino=normalizar(terminoBusqueda);
  document.querySelectorAll('.prod').forEach(p=>{
    const moods=(p.dataset.moods||'').split(',');
    const moodOk=!moodActivo || moods.includes(moodActivo);
    const textoOk=!termino || (p.dataset.haystack||'').includes(termino);
    p.classList.toggle('oculto', !(moodOk && textoOk));
  });
  document.querySelectorAll('section.cat').forEach(sec=>{
    sec.classList.toggle('sin-resultados', sec.querySelectorAll('.prod:not(.oculto)').length===0);
  });
  $('limpiar').classList.toggle('visible', !!moodActivo);
  actualizarResultadosBusqueda();
}
function actualizarResultadosBusqueda(){
  const el=$('buscarResultados');
  if(!terminoBusqueda){ el.textContent=''; return; }
  const visibles=document.querySelectorAll('.prod:not(.oculto)').length;
  el.textContent = visibles===0 ? UI.buscarSinResultados[lang] : `${visibles} ${UI.buscarResultados[lang]}`;
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
