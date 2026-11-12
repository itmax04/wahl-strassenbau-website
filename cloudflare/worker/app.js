/**
 * Formular-Endpunkt POST /kontakt.php für Cloudflare Workers — Portierung von server/ (ADR-0001) ohne PHP.
 * Ablauf wie FormHandler.php: POST → Origin/Referer → Honeypot (stiller Erfolg) → Mindestzeit (stiller Erfolg)
 * → Rate-Limit (429) → Validierung (422) → D1 → Mail an Inhaber → bei Widerruf Eingangsbestätigung → mail_status → Antwort.
 * Antworten (JSON für fetch, 303/HTML ohne JavaScript) sind dieselben wie bei kontakt.php, main.js bleibt unverändert.
 * Texte: server/messages.json, Markup: server/templates/ (build.py) — beides über generated.js (cloudflare/build.py).
 */
import { MESSAGES as M, TEMPLATES } from './generated.js';
import { Message, mailer } from './mail.js';

/** Gleiche Liste wie build.py → SERVICES und Validator.php. */
export const SERVICES = ['Pflasterarbeiten', 'Garten & Landschaft', 'Asphalt- & Erdarbeiten', 'Havarie', 'Sonstiges'];
export const FORMS = ['kontakt', 'kurz', 'widerruf'];
const PHONE_RE = /^[0-9+()\/\s.\-]{5,40}$/;
const PHONE_HREF = 'tel:+4938125223941';
const MAX_BODY = 100_000;

/** Feld → [Typ, Maximallänge] */
const FIELDS = {
  name: ['line', 100], email: ['line', 200], telefon: ['line', 40], leistung: ['line', 60],
  nachricht: ['text', 5000], bestellnummer: ['line', 100], artikel: ['text', 300],
};
const REQUIRED = {
  kontakt: ['name', 'email', 'nachricht'],
  kurz: ['name', 'telefon', 'nachricht'],
  widerruf: ['name', 'bestellnummer', 'email'],
};
/** Nur die Felder des jeweiligen Formulars behalten (Datensparsamkeit). */
const KEEP = {
  kontakt: ['name', 'email', 'telefon', 'leistung', 'nachricht'],
  kurz: ['name', 'telefon', 'nachricht'],
  widerruf: ['name', 'bestellnummer', 'email', 'artikel', 'nachricht'],
};

/** Standardwerte wie server/bootstrap.php; Werte aus wrangler.jsonc «vars» bzw. Secrets haben Vorrang. */
const DEFAULTS = {
  RECIPIENT: 'info@wahl-strassenbau.de',
  FROM_ADDRESS: 'noreply@wahl-strassenbau.de',
  MAIL_TRANSPORT: 'log', // log | smtp
  SMTP_HOST: '', SMTP_PORT: '587', SMTP_USER: '', SMTP_PASS: '',
  SMTP_SECURE: 'tls', // tls (STARTTLS) | ssl | none
  SMTP_TIMEOUT: '10',
  RETENTION_DAYS: '90',
  RATE_LIMIT: '5/600',
  MIN_FILL_SECONDS: '3',
  ALLOWED_ORIGINS: '',
  SITE_NAME: 'Wahl Straßenbau',
  PHONE: '0381 25 22 39 41',
};

export function config(env = {}) {
  const c = { ...DEFAULTS };
  for (const k of Object.keys(DEFAULTS)) {
    const v = env[k];
    if (v !== undefined && v !== null && String(v) !== '') c[k] = String(v);
  }
  return c;
}

const int = (s) => parseInt(s, 10) || 0;
const chars = (s) => [...s].length;

/* ---------- Normalisierung und Prüfung (Validator.php) ---------- */

/** Einzeiliges Feld: Steuerzeichen inkl. CR/LF entfernen (Header-Injection), Leerraum zusammenfassen. */
export function line(v) {
  const s = typeof v === 'string' ? v : '';
  return s.replace(/[\x00-\x1F\x7F]+/g, ' ').replace(/\s{2,}/g, ' ').trim();
}

/** Mehrzeiliges Feld: Zeilenumbrüche vereinheitlichen, übrige Steuerzeichen entfernen. */
export function text(v) {
  const s = typeof v === 'string' ? v : '';
  return s.replace(/\r\n|\r/g, '\n').replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '').trim();
}

/** Entspricht im Ergebnis FILTER_VALIDATE_EMAIL (ASCII-Adressen) plus der Endungsregel aus Validator.php. */
export function validEmail(s) {
  if (s.length > 254) return false;
  const at = s.lastIndexOf('@');
  if (at < 1) return false;
  const local = s.slice(0, at);
  const domain = s.slice(at + 1);
  if (local.length > 64 || !/^[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*$/.test(local)) return false;
  const labels = domain.split('.');
  if (labels.length < 2 || !labels.every((l) => /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$/.test(l))) return false;
  return /\.[^.@\s]{2,}$/.test(s);
}

/** @returns {[Record<string,string>, Record<string,string>]} [bereinigte Werte, Fehler je Feld] */
export function validate(form, post) {
  const data = {};
  const errors = {};
  for (const [key, [type, max]] of Object.entries(FIELDS)) {
    const value = type === 'line' ? line(post[key]) : text(post[key]);
    data[key] = value;
    if (chars(value) > max) errors[key] = M.toolong.replace('%d', String(max));
  }
  data.einwilligung = post.einwilligung === 'ja' ? 'ja' : '';

  for (const key of REQUIRED[form]) {
    if (data[key] === '' && !errors[key]) errors[key] = key === 'nachricht' ? M.nachricht : M.required;
  }
  if (data.email !== '' && !errors.email && !validEmail(data.email)) errors.email = M.email;
  if (data.telefon !== '' && !errors.telefon && !PHONE_RE.test(data.telefon)) errors.telefon = M.telefon;
  if (data.nachricht !== '' && !errors.nachricht && form !== 'widerruf' && chars(data.nachricht) < 5) errors.nachricht = M.nachricht;
  if (data.leistung !== '' && !SERVICES.includes(data.leistung)) errors.leistung = M.leistung;
  if (form !== 'widerruf' && data.einwilligung !== 'ja') errors.einwilligung = M.einwilligung;

  const keep = KEEP[form];
  const clean = Object.fromEntries(keep.map((k) => [k, data[k]]));
  const errs = Object.fromEntries(Object.entries(errors).filter(([k]) => keep.includes(k) || k === 'einwilligung'));
  return [clean, errs];
}

/* ---------- Speicher (SubmissionStore.php, RateLimiter.php) auf Cloudflare D1 ---------- */

const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    form TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    service TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL DEFAULT '',
    order_no TEXT NOT NULL DEFAULT '',
    items TEXT NOT NULL DEFAULT '',
    consent_at TEXT,
    mail_status TEXT NOT NULL DEFAULT 'pending'
  )`,
  'CREATE INDEX IF NOT EXISTS submissions_created ON submissions(created_at)',
  'CREATE TABLE IF NOT EXISTS rate_limit (key_hash TEXT PRIMARY KEY, window_start INTEGER NOT NULL, count INTEGER NOT NULL)',
  'CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)',
];

const ready = new WeakSet();
/** Schema beim ersten Zugriff je Isolate anlegen (dasselbe steht in schema.sql). */
async function ensureSchema(db) {
  if (ready.has(db)) return;
  await db.batch(SCHEMA.map((sql) => db.prepare(sql)));
  ready.add(db);
}

const isoNow = (now) => new Date(now).toISOString().replace(/\.\d{3}Z$/, 'Z');
const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');

/**
 * Begrenzung je Absender: Schlüssel = sha256(IP + Tagessalz). Das Salz liegt in D1 und wechselt täglich,
 * die rohe IP wird nie gespeichert; Einträge leben höchstens 24 h (purge). Ein einziges UPSERT zählt atomar.
 */
async function rateLimitHit(db, ip, cfg, now) {
  const [n, sec] = (cfg.RATE_LIMIT + '/600').split('/').map((x) => int(x));
  const limit = Math.max(1, n);
  const windowSec = Math.max(1, sec);
  const day = isoNow(now).slice(0, 10);
  const saltKey = 'salt_' + day;
  const fresh = hex(crypto.getRandomValues(new Uint8Array(32)));
  await db.prepare('INSERT OR IGNORE INTO meta (key, value) VALUES (?, ?)').bind(saltKey, fresh).run();
  const salt = (await db.prepare('SELECT value FROM meta WHERE key = ?').bind(saltKey).first())?.value ?? fresh;
  const key = hex(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(ip + '|' + salt)));
  const t = Math.floor(now / 1000);
  const row = await db.prepare(
    `INSERT INTO rate_limit (key_hash, window_start, count) VALUES (?, ?, 1)
     ON CONFLICT(key_hash) DO UPDATE SET
       count = CASE WHEN excluded.window_start - rate_limit.window_start >= ? THEN 1 ELSE rate_limit.count + 1 END,
       window_start = CASE WHEN excluded.window_start - rate_limit.window_start >= ? THEN excluded.window_start ELSE rate_limit.window_start END
     RETURNING count`,
  ).bind(key, t, windowSec, windowSec).first();
  return (row?.count ?? 1) <= limit;
}

async function insertSubmission(db, form, d, consentAt, now) {
  const res = await db.prepare(
    `INSERT INTO submissions (created_at, form, name, email, phone, service, message, order_no, items, consent_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  ).bind(isoNow(now), form, d.name ?? '', d.email ?? '', d.telefon ?? '', d.leistung ?? '', d.nachricht ?? '',
    d.bestellnummer ?? '', d.artikel ?? '', consentAt).run();
  return res.meta.last_row_id;
}

/** Löscht Anfragen älter als RETENTION_DAYS, Rate-Limit-Einträge älter als 24 h und alte Tagessalze. */
export async function purge(env, now = Date.now()) {
  const db = env.DB;
  await ensureSchema(db);
  const cfg = config(env);
  const days = Math.max(1, int(cfg.RETENTION_DAYS));
  const res = await db.prepare('DELETE FROM submissions WHERE created_at < ?').bind(isoNow(now - days * 86400_000)).run();
  await db.batch([
    db.prepare('DELETE FROM rate_limit WHERE window_start < ?').bind(Math.floor(now / 1000) - 86400),
    db.prepare("DELETE FROM meta WHERE key LIKE 'salt_%' AND key <> ?").bind('salt_' + isoNow(now).slice(0, 10)),
  ]);
  return res.meta.changes ?? 0;
}

/* ---------- HTML-Antworten ohne JavaScript (Page.php) ---------- */

export function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}
const unesc = (s) => s.replace(/&quot;/g, '"').replace(/&#0?39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const reEsc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const replaceAll = (s, find, repl) => s.split(find).join(repl);

function layout(title, body) {
  const tpl = TEMPLATES.layout || '';
  if (tpl === '') return `<!doctype html><html lang="de"><meta charset="utf-8"><title>${esc(title)}</title>${body}`;
  return replaceAll(replaceAll(tpl, '{{page_title}}', esc(title + ' – Wahl Straßenbau')), '{{page_body}}', body);
}

function hero(eyebrow, title, lead) {
  return '<section class="phero phero--plain phero--sm" aria-labelledby="page-title"><div class="wrap phero__inner">'
    + `<div class="phero__body"><p class="eyebrow">${esc(eyebrow)}</p>`
    + `<h1 id="page-title">${esc(title)}</h1><p class="lead">${lead}</p></div></div></section>`;
}

/** Setzt Werte, Fehlermeldungen, aria-invalid und die Fehlerübersicht im Formular-Markup aus build.py. */
export function fillForm(form, errors, values) {
  let html = TEMPLATES['form-' + form] || '';
  if (html === '') return '';
  const labels = {};
  for (const [, key] of html.matchAll(/data-field="([a-z]+)"/g)) {
    const m = html.match(new RegExp(`<label class="field__label" for="${form}-${key}">([^<]*)</label>`));
    labels[key] = m ? unesc(m[1]).trim().replace(/[ *]+$/, '') : 'Einwilligung';
    const value = values[key] ?? '';
    const bad = key in errors;
    const invalid = bad ? ' aria-invalid="true"' : '';

    // Steuerelement mit name="key"
    const ta = new RegExp(`(<textarea\\b[^>]*\\bname="${key}"[^>]*)>[\\s\\S]*?</textarea>`);
    const sel = new RegExp(`(<select\\b[^>]*\\bname="${key}"[^>]*)>([\\s\\S]*?)</select>`);
    const inp = new RegExp(`<input\\b[^>]*\\bname="${key}"[^>]*>`);
    if (ta.test(html)) {
      html = html.replace(ta, (_, open) => `${open}${invalid}>${esc(value)}</textarea>`);
    } else if (sel.test(html)) {
      html = html.replace(sel, (_, open, opts) => {
        const o = value !== '' ? opts.replace(`<option value="${esc(value)}">`, (t) => t.slice(0, -1) + ' selected>') : opts;
        return `${open}${invalid}>${o}</select>`;
      });
    } else {
      html = html.replace(inp, (tag) => {
        const checkbox = /\btype="checkbox"/.test(tag);
        return tag.slice(0, -1) + (checkbox ? '' : ` value="${esc(value)}"`) + invalid + '>';
      });
    }
    if (bad) {
      html = html.replace(new RegExp(`<div class="([^"]*)" data-field="${key}"`), (_, cls) => `<div class="${cls} is-error" data-field="${key}"`);
      html = html.replace(new RegExp(`(<p class="field__error[^"]*" id="${form}-${key}-err")(?: hidden)?>[\\s\\S]*?</p>`),
        (_, open) => `${open}>${esc(errors[key])}</p>`);
    }
  }
  const keys = Object.keys(errors);
  if (keys.length) {
    html = html.replace(/(<div class="errsum"[^>]*?) hidden>/, '$1>');
    const others = keys.filter((k) => k !== 'einwilligung');
    let t = '';
    if (others.length) {
      t += others.length === 1 ? '1 Pflichtfeld fehlt oder ist ungültig: ' : `${others.length} Pflichtfelder fehlen oder sind ungültig: `;
      t += others.map((k) => `<a href="#${form}-${k}">${esc(labels[k] ?? k)}</a>`).join(', ') + '.';
    }
    if ('einwilligung' in errors) {
      t += (others.length ? ' Außerdem ist die ' : 'Die ') + `<a href="#${form}-einwilligung">Einwilligung</a> erforderlich.`;
    }
    html = html.replace('<p class="errsum__text"></p>', () => `<p class="errsum__text">${t}</p>`);
  }
  return html;
}

export function formErrorPage(form, errors, general, values, cfg) {
  const lead = general !== ''
    ? esc(general)
    : esc(M.summary) + ` Ihre Angaben sind noch da. Oder rufen Sie uns an: <a class="inline" href="${PHONE_HREF}">${esc(cfg.PHONE)}</a>`;
  const body = hero('Kontakt', 'Bitte prüfen Sie Ihre Angaben', lead)
    + `<section class="sec"><div class="wrap"><div class="panel" style="max-width:760px">${fillForm(form, errors, values)}</div></div></section>`;
  return layout('Bitte prüfen Sie Ihre Angaben', body);
}

/** D-05: Bestätigung des Widerrufs; Markup aus server/templates/widerruf-done.html (build.py). */
export function widerrufDonePage(mailed = true) {
  let done = replaceAll(TEMPLATES['widerruf-done'] || '', ' role="status" hidden>', '>');
  if (!mailed) {
    done = done.replace('<p data-mailed>', '<p data-mailed hidden>').replace('<p data-nomail hidden>', '<p data-nomail>');
  }
  const body = `<section class="sec"><div class="wrap"><div class="panel" style="max-width:760px">${done}`
    + '<p style="margin-top:24px"><a class="btn btn--secondary" href="/">Zur Startseite</a></p></div></div></section>';
  return layout('Widerruf eingegangen', body);
}

/* ---------- E-Mail-Inhalte (FormHandler.php) ---------- */

function berlinStamp(now) {
  const p = Object.fromEntries(new Intl.DateTimeFormat('de-DE', {
    timeZone: 'Europe/Berlin', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(new Date(now)).map((x) => [x.type, x.value]));
  return `${p.day}.${p.month}.${p.year} ${p.hour}:${p.minute}`;
}

function ownerMessage(form, d, cfg, now) {
  const name = d.name;
  let subject;
  let body;
  if (form === 'widerruf') {
    subject = 'Widerruf über die Webseite: ' + name;
    body = 'Widerruf über die Webseite\n\n'
      + `Name: ${name}\n`
      + `Bestell- oder Buchungsnummer: ${d.bestellnummer}\n`
      + `E-Mail: ${d.email}\n`
      + `Betroffene Artikel: ${d.artikel !== '' ? d.artikel : '(gesamter Vertrag)'}\n\n`
      + `Grund:\n${d.nachricht !== '' ? d.nachricht : '(nicht angegeben)'}\n`;
  } else {
    subject = (form === 'kurz' ? 'Rückrufwunsch über die Webseite: ' : 'Anfrage über die Webseite: ') + name;
    body = `Anfrage über die Webseite (${form})\n\n`
      + `Name: ${name}\n`
      + `E-Mail: ${(d.email ?? '') !== '' ? d.email : '(nicht angegeben)'}\n`
      + `Telefon: ${(d.telefon ?? '') !== '' ? d.telefon : '(nicht angegeben)'}\n`
      + `Leistung: ${(d.leistung ?? '') !== '' ? d.leistung : '(nicht angegeben)'}\n\n`
      + `Nachricht:\n${d.nachricht}\n\n`
      + 'Einwilligung zur Datenverarbeitung: erteilt\n';
  }
  body += `\n--\nGesendet über wahl-strassenbau.de am ${berlinStamp(now)} Uhr\n`;
  return new Message(cfg.RECIPIENT, subject, body, d.email ?? '');
}

/** Eingangsbestätigung Widerruf (Text aus dem bisherigen kontakt.php). */
function confirmation(d, cfg) {
  const body = `Guten Tag ${d.name},\n\nIhr Widerruf zur Bestell- oder Buchungsnummer ${d.bestellnummer} ist bei uns eingegangen.\n\n`
    + `Wahl Straßenbau GmbH & Co. KG\nTelefon: ${cfg.PHONE}\n`;
  return new Message(d.email, 'Eingangsbestätigung: Ihr Widerruf', body);
}

/* ---------- Ablauf ---------- */

const SECURITY = {
  'X-Content-Type-Options': 'nosniff',
  'Cache-Control': 'no-store',
  'Referrer-Policy': 'same-origin',
  'X-Frame-Options': 'SAMEORIGIN',
  'Strict-Transport-Security': 'max-age=31536000',
};

function originAllowed(request, cfg) {
  const host = new URL(request.url).host.toLowerCase();
  const allowed = cfg.ALLOWED_ORIGINS.split(',').map((o) => o.trim().replace(/\/+$/, '').toLowerCase()).filter(Boolean);
  const origin = request.headers.get('origin') || '';
  // «Origin: null» (Datenschutzmodi, Weiterleitungen) wie fehlender Origin behandeln → Referer prüfen
  const check = origin !== '' && origin !== 'null' ? origin : request.headers.get('referer') || '';
  if (check === '') return true; // weder Origin noch Referer (strikte Datenschutz-Einstellungen): nicht blockieren
  let u;
  try {
    u = new URL(check);
  } catch {
    return false;
  }
  if (!u.host) return false;
  return u.host.toLowerCase() === host || allowed.includes(`${u.protocol}//${u.host}`.toLowerCase());
}

/** Formulardaten lesen; null = Anfrage zu groß (Größe des tatsächlichen Inhalts, nicht nur Content-Length). */
async function readPost(request) {
  if (int(request.headers.get('content-length') || '0') > MAX_BODY) return null;
  try {
    const buf = await request.arrayBuffer();
    if (buf.byteLength > MAX_BODY) return null;
    const type = request.headers.get('content-type') || '';
    const fd = await new Response(buf, { headers: { 'content-type': type } }).formData();
    const out = {};
    for (const [k, v] of fd.entries()) if (typeof v === 'string' && !(k in out)) out[k] = v;
    return out;
  } catch {
    return {};
  }
}

/**
 * @param {Request} request
 * @param {{DB?: D1Database} & Record<string,string>} env
 * @param {{connect?: Function, now?: () => number, onMail?: (m: Message) => void, log?: (s: string) => void}} deps
 */
export async function handleForm(request, env, deps = {}) {
  const cfg = config(env);
  const now = deps.now ? deps.now() : Date.now();
  const log = deps.log || ((s) => console.log(s));
  const accept = request.headers.get('accept') || '';
  const json = accept.toLowerCase().includes('application/json') || request.headers.get('x-requested-with') === 'fetch';
  let form = 'kontakt';
  let post = {};

  const respond = (status, body, type, extra = {}) =>
    new Response(body, { status, headers: { ...SECURITY, 'Content-Type': type, ...extra } });

  const success = (silent, confirmed = null) => {
    const redirect = form === 'widerruf' ? null : '/kontakt/danke/';
    if (json) {
      return respond(200, JSON.stringify({ ok: true, errors: {}, error: '', redirect, confirmation: confirmed }), 'application/json; charset=utf-8');
    }
    if (redirect !== null) return new Response(null, { status: 303, headers: { ...SECURITY, Location: redirect } });
    return respond(200, widerrufDonePage(confirmed !== false), 'text/html; charset=utf-8');
  };

  const fail = (status, errors, general, values = null, extra = {}) => {
    if (json) {
      return respond(status, JSON.stringify({ ok: false, errors, error: general }), 'application/json; charset=utf-8', extra);
    }
    const raw = {};
    for (const k of ['name', 'email', 'telefon', 'leistung', 'nachricht', 'bestellnummer', 'artikel']) raw[k] = text(post[k]);
    const vals = values && Object.keys(values).length ? values : raw;
    return respond(status, formErrorPage(form, errors, general, vals, cfg), 'text/html; charset=utf-8', extra);
  };

  if (request.method !== 'POST') return fail(405, {}, M.method, null, { Allow: 'POST' });

  const parsed = await readPost(request);
  if (parsed === null) return fail(413, {}, M.network);
  post = parsed;
  const f = line(post.form);
  form = FORMS.includes(f) ? f : 'kontakt';

  if (!originAllowed(request, cfg)) return fail(403, {}, M.origin);
  // Honeypot: für Menschen unsichtbar; gefüllt = Bot → stiller Erfolg, nichts wird gespeichert oder gesendet
  if (line(post.website) !== '') return success(true);
  // Mindestausfüllzeit: «t» = Sekunden seit dem Laden der Seite (main.js). Ohne JavaScript fehlt das Feld → keine Prüfung.
  const t = post.t ?? '';
  if (/^\d{1,8}$/.test(t) && int(t) < int(cfg.MIN_FILL_SECONDS)) return success(true);

  // Speicher: fällt D1 aus, wird die Anfrage trotzdem per E-Mail zugestellt (ADR-0001: nichts verlieren)
  let db = env.DB || null;
  if (db) {
    try {
      await ensureSchema(db);
      const ip = request.headers.get('cf-connecting-ip') || '';
      if (!(await rateLimitHit(db, ip, cfg, now))) {
        const retry = Math.max(1, int((cfg.RATE_LIMIT + '/600').split('/')[1]));
        return fail(429, {}, M.rate, null, { 'Retry-After': String(retry) });
      }
    } catch (e) {
      log('kontakt: Speicher nicht verfügbar: ' + (e && e.message));
      db = null;
    }
  } else {
    log('kontakt: keine D1-Bindung «DB» konfiguriert');
  }

  const [data, errors] = validate(form, post);
  if (Object.keys(errors).length) return fail(422, errors, '', data);

  const consentAt = form === 'widerruf' ? null : isoNow(now);
  let id = null;
  if (db) {
    try {
      id = await insertSubmission(db, form, data, consentAt, now);
      await purge(env, now);
    } catch (e) {
      log('kontakt: Speichern fehlgeschlagen: ' + (e && e.message));
    }
  }

  const host = new URL(request.url).hostname;
  const m = mailer(cfg, { ...deps, log, host });
  const sent = await m.send(ownerMessage(form, data, cfg, now));
  let status = sent ? 'sent' : 'failed';
  let confirmed = null;
  if (sent && form === 'widerruf') {
    confirmed = await m.send(confirmation(data, cfg));
    status = confirmed ? 'sent' : 'sent_owner_only';
  }
  if (id !== null) {
    try {
      await db.prepare('UPDATE submissions SET mail_status = ? WHERE id = ?').bind(status, id).run();
    } catch (e) {
      log('kontakt: mail_status nicht gespeichert: ' + (e && e.message));
    }
  }
  log(`kontakt: Anfrage #${id ?? '-'} (${form}) mail_status=${status}`);

  if (!sent && id === null) return fail(500, {}, M.network, data); // weder gespeichert noch gesendet
  if (!sent) return fail(502, {}, M.network, data);
  return success(false, confirmed);
}
