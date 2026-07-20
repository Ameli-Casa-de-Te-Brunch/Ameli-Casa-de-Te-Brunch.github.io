/**
 * Backend de "me gusta" para el menú Amelí — Google Apps Script Web App.
 * Ver backend/apps-script/README.md para instrucciones de despliegue.
 *
 * Hoja esperada: una pestaña llamada "Votos" con encabezados en la fila 1:
 *   A: producto_id   B: cuenta
 */

const SHEET_NAME = 'Votos';

function _sheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(['producto_id', 'cuenta']);
  }
  return sheet;
}

function _leerTodos() {
  const sheet = _sheet();
  const values = sheet.getDataRange().getValues();
  const out = {};
  for (let i = 1; i < values.length; i++) {
    const id = values[i][0];
    if (id) out[id] = Number(values[i][1]) || 0;
  }
  return out;
}

function _incrementar(id) {
  const sheet = _sheet();
  const values = sheet.getDataRange().getValues();
  for (let i = 1; i < values.length; i++) {
    if (values[i][0] === id) {
      const nuevo = (Number(values[i][1]) || 0) + 1;
      sheet.getRange(i + 1, 2).setValue(nuevo);
      return nuevo;
    }
  }
  sheet.appendRow([id, 1]);
  return 1;
}

function _json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

/** GET: devuelve {producto_id: cuenta, ...} para pintar los contadores al cargar la página. */
function doGet(e) {
  return _json(_leerTodos());
}

/**
 * POST: incrementa el contador de un producto. Body: {"id":"TYT001"}
 * El cliente debe mandar Content-Type: text/plain (no application/json) para
 * evitar el preflight CORS que Apps Script no responde correctamente.
 */
function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    const id = String(body.id || '').trim();
    if (!id) throw new Error('id requerido');

    const lock = LockService.getScriptLock();
    lock.waitLock(5000);
    let nuevo;
    try {
      nuevo = _incrementar(id);
    } finally {
      lock.releaseLock();
    }
    return _json({ ok: true, id: id, cuenta: nuevo });
  } catch (err) {
    return _json({ ok: false, error: String(err) });
  }
}
