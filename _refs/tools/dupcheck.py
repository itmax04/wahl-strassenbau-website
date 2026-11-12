"""WEB-2026 (spec R-08.5): Fotos dürfen sich zwischen Seiten nur so wiederholen wie im Figma-Layout.

Quelle der erlaubten Verwendung: Frames der Seiten 02 Desktop / 03 Tablet / 04 Mobile und Tabelle «Fotos & Alt-Texte» (Figma 39:2,
_refs/figma/photos.json). Die Tabelle nennt nicht jede Verwendung (z. B. Service card «Pflasterarbeiten» auf Startseite/Danke = weg),
deshalb ist die Zuordnung hier aus den Frames übernommen.
Prüft außerdem: Alt-Texte entsprechen der Tabelle 39:2, nur die 15 Originalfotos, keine Fotos mit fast gleichem Inhalt (dHash).
Aufruf: python3 build.py && python3 _refs/tools/dupcheck.py   (Exit-Code 1 bei Verstoß)
"""
import html
import json
import pathlib
import re
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]
ALLOWED = {
    "weg": {"/", "/leistungsangebot/pflasterarbeiten/", "/technikangebot/", "/referenzen/", "/kontakt/danke/", "/404.html"},
    "rundplatz": {"/", "/leistungsangebot/garten-landschaft/", "/referenzen/", "/kontakt/danke/"},
    "logo-hammer": {"/", "/leistungsangebot/", "/leistungsangebot/pflasterarbeiten/", "/kontakt/danke/"},
    "medaillon": {"/", "/leistungsangebot/", "/leistungsangebot/pflasterarbeiten/", "/referenzen/"},
    "wappen-gruen": {"/", "/referenzen/"},
    "logo-mosaik": {"/", "/referenzen/"},
    "stern-beet": {"/", "/referenzen/"},
    "team-2020": {"/"},
    "segmentbogen": {"/leistungsangebot/", "/leistungsangebot/pflasterarbeiten/"},
    "tritt": {"/leistungsangebot/", "/leistungsangebot/garten-landschaft/"},
    "stier-ziegel": {"/leistungsangebot/pflasterarbeiten/"},
    "ornament": {"/leistungsangebot/garten-landschaft/"},
    "rosette": {"/leistungsangebot/garten-landschaft/"},
    "stiere-bau": {"/referenzen/"},
    "wappen-bau": {"/referenzen/"},
}
URLS = {"index.html": "/", "404.html": "/404.html"}


def page_url(p):
    rel = str(p.relative_to(ROOT))
    return URLS.get(rel, "/" + rel.replace("index.html", ""))


def dhash(path):
    im = Image.open(path).convert("L").resize((9, 8), Image.LANCZOS)
    px = list(im.getdata())
    return int("".join("1" if px[r * 9 + c] > px[r * 9 + c + 1] else "0" for r in range(8) for c in range(8)), 2)


def main():
    table = json.loads((ROOT / "_refs" / "figma" / "photos.json").read_text())
    used, bad = {}, []
    pages = [p for p in ROOT.glob("**/*.html") if not any(x in p.parts for x in ("src", "_refs", "docs", "server", "storage", "tests", ".git"))]
    for p in sorted(pages):
        url = page_url(p)
        for tag in re.findall(r"<img\b[^>]*>", p.read_text(encoding="utf8")):
            m = re.search(r'src="/assets/photos/([\w-]+)\.webp"', tag)
            if not m:
                continue
            name = m.group(1)
            used.setdefault(name, set()).add(url)
            alt = html.unescape(re.search(r'alt="([^"]*)"', tag).group(1))
            if name not in table:
                bad.append(f"{url}: unbekanntes Foto {name}")
            elif alt and alt != table[name]["alt"]:
                bad.append(f"{url}: Alt-Text {name} weicht von Figma 39:2 ab: «{alt}»")
    for name, pages_used in sorted(used.items()):
        extra = pages_used - ALLOWED.get(name, set())
        missing = ALLOWED.get(name, set()) - pages_used
        if extra:
            bad.append(f"{name}: nicht laut Figma verwendet auf {sorted(extra)}")
        if missing:
            bad.append(f"{name}: fehlt laut Figma auf {sorted(missing)}")
        print(f"{name:13s} {sorted(pages_used)}")
    names = sorted(used)
    hashes = {n: dhash(ROOT / f"assets/photos/{n}.webp") for n in names}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if bin(hashes[a] ^ hashes[b]).count("1") <= 6:
                bad.append(f"Fotos mit fast gleichem Inhalt: {a} / {b}")
    print("\nVERSTÖSSE:" if bad else "\nKeine Verstöße: Fotoverwendung wie im Figma-Layout, Alt-Texte laut 39:2.")
    for b in bad:
        print("  - " + b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
