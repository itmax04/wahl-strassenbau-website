/**
 * E-Mail für den Worker (Portierung von Message.php, LogMailer.php, SmtpMailer.php).
 * Transporte: «log» (Standard, nichts wird gesendet) und «smtp» (Postfach des Hosters über TCP-Sockets von Cloudflare:
 * STARTTLS auf 587 oder TLS auf 465; Port 25 ist bei Cloudflare gesperrt). Zugangsdaten nur als Secret (wrangler secret put).
 */

const enc = new TextEncoder();

/** Einzeilig wie Validator::line (Header-Injection). */
const oneLine = (v) => String(v ?? '').replace(/[\x00-\x1F\x7F]+/g, ' ').replace(/\s{2,}/g, ' ').trim();
const looksLikeEmail = (s) => /^[^\s@<>()[\]\\,;:"]+@[^\s@<>()[\]\\,;:"]+\.[^\s@<>()[\]\\,;:"]{2,}$/.test(s);

function b64(bytes) {
  let bin = '';
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

/** RFC 2047 «B»-Kodierung wie mb_encode_mimeheader: ASCII bleibt, sonst Encoded-Words (≤ 45 Byte je Wort), gefaltet mit CRLF+Leerzeichen. */
export function encodeHeader(s) {
  if (/^[\x20-\x7E]*$/.test(s)) return s;
  const words = [];
  let chunk = [];
  for (const ch of s) {
    const b = enc.encode(ch);
    if (chunk.length + b.length > 45) {
      words.push(chunk);
      chunk = [];
    }
    chunk.push(...b);
  }
  if (chunk.length) words.push(chunk);
  return words.map((w) => `=?UTF-8?B?${b64(w)}?=`).join('\r\n ');
}

/** Quoted-printable (RFC 2045): Zeilen ≤ 76 Zeichen mit weichen Umbrüchen, harte Umbrüche als CRLF. */
export function quotedPrintable(text) {
  const out = [];
  for (const lineText of text.replace(/\r\n|\r/g, '\n').split('\n')) {
    const bytes = enc.encode(lineText);
    let cur = '';
    bytes.forEach((b, i) => {
      const last = i === bytes.length - 1;
      let tok;
      if ((b === 0x20 || b === 0x09) && !last) tok = String.fromCharCode(b);
      else if (b >= 33 && b <= 126 && b !== 61) tok = String.fromCharCode(b);
      else tok = '=' + b.toString(16).toUpperCase().padStart(2, '0');
      if (cur.length + tok.length > 75) {
        out.push(cur + '=');
        cur = '';
      }
      cur += tok;
    });
    out.push(cur);
  }
  return out.join('\r\n');
}

/** Eine Text-E-Mail. Alle Kopfzeilenwerte sind einzeilig, der Betreff wird MIME-kodiert. */
export class Message {
  constructor(to, subject, body, replyTo = '') {
    this.to = to;
    this.subject = subject;
    this.body = body;
    this.replyTo = replyTo;
  }

  headers(cfg) {
    const h = [
      `From: ${encodeHeader(cfg.SITE_NAME)} <${oneLine(cfg.FROM_ADDRESS)}>`,
      'MIME-Version: 1.0',
      'Content-Type: text/plain; charset=UTF-8',
      'Content-Transfer-Encoding: quoted-printable',
    ];
    const reply = oneLine(this.replyTo);
    if (reply !== '' && looksLikeEmail(reply)) h.push(`Reply-To: ${reply}`);
    return h;
  }

  /** Vollständige Nachricht für SMTP DATA, inkl. Dot-Stuffing. */
  raw(cfg, now = Date.now()) {
    const to = oneLine(this.to);
    const from = oneLine(cfg.FROM_ADDRESS);
    const domain = from.split('@')[1] || 'localhost';
    const id = [...crypto.getRandomValues(new Uint8Array(12))].map((b) => b.toString(16).padStart(2, '0')).join('');
    const head = [
      `Date: ${new Date(now).toUTCString().replace('GMT', '+0000')}`,
      `To: <${to}>`,
      `Subject: ${encodeHeader(oneLine(this.subject))}`,
      ...this.headers(cfg),
      `Message-ID: <${id}@${domain}>`,
    ];
    const body = quotedPrintable(this.body).split('\r\n').map((l) => (l.startsWith('.') ? '.' + l : l)).join('\r\n');
    return head.join('\r\n') + '\r\n\r\n' + body;
  }
}

/** «log»: nichts senden. Ins Worker-Log nur ein Hinweis ohne personenbezogene Daten (Inhalt steht in D1). */
class LogMailer {
  constructor(cfg, deps) {
    this.cfg = cfg;
    this.deps = deps;
  }

  async send(message) {
    this.deps.onMail?.(message, this.cfg);
    const who = oneLine(message.to) === oneLine(this.cfg.RECIPIENT) ? 'Inhaber' : 'Absender';
    this.deps.log(`mail: MAIL_TRANSPORT=log, Nachricht an ${who} nicht gesendet`);
    return true;
  }
}

/** Minimaler SMTP-Client: EHLO, STARTTLS (tls) oder TLS (ssl), AUTH LOGIN, MAIL FROM, RCPT TO, DATA, QUIT. */
class SmtpMailer {
  constructor(cfg, deps) {
    this.cfg = cfg;
    this.deps = deps;
  }

  async send(message) {
    const timeout = Math.max(1, parseInt(this.cfg.SMTP_TIMEOUT, 10) || 10) * 1000;
    let session = null;
    let timer;
    try {
      await Promise.race([
        (async () => {
          session = await this.open();
          await this.deliver(session, message);
        })(),
        new Promise((_, reject) => {
          timer = setTimeout(() => reject(new Error('Zeitüberschreitung')), timeout);
        }),
      ]);
      return true;
    } catch (e) {
      // Nur Status ins Log, keine personenbezogenen Daten, keine Zugangsdaten
      this.deps.log('SmtpMailer: ' + String(e && e.message).replace(/\s+/g, ' '));
      return false;
    } finally {
      clearTimeout(timer);
      if (session) await session.quit();
    }
  }

  async open() {
    const { SMTP_HOST: host, SMTP_SECURE: secure } = this.cfg;
    const to = oneLine(this.cfg.RECIPIENT);
    if (!host || !this.deps.connect || !looksLikeEmail(to) || !looksLikeEmail(oneLine(this.cfg.FROM_ADDRESS))) {
      throw new Error('Konfiguration oder Adresse ungültig');
    }
    const secureTransport = secure === 'ssl' ? 'on' : secure === 'tls' ? 'starttls' : 'off';
    const socket = this.deps.connect({ hostname: host, port: parseInt(this.cfg.SMTP_PORT, 10) || 587 }, { secureTransport, allowHalfOpen: false });
    return new SmtpSession(socket);
  }

  async deliver(s, message) {
    const to = oneLine(message.to);
    const from = oneLine(this.cfg.FROM_ADDRESS);
    if (!looksLikeEmail(to)) throw new Error('Empfängeradresse ungültig');
    const helo = String(this.deps.host || 'localhost').replace(/[^A-Za-z0-9.\-]/g, '') || 'localhost';
    await s.expect(220);
    await s.command(`EHLO ${helo}`, 250);
    if (this.cfg.SMTP_SECURE === 'tls') {
      await s.command('STARTTLS', 220);
      s.upgrade();
      await s.command(`EHLO ${helo}`, 250);
    }
    if (this.cfg.SMTP_USER !== '') {
      await s.command('AUTH LOGIN', 334);
      await s.command(b64(enc.encode(this.cfg.SMTP_USER)), 334, true);
      await s.command(b64(enc.encode(this.cfg.SMTP_PASS)), 235, true);
    }
    await s.command(`MAIL FROM:<${from}>`, 250);
    await s.command(`RCPT TO:<${to}>`, [250, 251]);
    await s.command('DATA', 354);
    await s.write(message.raw(this.cfg) + '\r\n.\r\n');
    await s.expect(250);
  }
}

/** Zeilenweises Lesen/Schreiben auf einem Socket mit readable/writable (cloudflare:sockets). */
class SmtpSession {
  constructor(socket) {
    this.socket = socket;
    this.attach();
  }

  attach() {
    this.reader = this.socket.readable.getReader();
    this.writer = this.socket.writable.getWriter();
    this.decoder = new TextDecoder();
    this.buf = '';
  }

  upgrade() {
    this.reader.releaseLock();
    this.writer.releaseLock();
    this.socket = this.socket.startTls();
    this.attach();
  }

  async write(s) {
    await this.writer.write(enc.encode(s));
  }

  async readLine() {
    for (;;) {
      const i = this.buf.indexOf('\n');
      if (i >= 0) {
        const l = this.buf.slice(0, i + 1);
        this.buf = this.buf.slice(i + 1);
        return l;
      }
      const { value, done } = await this.reader.read();
      if (done) {
        const rest = this.buf;
        this.buf = '';
        return rest === '' ? null : rest;
      }
      this.buf += this.decoder.decode(value, { stream: true });
    }
  }

  async expect(codes) {
    let reply = '';
    for (;;) {
      const l = await this.readLine();
      if (l === null) break;
      reply += l;
      if (l.length < 4 || l[3] !== '-') break;
    }
    const code = parseInt(reply.slice(0, 3), 10) || 0;
    if (![].concat(codes).includes(code)) throw new Error('Antwort ' + (code || 'leer'));
  }

  async command(lineText, codes, secret = false) {
    await this.write(lineText + '\r\n');
    try {
      await this.expect(codes);
    } catch (e) {
      throw new Error((secret ? '[AUTH]' : lineText.split(' ')[0]) + ': ' + e.message);
    }
  }

  async quit() {
    try {
      await this.write('QUIT\r\n');
    } catch {}
    try {
      this.reader.releaseLock();
      this.writer.releaseLock();
      await this.socket.close();
    } catch {}
  }
}

export function mailer(cfg, deps) {
  return cfg.MAIL_TRANSPORT === 'smtp' ? new SmtpMailer(cfg, deps) : new LogMailer(cfg, deps);
}
