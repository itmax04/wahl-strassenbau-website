"""WEB-2026 Ende-zu-Ende-Prüfung (Playwright, Chrome). Ersetzt e2e.py/e2e2.py (Lamborghini-Stil).

Aufruf:  python3 _refs/tools/e2e_figma.py [BASE]        (BASE Standard http://localhost:5178)
         python3 _refs/tools/e2e_figma.py BASE --webkit (zusätzlich Kernprüfungen in WebKit/Safari-Engine)
Deckt ab: AC-01 (Status, 404), AC-03 (kein horizontaler Scroll 320–1920), AC-04 (Prototyp-Routen aus _refs/figma/routes.json),
AC-05 Client (Fehlerzustand 07F, Übersicht mit Fokus, Erfolg → Danke, Widerruf D-05, ohne JavaScript), AC-06 (Skip-Link, ein h1,
Landmarks, Menü-Fokusfalle/Esc, Lightbox, Slider per Tastatur, reduced-motion, «STRASSENBAU»), AC-08 (SEO), Konsole ohne Fehler,
keine 404-Ressourcen, Druckansicht, «max. ein Primary-Button je Bildschirm» (ohne Kopfzeile, R-5).
Formular-Tests laufen gegen eine eigene php -S-Instanz mit temporärem Speicher (kein Rate-Limit-Konflikt mit dem Dev-Server).
Ergebnis: Konsole + _refs/shots/e2e/report.json; Exit 1 bei Fehlern.
"""
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "_refs" / "shots" / "e2e"
URLS = ["/", "/leistungsangebot/", "/leistungsangebot/pflasterarbeiten/", "/leistungsangebot/garten-landschaft/", "/technikangebot/",
        "/referenzen/", "/kontakt/", "/kontakt/danke/", "/about/", "/j/privacy/", "/j/legal-guarantee/", "/j/withdrawal/", "/sitemap/", "/404.html"]
WIDTHS = [320, 390, 768, 1024, 1280, 1440, 1920]
# Figma-Frame (Nummer im Namen) → URL
FRAME_URL = {"01": "/", "02": "/leistungsangebot/", "03": "/leistungsangebot/pflasterarbeiten/", "04": "/leistungsangebot/garten-landschaft/",
             "05": "/technikangebot/", "06": "/referenzen/", "07": "/kontakt/", "08": "/kontakt/danke/", "09": "/about/", "10": "/j/privacy/",
             "11": "/j/legal-guarantee/", "12": "/j/withdrawal/", "13": "/sitemap/", "14": "/404.html"}
TARGET_URL = {"Startseite": "/", "Leistungen": "/leistungsangebot/", "Pflasterarbeiten": "/leistungsangebot/pflasterarbeiten/",
              "Garten & Landschaft": "/leistungsangebot/garten-landschaft/", "Technik": "/technikangebot/", "Referenzen": "/referenzen/",
              "Kontakt": "/kontakt/", "Danke": "/kontakt/danke/", "Impressum": "/about/", "Datenschutz": "/j/privacy/",
              "Gewährleistung": "/j/legal-guarantee/", "Widerruf": "/j/withdrawal/"}

results = []


def rec(ok, name, detail=""):
    results.append({"ok": bool(ok), "name": name, "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail and not ok else ""))


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def start_form_server():
    port = free_port()
    storage = tempfile.mkdtemp(prefix="wahl-e2e-")
    env = dict(os.environ, MAIL_TRANSPORT="log", STORAGE_PATH=storage, RATE_LIMIT="200/600", MIN_FILL_SECONDS="1")
    proc = subprocess.Popen(["php", "-S", f"127.0.0.1:{port}", "-t", str(ROOT), str(ROOT / "server" / "router.php")],
                            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), 0.1).close()
            break
        except OSError:
            time.sleep(0.05)
    return proc, f"http://127.0.0.1:{port}", storage


def check_pages(browser, base):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    for u in URLS:
        page = ctx.new_page()
        console, failed, bad_res = [], [], []
        page.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console.append(str(e)))
        page.on("requestfailed", lambda r: failed.append(r.url))
        page.on("response", lambda r: bad_res.append(r.url) if r.status >= 400 and not r.url.endswith("/404.html") else None)
        resp = page.goto(base + u, wait_until="networkidle")
        page.evaluate("""async () => { for (let y = 0; y < document.documentElement.scrollHeight; y += innerHeight) { scrollTo(0, y); await new Promise(r => setTimeout(r, 40)); } }""")
        page.wait_for_load_state("networkidle")
        broken = page.evaluate("[...document.images].filter(i => i.getAttribute('src') && i.complete && i.naturalWidth === 0).map(i => i.currentSrc || i.src)")
        status_ok = resp.status == 200
        h1 = page.evaluate("document.querySelectorAll('h1').length")
        land = page.evaluate("['header','main','footer','nav'].every(t => document.querySelector(t))")
        lang = page.evaluate("document.documentElement.lang")
        first_tab = page.evaluate("(() => { const a = document.querySelector('a, button, input'); return a && a.classList.contains('skip'); })()")
        ok = status_ok and h1 == 1 and land and lang == "de" and first_tab and not console and not failed and not broken and not bad_res
        rec(ok, f"Seite {u}: 200, ein h1, Landmarks, lang=de, Skip-Link zuerst, Konsole/Ressourcen sauber",
            f"status={resp.status} h1={h1} land={land} lang={lang} skip={first_tab} console={console[:2]} failed={failed[:2]} broken={broken[:2]} 4xx={bad_res[:2]}")
        page.close()
    page = ctx.new_page()
    resp = page.goto(base + "/gibt-es-nicht/", wait_until="domcontentloaded")
    rec(resp.status == 404 and "Seite nicht gefunden" in page.content(), "AC-01 unbekannte URL → 404 mit /404.html", f"status={resp.status}")
    ctx.close()


def check_overflow(page, base):
    bad = []
    for w in WIDTHS:
        page.set_viewport_size({"width": w, "height": 800})
        for u in URLS:
            page.goto(base + u, wait_until="domcontentloaded")
            sw, cw = page.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
            if sw > cw:
                bad.append(f"{u}@{w}: {sw}>{cw}")
    rec(not bad, f"AC-03 kein horizontaler Scroll ({len(WIDTHS)} Breiten × {len(URLS)} URLs)", "; ".join(bad[:10]))


def norm_href(base, page_url, href):
    if href.startswith(("tel:", "mailto:")):
        return href
    full = urljoin(base + page_url, href)
    p = urlparse(full)
    return p.netloc + "|" + p.path + ("#" + p.fragment if p.fragment else "")


def check_routes(page, base):
    routes = json.loads((ROOT / "_refs" / "figma" / "routes.json").read_text())
    netloc = urlparse(base).netloc
    cache = {}
    missing, checked = [], set()
    for r in routes:
        num = re.search(r"/ (\d\d)", r["frame"])
        if not num:
            continue
        url = FRAME_URL[num.group(1)]
        key = (url, r["layer"], r["target"])
        if key in checked:
            continue
        checked.add(key)
        if url not in cache:
            page.goto(base + url, wait_until="domcontentloaded")
            cache[url] = page.evaluate("""() => ({
              links: [...document.querySelectorAll('a[href]')].filter(a => !a.closest('.menu')).map(a => [a.getAttribute('href'), a.textContent.trim()]),
              ids: [...document.querySelectorAll('[id]')].map(e => [e.id, e.textContent.trim().slice(0, 80)]),
              forms: [...document.querySelectorAll('form')].map(f => f.getAttribute('action')) })""")
        d = cache[url]
        t = r["target"]
        hrefs = [norm_href(base, url, h) for h, _ in d["links"]]
        ok = False
        if t in TARGET_URL:
            if r["layer"].startswith("Submit"):
                ok = "/kontakt.php" in d["forms"]
            else:
                want = netloc + "|" + TARGET_URL[t]
                ok = any(h.split("#")[0] == want for h in hrefs)
        elif t == "Kontakt – Fehler":
            ok = "/kontakt.php" in d["forms"]
        elif t.startswith(("tel:", "mailto:")):
            ok = t in hrefs
        elif t == "maps":
            ok = any("google.com/maps" in h for h, _ in d["links"])
        elif t.startswith("http"):
            ok = any(h == t for h, _ in d["links"])
        elif t == "#top":
            ok = any(h == "#top" for h, _ in d["links"])
        elif t.startswith("#"):
            label = t[1:].strip()
            ok = any(txt.startswith(label[:40]) and h.startswith("#") for h, txt in d["links"])
        if not ok:
            missing.append(f"{url}: {r['layer']} → {t}")
    rec(not missing, f"AC-04 Prototyp-Routen: {len(checked)} eindeutige Routen geprüft", "; ".join(missing[:15]))
    return len(checked), missing


def check_seo(page, base):
    bad = []
    for u in URLS:
        page.goto(base + u, wait_until="domcontentloaded")
        info = page.evaluate("""() => ({
          title: document.title, desc: document.querySelector('meta[name=description]')?.content || '',
          canonical: document.querySelector('link[rel=canonical]')?.href || '', robots: document.querySelector('meta[name=robots]')?.content || '',
          og: document.querySelector('meta[property="og:image"]')?.content || '',
          ld: [...document.querySelectorAll('script[type="application/ld+json"]')].map(s => s.textContent) })""")
        noindex = u in ("/kontakt/danke/", "/404.html")
        try:
            [json.loads(x) for x in info["ld"]]
            ld_ok = True
        except ValueError:
            ld_ok = False
        ok = info["title"] and info["desc"] and info["og"].startswith("https://www.wahl-strassenbau.de/assets/og/") and ld_ok
        ok = ok and (("noindex" in info["robots"] and not info["canonical"]) if noindex else info["canonical"] == "https://www.wahl-strassenbau.de" + u)
        ok = ok and (bool(info["ld"]) or noindex)
        og_file = ROOT / urlparse(info["og"]).path.lstrip("/")
        ok = ok and og_file.exists()
        if not ok:
            bad.append(f"{u}: {info}")
    sm = urllib.request.urlopen(base + "/sitemap.xml").read().decode()
    locs = re.findall(r"<loc>([^<]+)</loc>", sm)
    rec(not bad and len(locs) == 12 and not any("danke" in l or "404" in l for l in locs),
        "AC-08 SEO: title/description/canonical/og:image/JSON-LD, noindex Danke+404, sitemap 12 URLs", "; ".join(bad[:3]) + f" sitemap={len(locs)}")


def check_a11y(browser, base):
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    page.goto(base + "/", wait_until="networkidle")
    text = page.evaluate("document.querySelector('.hdr .logo span').innerText")
    rec("STRASSENBAU" in text, "«ß» in Versalien als «SS» (Logo: «WAHL STRASSENBAU»)", text)
    # Skip-Link
    page.keyboard.press("Tab")
    skip_visible = page.evaluate("document.activeElement.classList.contains('skip') && document.activeElement.getBoundingClientRect().top >= 0")
    page.keyboard.press("Enter")
    rec(skip_visible and page.evaluate("location.hash") == "#inhalt", "Skip-Link «Zum Inhalt springen» sichtbar bei Fokus und springt zu main")
    # Menü
    page.goto(base + "/", wait_until="networkidle")
    page.focus(".hdr__menu")
    page.keyboard.press("Enter")
    page.wait_for_timeout(100)
    opened = page.evaluate("!document.getElementById('menu').hidden && document.querySelector('.hdr__menu').getAttribute('aria-expanded') === 'true'")
    focus_close = page.evaluate("document.activeElement.classList.contains('menu__close')")
    locked = page.evaluate("document.body.classList.contains('is-locked')")
    trapped = True
    for _ in range(25):
        page.keyboard.press("Tab")
        if not page.evaluate("document.getElementById('menu').contains(document.activeElement)"):
            trapped = False
            break
    page.keyboard.press("Shift+Tab")
    trapped = trapped and page.evaluate("document.getElementById('menu').contains(document.activeElement)")
    page.keyboard.press("Escape")
    page.wait_for_timeout(100)
    closed = page.evaluate("document.getElementById('menu').hidden && document.activeElement.classList.contains('hdr__menu') && !document.body.classList.contains('is-locked')")
    rec(opened and focus_close and locked and trapped and closed, "Mobiles Menü: aria-expanded, Fokus auf Schließen, Fokusfalle, Scroll-Sperre, Esc, Fokus zurück",
        f"open={opened} focus={focus_close} locked={locked} trap={trapped} closed={closed}")
    # Lightbox
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(base + "/leistungsangebot/pflasterarbeiten/", wait_until="networkidle")
    tile = page.locator(".gallery a[data-lightbox]").first
    tile.scroll_into_view_if_needed()
    tile.focus()
    page.keyboard.press("Enter")
    page.wait_for_timeout(200)
    is_open = page.evaluate("document.querySelector('dialog.lightbox')?.open === true")
    c1 = page.evaluate("document.querySelector('.lightbox__count').textContent")
    page.keyboard.press("ArrowRight")
    c2 = page.evaluate("document.querySelector('.lightbox__count').textContent")
    page.keyboard.press("Escape")
    page.wait_for_timeout(150)
    back = page.evaluate("document.activeElement === document.querySelector('.gallery a[data-lightbox]')")
    rec(is_open and c1 == "1 / 4" and c2 == "2 / 4" and back, "Lightbox (<dialog>): öffnen per Tastatur, Pfeile, Esc, Fokus zurück auf die Kachel", f"{is_open} {c1} {c2} {back}")
    # Vorher/Nachher-Slider
    page.goto(base + "/referenzen/", wait_until="networkidle")
    rng = page.locator(".compare input[type=range]")
    rng.focus()
    page.keyboard.press("ArrowLeft")
    page.keyboard.press("ArrowLeft")
    val = page.evaluate("[document.querySelector('.compare input').value, getComputedStyle(document.querySelector('.compare')).getPropertyValue('--pct').trim(), document.querySelector('.compare input').getAttribute('aria-label')]")
    rec(val[0] == "48" and val[1] == "48%" and val[2] == "Vergleich: Wappenmosaik fertig und während der Verlegung",
        "Vorher/Nachher-Slider per Tastatur (range, aria-label laut spec)", str(val))
    # Fokus-Ring sichtbar
    page.goto(base + "/kontakt/", wait_until="networkidle")
    page.focus("#kontakt-name")
    page.wait_for_timeout(300)
    ring = page.evaluate("getComputedStyle(document.querySelector('#kontakt-name')).boxShadow")
    page.keyboard.press("Tab")
    rec("244, 196, 49" in ring, "Fokuszustand Feld: gelbe Umrandung + Ring", ring)
    # Sticky-Kopfzeile
    page.evaluate("scrollTo(0, 400)")
    page.wait_for_timeout(400)
    sticky = page.evaluate("[document.querySelector('.hdr').classList.contains('is-sticky'), getComputedStyle(document.querySelector('.hdr')).height]")
    rec(sticky[0] and sticky[1] == "76px", "Kopfzeile Sticky nach Scrollen > 8 px (Desktop 76 px)", str(sticky))
    # «Nach oben» auf Datenschutz
    page.goto(base + "/j/privacy/", wait_until="networkidle")
    page.evaluate("scrollTo(0, 3000)")
    page.wait_for_timeout(600)
    top_vis = page.evaluate("document.querySelector('[data-totop]').classList.contains('is-visible')")
    active = page.evaluate("document.querySelector('.toc a[aria-current]')?.textContent")
    rec(top_vis and active and active != "Datenschutzerklärung", "Datenschutz: «Nach oben» nach 600 px, TOC-Scroll-Spy", f"{top_vis} {active}")
    ctx.close()
    # reduced motion
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    page.goto(base + "/", wait_until="networkidle")
    rm = page.evaluate("""() => { const el = document.querySelector('[data-stagger] > *');
      return [getComputedStyle(el).opacity, getComputedStyle(document.documentElement).scrollBehavior, getComputedStyle(document.querySelector('h1')).animationName]; }""")
    rec(rm[0] == "1" and rm[1] == "auto" and rm[2] in ("none", "wipe"), "prefers-reduced-motion: Inhalte sofort sichtbar, kein Smooth-Scroll", str(rm))
    page.emulate_media(media="print")
    page.goto(base + "/about/", wait_until="networkidle")
    pr = page.evaluate("[getComputedStyle(document.querySelector('.hdr')).display, getComputedStyle(document.querySelector('.toc')).display, getComputedStyle(document.querySelector('.ftr')).display]")
    rec(pr == ["none", "none", "none"], "Druckansicht Rechtstexte ohne Kopfzeile, Inhaltsverzeichnis, Fußzeile", str(pr))
    ctx.close()


def check_primary(browser, base):
    bad = []
    for w, h in ((1440, 900), (390, 844)):
        ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
        page = ctx.new_page()
        for u in URLS:
            page.goto(base + u, wait_until="domcontentloaded")
            n = page.evaluate("""async () => { let max = 0;
              for (let y = 0; y < document.documentElement.scrollHeight; y += innerHeight / 2) { scrollTo(0, y); await new Promise(r => setTimeout(r, 20));
                const c = [...document.querySelectorAll('.btn--primary')].filter(b => !b.closest('.hdr, .menu') && b.offsetParent !== null)
                  .filter(b => { const r = b.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight; }).length;
                max = Math.max(max, c); } return max; }""")
            if n > 1:
                bad.append(f"{u}@{w}: {n}")
        ctx.close()
    rec(not bad, "Höchstens ein Primary-Button je Bildschirm (ohne Kopfzeile)", "; ".join(bad))


def check_forms(browser):
    proc, base, storage = start_form_server()
    try:
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(base + "/kontakt/", wait_until="networkidle")
        page.fill("#kontakt-email", "test@beispiel")
        page.click("form[data-form=kontakt] button[type=submit]")
        page.wait_for_timeout(200)
        st = page.evaluate("""() => ({ sum: !document.querySelector('.errsum').hidden, focus: document.activeElement.classList.contains('errsum'),
          text: document.querySelector('.errsum__text').textContent,
          inv: [...document.querySelectorAll('[aria-invalid=true]')].map(e => e.name) })""")
        rec(st["sum"] and st["focus"] and set(st["inv"]) == {"name", "email", "nachricht", "einwilligung"} and "Außerdem ist die Einwilligung erforderlich" in st["text"],
            "07F: Fehlerübersicht (role=alert) mit Fokus, aria-invalid an Name/E-Mail/Nachricht/Einwilligung", str(st))
        page.fill("#kontakt-name", "Test Nutzer")
        page.fill("#kontakt-email", "test@beispiel.de")
        page.fill("#kontakt-nachricht", "Testanfrage für die Abnahme.")
        page.check("#kontakt-einwilligung")
        page.wait_for_timeout(1100)
        with page.expect_navigation():
            page.click("form[data-form=kontakt] button[type=submit]")
        rec(page.url.endswith("/kontakt/danke/"), "Kontakt mit JavaScript: Erfolg → /kontakt/danke/", page.url)
        page.goto(base + "/", wait_until="networkidle")
        page.fill("#kurz-name", "Test")
        page.fill("#kurz-telefon", "0381 123456")
        page.fill("#kurz-nachricht", "Rückruf bitte")
        page.check("#kurz-einwilligung")
        page.wait_for_timeout(1100)
        with page.expect_navigation():
            page.click("form[data-form=kurz] button[type=submit]")
        rec(page.url.endswith("/kontakt/danke/"), "Kurzanfrage (Startseite): Erfolg → /kontakt/danke/", page.url)
        page.goto(base + "/j/withdrawal/", wait_until="networkidle")
        page.fill("#widerruf-name", "Test")
        page.fill("#widerruf-bestellnummer", "B-1")
        page.fill("#widerruf-email", "test@beispiel.de")
        page.wait_for_timeout(1100)
        page.click("form[data-form=widerruf] button[type=submit]")
        page.wait_for_selector("#widerruf-done:not([hidden])")
        rec(page.evaluate("document.activeElement.id") == "widerruf-done" and page.evaluate("document.querySelector('form[data-form=widerruf]').hidden"),
            "Widerruf mit JavaScript: Bestätigung im selben Bereich, Fokus darauf (D-05)")
        # Netzwerkfehler → allgemeine Meldung mit Telefon
        page.goto(base + "/kontakt/", wait_until="networkidle")
        page.route("**/kontakt.php", lambda r: r.abort())
        page.fill("#kontakt-name", "Test")
        page.fill("#kontakt-email", "test@beispiel.de")
        page.fill("#kontakt-nachricht", "Testanfrage für die Abnahme.")
        page.check("#kontakt-einwilligung")
        page.click("form[data-form=kontakt] button[type=submit]")
        page.wait_for_timeout(300)
        status = page.evaluate("document.querySelector('form[data-form=kontakt] .form__status').textContent")
        rec("0381 25 22 39 41" in status and not page.evaluate("document.querySelector('form[data-form=kontakt] [type=submit]').disabled"),
            "Netzwerkfehler: Hinweis mit Telefonnummer, Button wieder aktiv", status)
        ctx.close()
        # ohne JavaScript
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, java_script_enabled=False, reduced_motion="reduce")
        page = ctx.new_page()
        page.goto(base + "/kontakt/", wait_until="domcontentloaded")
        page.fill("#kontakt-name", "Ohne JS")
        page.fill("#kontakt-email", "nojs@beispiel.de")
        page.fill("#kontakt-nachricht", "Anfrage ohne JavaScript.")
        page.check("#kontakt-einwilligung")
        with page.expect_navigation():
            page.click("form[data-form=kontakt] button[type=submit]")
        rec(page.url.endswith("/kontakt/danke/"), "Ohne JavaScript: POST → 303 → /kontakt/danke/", page.url)
        page.goto(base + "/kontakt/", wait_until="domcontentloaded")
        page.fill("#kontakt-name", "<b>x</b>")
        with page.expect_navigation():
            page.click("form[data-form=kontakt] button[type=submit]")
        html = page.content()
        rec("Bitte prüfen Sie die markierten Felder." in html and 'value="&lt;b&gt;x&lt;/b&gt;"' in html and 'class="hdr"' in html,
            "Ohne JavaScript: Fehlerseite im Stil der Website mit Übersicht und erhaltenen (escapten) Eingaben")
        ctx.close()
        rows = subprocess.run(["php", str(ROOT / "server/bin/submissions.php"), "list"], env=dict(os.environ, STORAGE_PATH=storage),
                              capture_output=True, text=True).stderr
        rec("4 Anfrage(n)" in rows, "Gespeicherte Anfragen der Formular-Tests: 4 (kontakt, kurz, widerruf, ohne JS)", rows.strip())
    finally:
        proc.terminate()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = (args[0] if args else "http://localhost:5178").rstrip("/")
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        check_pages(browser, base)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        check_overflow(page, base)
        n_routes, _ = check_routes(page, base)
        check_seo(page, base)
        page.close()
        check_a11y(browser, base)
        check_primary(browser, base)
        check_forms(browser)
        browser.close()
        if "--webkit" in sys.argv:
            try:
                wk = p.webkit.launch()
                pg = wk.new_page(viewport={"width": 390, "height": 844})
                bad = []
                for u in URLS:
                    r = pg.goto(base + u, wait_until="load")
                    sw, cw = pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
                    if r.status != 200 or sw > cw:
                        bad.append(f"{u}: {r.status} {sw}>{cw}")
                rec(not bad, "WebKit (Safari-Engine) 390 px: 14 URLs laden, kein horizontaler Scroll", "; ".join(bad))
                wk.close()
            except Exception as e:  # WebKit nicht installiert
                rec(False, "WebKit-Prüfung", f"NOT RUN: {e}")
    failed = [r for r in results if not r["ok"]]
    (OUT / "report.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    print(f"\n{len(results) - len(failed)}/{len(results)} Prüfungen bestanden")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
