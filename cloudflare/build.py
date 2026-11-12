#!/usr/bin/env python3
"""Paket für Cloudflare (Workers + Static Assets) bauen.

    python3 cloudflare/build.py            # baut zuerst die Seiten (../build.py), dann das Paket
    python3 cloudflare/build.py --no-site  # nur das Paket aus den vorhandenen HTML-Dateien

Ergebnis:
    cloudflare/dist/               öffentliche Dateien + _headers (entspricht .htaccess)
    cloudflare/worker/generated.js Formular-Texte (server/messages.json) und Server-Vorlagen (server/templates/)
    cloudflare/wahl-strassenbau-cloudflare.zip  alles zum Hochladen: wrangler.jsonc, worker/, dist/, schema.sql, README.md
dist/, generated.js und die ZIP-Datei sind Build-Ergebnisse (nicht in git).
"""
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIST = HERE / 'dist'
ZIP = HERE / 'wahl-strassenbau-cloudflare.zip'

# Wie README.md «Что выкладывать на хостинг», ohne PHP-Teile (kontakt.php, server/, storage/, .htaccess): die übernimmt der Worker
PUBLIC_FILES = ['index.html', '404.html', 'styles.css', 'main.js', 'robots.txt', 'sitemap.xml']
PUBLIC_DIRS = ['about', 'j', 'kontakt', 'leistungsangebot', 'referenzen', 'sitemap', 'technikangebot', 'fonts', 'assets']
SKIP = {'.DS_Store', 'Thumbs.db'}
TEMPLATES = ['layout', 'form-kontakt', 'form-kurz', 'form-widerruf', 'widerruf-done']

# Header wie .htaccess (Sicherheit, Zwischenspeicher). HTML: Cloudflare-Standard «max-age=0, must-revalidate» = no-cache.
HEADERS = """# Erzeugt von cloudflare/build.py — entspricht den Headern aus .htaccess
/*
  Strict-Transport-Security: max-age=31536000
  X-Content-Type-Options: nosniff
  X-Frame-Options: SAMEORIGIN
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
  Content-Security-Policy: default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; font-src 'self'; form-action 'self'; frame-ancestors 'self'; base-uri 'self'

/assets/*
  Cache-Control: public, max-age=31536000, immutable

/fonts/*
  Cache-Control: public, max-age=31536000, immutable

/styles.css
  Cache-Control: public, max-age=86400, must-revalidate

/main.js
  Cache-Control: public, max-age=86400, must-revalidate

/sitemap.xml
  Cache-Control: public, max-age=3600

/robots.txt
  Cache-Control: public, max-age=3600
"""

# Workers Static Assets: höchstens 25 MiB je Datei (Cloudflare-Limit)
MAX_FILE = 25 * 1024 * 1024


def build_site():
    subprocess.run([sys.executable, str(ROOT / 'build.py')], cwd=ROOT, check=True)


def build_dist():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for name in PUBLIC_FILES:
        shutil.copy2(ROOT / name, DIST / name)
    for name in PUBLIC_DIRS:
        shutil.copytree(ROOT / name, DIST / name, ignore=shutil.ignore_patterns(*SKIP))
    (DIST / '_headers').write_text(HEADERS, encoding='utf-8')
    files = [p for p in DIST.rglob('*') if p.is_file()]
    big = [p for p in files if p.stat().st_size > MAX_FILE]
    if big:
        sys.exit('Zu groß für Cloudflare (> 25 MiB): ' + ', '.join(str(p.relative_to(DIST)) for p in big))
    stray = [p for p in files if p.suffix in {'.php', '.py', '.md', '.sqlite', '.log'}]
    if stray:
        sys.exit('Interne Dateien in dist/: ' + ', '.join(str(p.relative_to(DIST)) for p in stray))
    return files


def build_generated():
    messages = json.loads((ROOT / 'server' / 'messages.json').read_text(encoding='utf-8'))
    messages.pop('_comment', None)
    templates = {}
    for name in TEMPLATES:
        templates[name] = (ROOT / 'server' / 'templates' / f'{name}.html').read_text(encoding='utf-8')
    out = ('// Erzeugt von cloudflare/build.py aus server/messages.json und server/templates/ — nicht von Hand ändern.\n'
           f'export const MESSAGES = {json.dumps(messages, ensure_ascii=False, indent=2)};\n'
           f'export const TEMPLATES = {json.dumps(templates, ensure_ascii=False)};\n')
    (HERE / 'worker' / 'generated.js').write_text(out, encoding='utf-8')


def build_zip():
    if ZIP.exists():
        ZIP.unlink()
    parts = ['README.md', 'wrangler.jsonc', 'schema.sql']
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in parts:
            z.write(HERE / name, f'wahl-strassenbau-cloudflare/{name}')
        for base in ('worker', 'dist'):
            for p in sorted((HERE / base).rglob('*')):
                if p.is_file() and p.name not in SKIP:
                    z.write(p, f'wahl-strassenbau-cloudflare/{p.relative_to(HERE)}')


def main():
    if '--no-site' not in sys.argv:
        build_site()
    files = build_dist()
    build_generated()
    build_zip()
    size = sum(p.stat().st_size for p in files)
    print(f'dist/: {len(files)} Dateien, {size / 1024 / 1024:.1f} MB')
    print(f'ZIP: {ZIP.relative_to(ROOT)} ({ZIP.stat().st_size / 1024 / 1024:.1f} MB)')


if __name__ == '__main__':
    main()
