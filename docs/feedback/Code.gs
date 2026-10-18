/**
 * Wheels & Bones — приём замечаний игроков в Google-таблицу.
 * Вставить в таблицу: Расширения → Apps Script → этот файл → Развернуть → Веб-приложение
 * (Выполнять от имени: я; Доступ: все). Подробно — docs/FEEDBACK_SETUP.md.
 *
 * Игра шлёт POST с JSON (text/plain). Строка попадает на лист «Feedback»; уменьшенный снимок экрана
 * (JPEG, если есть) — в папку Google Диска «Wheels & Bones — feedback screenshots», в таблицу — ссылка.
 */
const KEY = "wnb-feedback-1";        // тот же ключ, что FEEDBACK_KEY в game.py (отсекает случайный мусор)
const MAX_PER_DAY = 300;             // не больше стольких замечаний в сутки
const SHEET = "Feedback";
const FOLDER = "Wheels & Bones — feedback screenshots";
const HEADERS = ["Received", "Player time", "Version", "Platform", "Language", "Screen", "Job", "Title",
                 "Phase", "Step", "Type", "Reason", "Game expected", "Player chose", "Game message",
                 "Comment", "Screenshot"];

function doPost(e) {
  try {
    const d = JSON.parse(e.postData.contents);
    if (d.key !== KEY) return reply_(false, "key");
    const props = PropertiesService.getScriptProperties();
    const day = "n_" + Utilities.formatDate(new Date(), "UTC", "yyyy-MM-dd");
    const n = Number(props.getProperty(day) || 0);
    if (n >= MAX_PER_DAY) return reply_(false, "limit");
    props.setProperty(day, String(n + 1));

    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName(SHEET) || ss.insertSheet(SHEET);
    if (sh.getLastRow() === 0) sh.appendRow(HEADERS);
    const head = sh.getRange(1, 1, 1, HEADERS.length);
    if (head.getValues()[0].join("|") !== HEADERS.join("|")) {   // старые (русские) заголовки — переписать
      head.setValues([HEADERS]).setFontWeight("bold");
      sh.setFrozenRows(1);
    }
    let shot = "";
    const b64 = String(d.screenshot_jpg_b64 || "");
    if (b64 && b64.length < 600000) {
      const blob = Utilities.newBlob(Utilities.base64Decode(b64), "image/jpeg",
                                     "shot_" + new Date().toISOString().replace(/[:.]/g, "-") + ".jpg");
      shot = folder_().createFile(blob).getUrl();
    }
    sh.appendRow([new Date(), cell_(d.time), cell_(d.version), cell_(d.platform), cell_(d.lang), cell_(d.scene),
                  cell_(d.job), cell_(d.title), cell_(d.phase), cell_(d.step), cell_(d.kind), cell_(d.reason),
                  cell_(d.expected), cell_(d.got), cell_(d.game_message), cell_(d.comment, 2000), shot]);
    return reply_(true, "");
  } catch (err) {
    return reply_(false, "error");
  }
}

// Текст в ячейку: обрезать и не дать выполниться «формуле» (=, +, -, @ в начале).
function cell_(v, max) {
  let s = String(v === undefined || v === null ? "" : v).slice(0, max || 500);
  if (/^[=+\-@]/.test(s)) s = "'" + s;
  return s;
}

function folder_() {
  const props = PropertiesService.getScriptProperties();
  const id = props.getProperty("folder_id");
  if (id) {
    try {
      const old = DriveApp.getFolderById(id);
      if (old.getName() !== FOLDER) old.setName(FOLDER);
      return old;
    } catch (e) {}
  }
  const f = DriveApp.createFolder(FOLDER);
  props.setProperty("folder_id", f.getId());
  return f;
}

function reply_(ok, why) {
  return ContentService.createTextOutput(JSON.stringify({ ok: ok, why: why }))
                       .setMimeType(ContentService.MimeType.JSON);
}

// Проверка из редактора: Выполнить → testPost (добавит тестовую строку).
function testPost() {
  const r = doPost({ postData: { contents: JSON.stringify({ key: KEY, time: "test", version: "test",
    platform: "editor", lang: "en", scene: "hub", kind: "general", reason: "Test", comment: "Test row" }) } });
  Logger.log(r.getContent());
}
