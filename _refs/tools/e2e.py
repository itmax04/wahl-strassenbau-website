"""Phase E: Playwright-Prüfung aller Seiten (1440x900 und 390x844).
Prüft: Konsole/HTTP >= 400, horizontales Scrollen, Bilder (naturalWidth, width/height), Gold-Anzahl je Bildschirm, leere Halbbilder."""
import sys, json, io
from playwright.sync_api import sync_playwright
from PIL import Image
import numpy as np

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:5178'
PAGES = ['/', '/leistungsangebot/', '/leistungsangebot/pflasterarbeiten/', '/leistungsangebot/garten-landschaft/', '/technikangebot/',
         '/referenzen/', '/kontakt/', '/kontakt/danke/', '/about/', '/j/privacy/', '/j/legal-guarantee/', '/j/withdrawal/', '/sitemap/', '/404.html']
SIZES = {'desktop': (1440, 900), 'mobile': (390, 844)}

GOLD_JS = """() => {
  const vh = innerHeight, vw = innerWidth; let n = 0; const hits = [];
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.backgroundColor !== 'rgb(255, 192, 0)') continue;
    if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) < 0.05) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2 || r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw) continue;
    n++; hits.push((el.className || el.tagName) + ' ' + el.textContent.trim().slice(0, 20));
  }
  return [n, hits];
}"""

def empty_half(png):
    """Anteil nicht-einfarbiger Pixel je Bildschirmhälfte (links/rechts, oben/unten). Rückgabe: Liste leerer Hälften."""
    a = np.asarray(Image.open(io.BytesIO(png)).convert('L')).astype(np.int16)
    h, w = a.shape
    out = []
    def busy(reg):
        # Kanten: Pixel, die sich von ihrem rechten/unteren Nachbarn um > 12 unterscheiden
        dx = np.abs(np.diff(reg, axis=1)) > 12
        dy = np.abs(np.diff(reg, axis=0)) > 12
        return (dx.mean() + dy.mean()) / 2
    for name, reg in (('links', a[:, :w // 2]), ('rechts', a[:, w // 2:]), ('oben', a[:h // 2, :]), ('unten', a[h // 2:, :])):
        if busy(reg) < 0.0006:
            out.append(name)
    return out

report = {}
with sync_playwright() as p:
    b = p.chromium.launch(channel='chrome')
    for label, (w, h) in SIZES.items():
        ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1, reduced_motion='no-preference')
        for path in PAGES:
            pg = ctx.new_page()
            errs = []
            pg.on('console', lambda m, e=errs: e.append('console: ' + m.text) if m.type == 'error' else None)
            pg.on('response', lambda r, e=errs: e.append(f'HTTP {r.status} {r.url}') if r.status >= 400 and not r.url.endswith('/404.html') else None)
            pg.on('pageerror', lambda ex, e=errs: e.append('pageerror: ' + str(ex)))
            resp = pg.goto(BASE + path, wait_until='networkidle')
            if path != '/404.html' and resp.status >= 400:
                errs.append(f'Seitenstatus {resp.status}')
            H = pg.evaluate('document.documentElement.scrollHeight')
            y, gold_max, gold_hits, empties = 0, 0, [], []
            pg.mouse.move(w // 2, h // 2)
            pos = 0
            while pos < H:
                pg.mouse.wheel(0, 200); pg.wait_for_timeout(120); pos += 200
                H = pg.evaluate('document.documentElement.scrollHeight')
                n, hits = pg.evaluate(GOLD_JS)
                if n > gold_max:
                    gold_max, gold_hits = n, hits
                if label == 'desktop' and pos % 800 == 0:
                    eh = empty_half(pg.screenshot())
                    if eh:
                        empties.append((pos, eh))
            pg.wait_for_timeout(500)
            sw, iw = pg.evaluate('[document.documentElement.scrollWidth, innerWidth]')
            imgs = pg.evaluate("""() => [...document.images].filter(i => !i.closest('dialog.lightbox')).map(i => ({
                src: (i.currentSrc || i.src).split('/').pop(), nw: i.naturalWidth, w: i.getAttribute('width'), h: i.getAttribute('height')}))""")
            bad_imgs = [i for i in imgs if i['nw'] == 0 or not i['w'] or not i['h']]
            report[f'{label} {path}'] = {'errors': errs, 'overflow': sw != iw, 'sw_iw': [sw, iw], 'bad_imgs': bad_imgs,
                                          'gold_max': gold_max, 'gold_hits': gold_hits, 'empty_halves': empties, 'height': H}
            pg.close()
        ctx.close()
    b.close()

fails = 0
for k, v in report.items():
    problems = []
    if v['errors']: problems.append(f"Konsole/HTTP: {v['errors'][:3]}")
    if v['overflow']: problems.append(f"horizontales Scrollen {v['sw_iw']}")
    if v['bad_imgs']: problems.append(f"Bilder: {v['bad_imgs'][:3]}")
    if v['gold_max'] > 1: problems.append(f"Gold x{v['gold_max']}: {v['gold_hits']}")
    if v['empty_halves']: problems.append(f"leere Bildschirmhälften: {v['empty_halves']}")
    print(('FEHLER ' if problems else 'ok     ') + k + f"  (Höhe {v['height']}px)")
    for pr in problems:
        print('    -', pr)
    fails += bool(problems)
print(f'\n{len(report) - fails}/{len(report)} Seitenläufe ohne Befund')
json.dump(report, open('/tmp/e2e_report.json', 'w'), ensure_ascii=False, indent=1)
sys.exit(1 if fails else 0)
