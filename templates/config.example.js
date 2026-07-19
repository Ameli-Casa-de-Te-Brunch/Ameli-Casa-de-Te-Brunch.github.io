/* Copiá este archivo como config.js (gitignoreado, no se sube al repo público)
   para probar el sistema de "me gusta" en local. En producción, el workflow de
   GitHub Actions genera dist/config.js desde el secret VOTOS_ENDPOINT — ver
   backend/apps-script/README.md */
window.AMELI_CONFIG = {
  votosEndpoint: "" // URL del Web App de Google Apps Script, ej: "https://script.google.com/macros/s/AKfycb.../exec"
};
