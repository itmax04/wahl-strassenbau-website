"""WEB-2026 AC-02: Seite und Figma-Frame nebeneinander.

Aufruf:  python3 _refs/tools/figma_compare.py [BASE] [--only 01,07F] [--widths 1440,390] [--top 1600]
Ergebnis: _refs/shots/figma-compare/<NN>-<w>.png  (links Figma 1:1, rechts Seite, gleiche Breite)
         _refs/shots/figma-compare/report.json  (Höhen, Höhenabweichung in %)
Voraussetzungen: Server läuft (php -S localhost:5178 server/router.php), PNGs der Frames in _refs/shots/figma/<node>.png (P-00).
Animationen werden per prefers-reduced-motion abgeschaltet, damit alle Inhalte sichtbar sind.
"""
import json
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "_refs" / "shots" / "figma"
OUT = ROOT / "_refs" / "shots" / "figma-compare"

# Zustand -> (URL, Frames Desktop/Tablet/Mobile, Aktion)
STATES = {
    "01": ("/", ("8:2", "8:485", "8:925"), None),
    "02": ("/leistungsangebot/", ("10:390", "10:653", "10:939"), None),
    "03": ("/leistungsangebot/pflasterarbeiten/", ("10:1212", "10:1436", "10:1644"), None),
    "04": ("/leistungsangebot/garten-landschaft/", ("10:1846", "10:2079", "10:2299"), None),
    "05": ("/technikangebot/", ("11:956", "11:1198", "11:1456"), None),
    "06": ("/referenzen/", ("11:1701", "11:1954", "11:2194"), None),
    "07": ("/kontakt/", ("11:4352", "11:4583", "11:4801"), None),
    "07F": ("/kontakt/", ("37:2", "37:331", "37:611"), "kontakt-fehler"),
    "08": ("/kontakt/danke/", ("11:5013", "11:5200", "11:5376"), None),
    "09": ("/about/", ("12:1781", "12:1968", "12:2168"), None),
    "10": ("/j/privacy/", ("14:2264", "14:2563", "14:2853"), None),
    "11": ("/j/legal-guarantee/", ("12:2353", "12:2544", "12:2719"), None),
    "12": ("/j/withdrawal/", ("12:2888", "12:3066", "12:3233"), None),
    "13": ("/sitemap/", ("12:3394", "12:3573", "12:3741"), None),
    "14": ("/404.html", ("11:5546", "11:5674", "11:5791"), None),
    "M": ("/", (None, "17:7074", "18:5256"), "menu"),
}
WIDTHS = (1440, 1024, 390)


def action(page, name):
    if name == "kontakt-fehler":
        # Zustand 07F: Formular mit ungültigen Angaben absenden (Name gültig, E-Mail ungültig, Nachricht leer, keine Einwilligung)
        page.fill("#kontakt-name", "Test Nutzer")
        page.select_option("#kontakt-leistung", "Pflasterarbeiten")
        page.fill("#kontakt-email", "test@beispiel")
        page.click("form[data-form=kontakt] button[type=submit]")
        page.wait_for_timeout(200)
        page.evaluate("window.scrollTo(0, 0)")
    elif name == "menu":
        page.click(".hdr__menu")
        page.wait_for_timeout(150)


def shoot(pw_page, base, state, width):
    url, frames, act = STATES[state]
    idx = WIDTHS.index(width)
    node = frames[idx]
    if not node:
        return None
    fig_path = FIG / f"{node.replace(':', '-')}.png"
    fig = Image.open(fig_path).convert("RGB")
    if fig.width != width:  # Datenschutz mobil wurde von Figma verkleinert
        fig = fig.resize((width, round(fig.height * width / fig.width)), Image.LANCZOS)
    pw_page.set_viewport_size({"width": width, "height": 900 if width > 500 else 844})
    pw_page.goto(base + url, wait_until="networkidle")
    pw_page.evaluate("document.fonts.ready")
    if act:
        action(pw_page, act)
    if act == "menu":
        site = Image.open(BytesIO(pw_page.screenshot(full_page=False))).convert("RGB")
    else:
        # Bilder mit loading=lazy laden
        # Lazy-Bilder laden: schrittweise scrollen, auf alle Bilder warten, zurück nach oben
        pw_page.evaluate("""async () => {
          document.querySelectorAll('img[loading=lazy]').forEach(i => { i.loading = 'eager'; });
          for (let y = 0; y < document.documentElement.scrollHeight; y += innerHeight / 2) { scrollTo(0, y); await new Promise(r => setTimeout(r, 80)); }
          const wait = Promise.all([...document.images].map(i => (i.complete && i.naturalWidth) ? 0 : new Promise(r => { i.addEventListener('load', r); i.addEventListener('error', r); })));
          await Promise.race([wait, new Promise(r => setTimeout(r, 6000))]);
          scrollTo(0, 0); await new Promise(r => setTimeout(r, 150)); }""")
        site = Image.open(BytesIO(pw_page.screenshot(full_page=True))).convert("RGB")
    h = max(fig.height, site.height)
    sheet = Image.new("RGB", (width * 2 + 24, h + 40), (255, 0, 255))
    sheet.paste(fig, (0, 40))
    sheet.paste(site, (width + 24, 40))
    d = ImageDraw.Draw(sheet)
    d.text((8, 12), f"FIGMA {node}  {fig.height}px", fill=(0, 0, 0))
    d.text((width + 32, 12), f"SITE {url} @ {width}  {site.height}px", fill=(0, 0, 0))
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{state}-{width}.png"
    sheet.save(out)
    return {"state": state, "width": width, "node": node, "figma_h": fig.height, "site_h": site.height,
            "diff_pct": round(100 * (site.height - fig.height) / fig.height, 1), "file": str(out.relative_to(ROOT))}


def main():
    args = sys.argv[1:]
    base = "http://localhost:5178"
    only, widths = list(STATES), list(WIDTHS)
    i = 0
    while i < len(args):
        if args[i] == "--only":
            only = args[i + 1].split(",")
            i += 2
        elif args[i] == "--widths":
            widths = [int(w) for w in args[i + 1].split(",")]
            i += 2
        else:
            base = args[i].rstrip("/")
            i += 1
    results = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        ctx = b.new_context(reduced_motion="reduce", device_scale_factor=1)
        page = ctx.new_page()
        for st in only:
            for w in widths:
                r = shoot(page, base, st, w)
                if r:
                    results.append(r)
                    print(f"{st:>3} @{w:<4} figma {r['figma_h']:>6}  site {r['site_h']:>6}  Δ {r['diff_pct']:+.1f}%")
        b.close()
    rep = OUT / "report.json"
    old = json.loads(rep.read_text()) if rep.exists() else []
    keep = [o for o in old if (o["state"], o["width"]) not in {(r["state"], r["width"]) for r in results}]
    rep.write_text(json.dumps(keep + results, indent=1))


if __name__ == "__main__":
    main()
