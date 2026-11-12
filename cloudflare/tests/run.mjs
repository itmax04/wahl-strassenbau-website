/**
 * Tests für den Formular-Worker ohne Cloudflare-Konto (Node ≥ 22.5):  node cloudflare/tests/run.mjs
 * - D1 wird durch eine kleine Hülle um node:sqlite ersetzt (gleiche API-Teilmenge: prepare/bind/run/first/all/batch),
 * - SMTP läuft gegen tests/php/fake_smtp.php (ohne TLS) über einen node:net-Socket mit readable/writable wie cloudflare:sockets,
 * - die Fehlerseite ohne JavaScript wird mit der PHP-Ausgabe (Page::formError) verglichen.
 * Das echte Laufzeitsystem (workerd, Static Assets, _headers) prüft das nicht: dafür «npx wrangler dev» (siehe README.md).
 */
import { DatabaseSync } from 'node:sqlite';
import { spawn, execFileSync } from 'node:child_process';
import net from 'node:net';
import { Duplex } from 'node:stream';
import { readFileSync, existsSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { handleForm, purge, validate, formErrorPage, config } from '../worker/app.js';
import { quotedPrintable, encodeHeader } from '../worker/mail.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const ORIGIN = 'https://www.wahl-strassenbau.de';

/* ---------- D1-Ersatz ---------- */
function d1(failing = false) {
  const db = new DatabaseSync(':memory:');
  db.exec(readFileSync(join(ROOT, 'cloudflare/schema.sql'), 'utf8')); // schema.sql muss gültig sein
  const stmt = (sql, args = []) => ({
    bind: (...a) => stmt(sql, a),
    async run() {
      if (failing) throw new Error('D1 nicht erreichbar');
      const r = db.prepare(sql).run(...args);
      return { success: true, meta: { last_row_id: Number(r.lastInsertRowid), changes: Number(r.changes) } };
    },
    async first(col) {
      if (failing) throw new Error('D1 nicht erreichbar');
      const row = db.prepare(sql).get(...args) ?? null;
      return col && row ? row[col] : row;
    },
    async all() {
      if (failing) throw new Error('D1 nicht erreichbar');
      return { results: db.prepare(sql).all(...args) };
    },
  });
  return {
    raw: db,
    prepare: (sql) => stmt(sql),
    async batch(list) {
      const out = [];
      for (const s of list) out.push(await s.run());
      return out;
    },
  };
}

/* ---------- Hilfen ---------- */
let passed = 0;
let failed = 0;
function check(name, cond, info = '') {
  if (cond) {
    passed++;
    console.log('PASS ' + name);
  } else {
    failed++;
    console.log('FAIL ' + name + (info ? ' — ' + info : ''));
  }
}

const valid = {
  kontakt: { form: 'kontakt', name: 'Erika Mustermann', email: 'erika@example.org', telefon: '0381 123456', leistung: 'Garten & Landschaft', nachricht: 'Bitte um ein Angebot für 40 m² Pflaster.', einwilligung: 'ja', t: '12', website: '' },
  kurz: { form: 'kurz', name: 'Max Muster', telefon: '+49 381 1234', nachricht: 'Rückruf bitte, Hofeinfahrt.', einwilligung: 'ja', t: '9', website: '' },
  widerruf: { form: 'widerruf', name: 'Max Muster', bestellnummer: 'A-123', email: 'max@example.org', artikel: '', nachricht: '', t: '20', website: '' },
};

function req(fields, { js = true, origin = ORIGIN, method = 'POST', ip = '203.0.113.7', headers = {} } = {}) {
  const h = new Headers({ 'cf-connecting-ip': ip, ...headers });
  if (origin) h.set('origin', origin);
  if (js) {
    h.set('accept', 'application/json');
    h.set('x-requested-with', 'fetch');
  }
  const init = { method, headers: h };
  if (method === 'POST') init.body = new URLSearchParams(fields);
  return new Request(ORIGIN + '/kontakt.php', init);
}

function env(extra = {}) {
  return { DB: d1(), ...extra };
}

async function run(fields, opts = {}, e = env(), deps = {}) {
  const mails = [];
  const logs = [];
  const res = await handleForm(req(fields, opts), e, { onMail: (m) => mails.push(m), log: (s) => logs.push(s), ...deps });
  const body = await res.text();
  let json = null;
  try {
    json = JSON.parse(body);
  } catch {}
  return { res, body, json, mails, logs, e };
}

const rows = (e) => e.DB.raw.prepare('SELECT * FROM submissions ORDER BY id').all();

/* ---------- Tests ---------- */

{
  const r = await run({}, { method: 'GET' });
  check('GET → 405 mit Allow: POST', r.res.status === 405 && r.res.headers.get('allow') === 'POST' && r.json?.error === 'Method Not Allowed');
}
{
  const r = await run(valid.kontakt, { origin: 'https://evil.example' });
  check('Fremder Origin → 403, nichts gespeichert', r.res.status === 403 && rows(r.e).length === 0);
}
{
  const r = await run(valid.kontakt, { origin: 'null', headers: { referer: ORIGIN + '/kontakt/' } });
  check('Origin «null» → Referer der eigenen Domain erlaubt', r.res.status === 200 && r.json?.ok === true);
}
{
  const r = await run(valid.kontakt, { origin: 'https://wahl-strassenbau.example.workers.dev' }, env({ ALLOWED_ORIGINS: 'https://wahl-strassenbau.example.workers.dev/' }));
  check('ALLOWED_ORIGINS erlaubt zusätzliche Herkunft', r.res.status === 200);
}
{
  const r = await run({ ...valid.kontakt, website: 'http://spam' });
  check('Honeypot → stiller Erfolg, nichts gespeichert/gesendet', r.json?.ok === true && rows(r.e).length === 0 && r.mails.length === 0);
}
{
  const r = await run({ ...valid.kontakt, t: '1' });
  check('Zu schnell (t < 3 s) → stiller Erfolg, nichts gespeichert', r.json?.ok === true && rows(r.e).length === 0 && r.mails.length === 0);
}
{
  const r = await run(valid.kontakt);
  const [row] = rows(r.e);
  const m = r.mails[0];
  check('Kontakt (JS) → 200, redirect /kontakt/danke/', r.res.status === 200 && r.json.ok && r.json.redirect === '/kontakt/danke/' && r.json.confirmation === null);
  check('Kontakt gespeichert mit consent_at und mail_status=sent', row && row.form === 'kontakt' && row.service === 'Garten & Landschaft' && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(row.consent_at) && row.mail_status === 'sent');
  check('Mail an Inhaber: Betreff, Reply-To, Inhalt', m && m.to === 'info@wahl-strassenbau.de' && m.subject === 'Anfrage über die Webseite: Erika Mustermann'
    && m.replyTo === 'erika@example.org' && m.body.includes('Leistung: Garten & Landschaft') && m.body.includes('Einwilligung zur Datenverarbeitung: erteilt')
    && /Gesendet über wahl-strassenbau\.de am \d\d\.\d\d\.\d{4} \d\d:\d\d Uhr/.test(m.body));
  check('Sicherheits-Header an Worker-Antworten', r.res.headers.get('cache-control') === 'no-store' && r.res.headers.get('x-content-type-options') === 'nosniff');
  check('Log ohne personenbezogene Daten', !r.logs.join('\n').includes('Erika') && !r.logs.join('\n').includes('example.org'));
}
{
  const r = await run(valid.kurz);
  const [row] = rows(r.e);
  check('Kurzanfrage → ok, Betreff Rückrufwunsch, nur Felder der Kurzanfrage', r.json?.ok && r.mails[0].subject.startsWith('Rückrufwunsch über die Webseite: ') && row.email === '' && row.service === '');
}
{
  const r = await run(valid.widerruf);
  const [row] = rows(r.e);
  check('Widerruf (JS) → ok, redirect null, confirmation true, 2 Mails', r.json?.ok && r.json.redirect === null && r.json.confirmation === true && r.mails.length === 2 && r.mails[1].to === 'max@example.org');
  check('Widerruf ohne consent_at, Artikel-Hinweis in der Mail', row.consent_at === null && r.mails[0].body.includes('Betroffene Artikel: (gesamter Vertrag)'));
}
{
  const r = await run({ form: 'kontakt', name: '', email: 'falsch', telefon: 'abc', leistung: 'Hack', nachricht: 'kurz', t: '10' });
  const e = r.json?.errors || {};
  check('422 mit Fehlern je Feld (Texte aus messages.json)', r.res.status === 422 && e.name === 'Bitte füllen Sie dieses Pflichtfeld aus.'
    && e.email === 'Bitte geben Sie eine gültige E-Mail-Adresse ein.' && e.telefon && e.leistung && e.nachricht && e.einwilligung && rows(r.e).length === 0);
}
{
  const [d, errs] = validate('kontakt', { name: 'A\r\nBcc: x@y.de', email: 'a@b.de', nachricht: 'x'.repeat(5001), einwilligung: 'ja' });
  check('CR/LF im Namen entfernt (Header-Injection), Länge > 5000 → Fehler', d.name === 'A Bcc: x@y.de' && errs.nachricht === 'Bitte kürzen Sie Ihre Eingabe auf höchstens 5000 Zeichen.');
  const emails = ['a@b.de', 'max.muster+x@sub.example.org', 'ä@b.de', 'a@b', 'a@b.c', 'a..b@c.de', '.a@b.de', 'a@-b.de', 'a b@c.de'];
  const ok = emails.map((x) => !validate('widerruf', { name: 'n', bestellnummer: '1', email: x }).at(1).email);
  check('E-Mail-Regeln wie FILTER_VALIDATE_EMAIL + Endung', JSON.stringify(ok) === JSON.stringify([true, true, false, false, false, false, false, false, false]), JSON.stringify(ok));
}
{
  const r = await run(valid.kontakt, { js: false });
  check('Ohne JS: Erfolg → 303 /kontakt/danke/', r.res.status === 303 && r.res.headers.get('location') === '/kontakt/danke/');
}
{
  const r = await run({ form: 'kontakt', name: '<script>alert(1)</script>', email: 'x', leistung: 'Pflasterarbeiten', nachricht: 'Hallo "Welt" & Co', t: '10' }, { js: false });
  const b = r.body;
  check('Ohne JS: 422-Seite im Layout, Eingaben escaped', r.res.status === 422 && b.includes('<title>Bitte prüfen Sie Ihre Angaben – Wahl Straßenbau</title>')
    && b.includes('value="&lt;script&gt;alert(1)&lt;/script&gt;"') && !b.includes('<script>alert') && b.includes('>Hallo &quot;Welt&quot; &amp; Co</textarea>'));
  check('Ohne JS: Fehlerübersicht, aria-invalid, is-error, Auswahl erhalten', /<div class="errsum"[^>]*role="alert"[^>]*>/.test(b) && !/<div class="errsum"[^>]*hidden>/.test(b)
    && b.includes('<a href="#kontakt-email">E-Mail</a>') && b.includes('Außerdem ist die <a href="#kontakt-einwilligung">Einwilligung</a> erforderlich.')
    && (b.match(/aria-invalid="true"/g) || []).length === 2 && b.includes('<option value="Pflasterarbeiten" selected>') && b.includes('class="field is-error" data-field="email"'));
}
{
  const r = await run(valid.widerruf, { js: false });
  check('Ohne JS: Widerruf → Bestätigungsseite (D-05)', r.res.status === 200 && r.body.includes('Widerruf eingegangen') && r.body.includes('<p data-nomail hidden>') && !r.body.includes('role="status" hidden'));
}
{
  const e = env();
  const codes = [];
  for (let i = 0; i < 6; i++) codes.push((await run(valid.kurz, {}, e)).res.status);
  const other = await run(valid.kurz, { ip: '198.51.100.1' }, e);
  const r429 = await run(valid.kurz, {}, e);
  const keys = e.DB.raw.prepare('SELECT key_hash FROM rate_limit').all().map((x) => x.key_hash);
  check('Rate-Limit 5/600: 6. Anfrage → 429 mit Retry-After, andere IP frei', codes.join() === '200,200,200,200,200,429' && other.res.status === 200
    && r429.res.headers.get('retry-after') === '600' && r429.json.error.startsWith('Zu viele Anfragen'));
  check('Rate-Limit speichert keine IP (nur sha256)', keys.every((k) => /^[0-9a-f]{64}$/.test(k)) && !JSON.stringify(e.DB.raw.prepare('SELECT * FROM meta').all()).includes('203.0.113'));
  const later = await run(valid.kurz, {}, e, { now: () => Date.now() + 601_000 });
  check('Rate-Limit: nach Ablauf des Fensters wieder erlaubt', later.res.status === 200);
}
{
  const e = env();
  const old = Date.now() - 91 * 86400_000;
  await run(valid.kontakt, {}, e, { now: () => old });
  await run(valid.kurz, {}, e);
  const n = rows(e).length;
  const deleted = await purge(e);
  check('Aufbewahrung 90 Tage: alte Anfrage bei neuer Anfrage gelöscht, purge() idempotent', n === 1 && rows(e)[0].form === 'kurz' && deleted === 0);
}
{
  const r = await run(valid.kontakt, {}, { DB: d1(true) });
  check('D1 ausgefallen → Mail wird trotzdem gesendet, 200', r.res.status === 200 && r.mails.length === 1 && r.logs.some((l) => l.includes('Speicher nicht verfügbar')));
}
{
  const r = await run(valid.kontakt, {}, {});
  check('Ohne D1-Bindung → Mail wird gesendet, Hinweis im Log', r.res.status === 200 && r.logs.some((l) => l.includes('keine D1-Bindung')));
}
{
  const big = { ...valid.kontakt, nachricht: 'x'.repeat(120_000) };
  const r = await run(big);
  check('Übergroße Anfrage (> 100 kB) → 413', r.res.status === 413);
}

/* ---------- Kodierung ---------- */
{
  const qp = quotedPrintable('Grüße = 100 %\n' + 'a'.repeat(100) + ' \n.Punkt');
  const lines = qp.split('\r\n');
  check('Quoted-printable: UTF-8, =3D, Zeilen ≤ 76, Leerzeichen am Zeilenende kodiert', qp.startsWith('Gr=C3=BC=C3=9Fe =3D 100 %') && lines.every((l) => l.length <= 76) && qp.includes('=20\r\n'));
  const h = encodeHeader('Anfrage über die Webseite: ' + 'Ä'.repeat(40));
  check('Betreff RFC 2047, gefaltet, Wörter ≤ 75 Zeichen', h.split('\r\n ').every((w) => /^=\?UTF-8\?B\?[A-Za-z0-9+/=]+\?=$/.test(w) && w.length <= 75) && encodeHeader('ASCII') === 'ASCII');
}

/* ---------- SMTP gegen tests/php/fake_smtp.php ---------- */
function nodeConnect({ hostname, port }, opts) {
  const s = net.connect({ host: hostname, port });
  const { readable, writable } = Duplex.toWeb(s);
  return {
    readable, writable, opts,
    startTls() { throw new Error('TLS im Test nicht verfügbar'); },
    async close() { s.destroy(); },
  };
}

const port = 20000 + Math.floor(Math.random() * 20000);
const dir = mkdtempSync(join(tmpdir(), 'wahl-cf-'));
const slog = join(dir, 'smtp.log');
const fake = spawn('php', [join(ROOT, 'tests/php/fake_smtp.php'), String(port), slog], { stdio: 'ignore' });
await new Promise((r) => setTimeout(r, 400));
try {
  const smtpEnv = env({ MAIL_TRANSPORT: 'smtp', SMTP_HOST: '127.0.0.1', SMTP_PORT: String(port), SMTP_SECURE: 'none', SMTP_USER: 'user@wahl-strassenbau.de', SMTP_PASS: 'geheim' });
  const r = await run({ ...valid.widerruf, name: 'Jörg .Punkt' }, {}, smtpEnv, { connect: nodeConnect });
  const log = existsSync(slog) ? readFileSync(slog, 'utf8') : '';
  check('SMTP: EHLO, AUTH LOGIN, MAIL FROM, RCPT TO, DATA, QUIT', r.res.status === 200 && r.json.confirmation === true
    && /C: EHLO www\.wahl-strassenbau\.de/.test(log) && log.includes('C: AUTH LOGIN') && log.includes('C: MAIL FROM:<noreply@wahl-strassenbau.de>')
    && log.includes('C: RCPT TO:<info@wahl-strassenbau.de>') && log.includes('C: RCPT TO:<max@example.org>') && log.includes('C: QUIT'), log.slice(0, 400));
  check('SMTP: Betreff kodiert, quoted-printable, kein Passwort im Klartext', log.includes('Subject: =?UTF-8?B?') && log.includes('Content-Transfer-Encoding: quoted-printable')
    && log.includes('Name: J=C3=B6rg .Punkt') && !log.includes('geheim') && log.includes('Reply-To: max@example.org'));
  check('SMTP: mail_status=sent', rows(smtpEnv)[0].mail_status === 'sent');

  const downEnv = env({ MAIL_TRANSPORT: 'smtp', SMTP_HOST: '127.0.0.1', SMTP_PORT: '1', SMTP_SECURE: 'none', SMTP_TIMEOUT: '2' });
  const down = await run(valid.kontakt, {}, downEnv, { connect: nodeConnect });
  check('SMTP nicht erreichbar → 502 mit Telefonnummer, Anfrage gespeichert (failed)', down.res.status === 502
    && down.json.error.includes('0381 25 22 39 41') && rows(downEnv)[0].mail_status === 'failed');
} finally {
  fake.kill();
}

/* ---------- Gleichheit mit PHP (Page::formError) ---------- */
{
  const errors = { name: 'Bitte füllen Sie dieses Pflichtfeld aus.', email: 'Bitte geben Sie eine gültige E-Mail-Adresse ein.', einwilligung: 'Bitte bestätigen Sie die Einwilligung zur Datenverarbeitung.' };
  const values = { name: '', email: 'a"<b>', telefon: '0381', leistung: 'Garten & Landschaft', nachricht: 'Zeile 1\nZeile 2 & <x>' };
  const php = `require 'server/bootstrap.php'; echo Wahl\\Page::formError('kontakt', json_decode($argv[1], true), '', json_decode($argv[2], true));`;
  const p = execFileSync('php', ['-r', php, JSON.stringify(errors), JSON.stringify(values)], { cwd: ROOT, encoding: 'utf8' });
  const j = formErrorPage('kontakt', errors, '', values, config({}));
  const textOf = (h) => h.replace(/<script[\s\S]*?<\/script>/g, '').replace(/<[^>]+>/g, ' ').replace(/&#0?39;/g, "'").replace(/&quot;/g, '"').replace(/\s+/g, ' ').trim();
  const marks = (h) => [
    (h.match(/aria-invalid="true"/g) || []).length,
    (h.match(/is-error/g) || []).length,
    (h.match(/<option[^>]*selected/g) || []).length,
    /<div class="errsum"[^>]*hidden/.test(h),
    // libxml schreibt Werte mit «"» in einfache Anführungszeichen → beide Formen auf den Klartext zurückführen
    [...h.matchAll(/value=(?:"([^"]*)"|'([^']*)')/g)].map((m) => (m[1] ?? m[2]).replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&#0?39;/g, "'")).join('|'),
  ];
  check('Fehlerseite ohne JS: gleicher Text wie PHP', textOf(p) === textOf(j), textOf(p).slice(0, 120) + ' ≠ ' + textOf(j).slice(0, 120));
  check('Fehlerseite ohne JS: gleiche Markierungen wie PHP (aria-invalid, is-error, selected, Werte)', JSON.stringify(marks(p)) === JSON.stringify(marks(j)), JSON.stringify(marks(p)) + ' ≠ ' + JSON.stringify(marks(j)));
}

console.log(`\n${passed}/${passed + failed} Prüfungen bestanden`);
process.exit(failed ? 1 : 0);
