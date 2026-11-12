#!/usr/bin/env python3
"""Baut die statische Seite: src/layout.html + src/pages/*.html -> fertige HTML-Dateien.

Aufruf: python3 build.py
Die Ergebnisse sind gewöhnliche HTML-Dateien (kein Framework nötig zum Betrieb).
Jede Seite in src/pages/ beginnt mit Kopfzeilen (title, description, class …), dann '---', dann der Inhalt.
Die URLs entsprechen den bisherigen Jimdo-Adressen, damit keine Weiterleitungen nötig sind.
Gestaltung: Figma «Website 2026» (DESIGN.md). Komponenten-Markup entsteht hier, damit es nur einen Ort gibt.
"""
import json
import re
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"
TODAY = date.today()

# (URL-Pfad, Quelldatei ohne .html, Navigationspunkt)
PAGES = [
    ("/", "index", "start"),
    ("/leistungsangebot/", "leistungen", "leistungen"),
    ("/leistungsangebot/pflasterarbeiten/", "pflasterarbeiten", "pflaster"),
    ("/leistungsangebot/garten-landschaft/", "garten-landschaft", "garten"),
    ("/technikangebot/", "technik", "technik"),
    ("/referenzen/", "referenzen", "referenzen"),
    ("/kontakt/", "kontakt", "kontakt"),
    ("/kontakt/danke/", "danke", ""),
    ("/about/", "impressum", ""),
    ("/j/privacy/", "datenschutz", ""),
    ("/j/legal-guarantee/", "gewaehrleistung", ""),
    ("/j/withdrawal/", "widerruf", ""),
    ("/sitemap/", "sitemap", ""),
    ("/404.html", "404", ""),
]
# Brotkrumen: URL -> (Bezeichnung, übergeordnete URL)
CRUMBS = {
    "/leistungsangebot/": ("Leistungen", "/"),
    "/leistungsangebot/pflasterarbeiten/": ("Pflasterarbeiten", "/leistungsangebot/"),
    "/leistungsangebot/garten-landschaft/": ("Garten & Landschaft", "/leistungsangebot/"),
    "/technikangebot/": ("Technik", "/"),
    "/referenzen/": ("Referenzen", "/"),
    "/kontakt/": ("Kontakt", "/"),
    "/kontakt/danke/": ("Danke", "/kontakt/"),
    "/about/": ("Impressum", "/"),
    "/j/privacy/": ("Datenschutz", "/"),
    "/j/legal-guarantee/": ("Gesetzliche Gewährleistung", "/"),
    "/j/withdrawal/": ("Vertrag widerrufen", "/"),
    "/sitemap/": ("Sitemap", "/"),
}
# Bild für die Vorschau in sozialen Netzwerken (OG) je Seite: Name aus assets/photos/
OG_PHOTO = {"/": "weg", "/leistungsangebot/": "segmentbogen", "/leistungsangebot/pflasterarbeiten/": "weg",
            "/leistungsangebot/garten-landschaft/": "rundplatz", "/referenzen/": "wappen-gruen", "/kontakt/danke/": "rundplatz"}
OG_DEFAULT_PHOTO = "segmentbogen"
# Navigationsschlüssel: Kopfzeile (Bereich) und Menü (genaue Seite)
NAV_AREA = {"leistungen": "leistungen", "pflaster": "leistungen", "garten": "leistungen", "technik": "technik",
            "referenzen": "referenzen", "kontakt": "kontakt"}
# Produktiv-Domain für canonical, Open Graph und sitemap.xml (bei anderem Domainnamen hier ändern)
SITE = "https://www.wahl-strassenbau.de"
PHONE_HREF = "tel:+4938125223941"
PHONE = "0381 25 22 39 41"
MAPS = "https://www.google.com/maps/dir/?api=1&amp;destination=Ringstra%C3%9Fe+25,+18059+Papendorf"


def years_since(year, month):
    """Volle Jahre seit Gründung (Mai 2005) zum Build-Datum."""
    return TODAY.year - year - (1 if TODAY.month < month else 0)


# ---- Icons (Figma «Icon / *», 24 px, Strich 1,75; Pfade in src/icons/) ---------------------------------
_icons = {}


def icon(name, cls="i"):
    if name not in _icons:
        _icons[name] = (SRC / "icons" / f"{name}.svg").read_text(encoding="utf8").strip()
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{_icons[name]}</svg>')


# ---- Bilder: <picture> mit AVIF/WebP, srcset, width/height -----------------------------------------
PHOTOS = ROOT / "assets" / "photos"
_dims = {}
# Alt-Texte: Figma-Tabelle «Fotos & Alt-Texte» (Node 39:2), siehe _refs/figma/photos.json
ALT = {
    "weg": "Geschwungener Weg aus Natursteinpflaster durch einen Garten, links eine Trockenmauer aus Naturstein.",
    "medaillon": "Straßenbauer verlegt ein Natursteinmosaik mit dunklem Medaillon in Bruchsteinplatten.",
    "rundplatz": "Runder Platz aus hellem Natursteinpflaster mit Mulchfläche und Findlingen.",
    "segmentbogen": "Segmentbogenpflaster aus hellem Naturstein mit dunklen Bögen.",
    "logo-hammer": "Logo-Mosaik aus Naturstein (Hand mit Hammer) in rundem Rahmen.",
    "stier-ziegel": "Stiermotiv als Mosaik aus rötlichen Pflastersteinen.",
    "logo-mosaik": "Firmenlogo als Mosaik aus Pflastersteinen.",
    "stiere-bau": "Zwei Stiermotive aus hellen Pflastersteinen während der Verlegung.",
    "wappen-gruen": "Wappenmosaik mit Greif aus Pflastersteinen in einer Grünanlage mit Tulpen (fertig).",
    "wappen-bau": "Wappenmosaik während der Verlegung.",
    "stern-beet": "Weißer Stern aus Pflastersteinen in einem Beet mit Buchskugeln.",
    "tritt": "Trittplatten aus Naturstein im Rasen mit geschwungener Pflasterkante.",
    "ornament": "Geschwungenes Ornament aus Pflastersteinen im Rasen um eine Holzfläche.",
    "rosette": "Runde Rosette aus Natursteinpflaster während der Verlegung.",
    "team-2020": "Das Team von Wahl Straßenbau, Sommer 2020, vor dem Firmengebäude.",
}


def img_dims(path):
    """(Breite, Höhe) einer lokalen Bilddatei; SVG wird nicht gelesen."""
    path = Path(path)
    if path not in _dims:
        from PIL import Image
        with Image.open(path) as im:
            _dims[path] = im.size
    return _dims[path]


def photo_sources(name, ext):
    files = []
    base = PHOTOS / f"{name}.{ext}"
    if base.exists():
        # AVIF hat dieselben Maße wie die WebP-Datei (Pillow liest kein AVIF)
        files.append((img_dims(PHOTOS / f"{name}.webp")[0], f"/assets/photos/{name}.{ext}"))
    for p in PHOTOS.glob(f"{name}-*.{ext}"):
        m = re.fullmatch(rf"{re.escape(name)}-(\d+)\.{ext}", p.name)
        if m:
            files.append((int(m.group(1)), f"/assets/photos/{p.name}"))
    return sorted(set(files))


USED_PHOTOS = {}  # Name -> Liste der Seiten (für dupcheck)
_current_url = ["/"]
_preload = []


def photo_tag(name, alt=None, sizes="100vw", cls="", eager=False, pos="", decorative=False, zoom=""):
    base = PHOTOS / f"{name}.webp"
    if not base.exists():
        raise SystemExit(f"Foto fehlt: assets/photos/{name}.webp")
    USED_PHOTOS.setdefault(name, []).append(_current_url[0])
    alt = "" if decorative else (ALT.get(name, "") if alt is None else alt)
    w, h = img_dims(base)
    parts = ['<picture>']
    for ext, mime in (("avif", "image/avif"), ("webp", "image/webp")):
        srcs = photo_sources(name, ext)
        if srcs:
            srcset = ", ".join(f"{u} {wd}w" for wd, u in srcs)
            parts.append(f'<source type="{mime}" srcset="{srcset}" sizes="{sizes}">')
            if eager and ext == "avif":
                _preload.append(f'<link rel="preload" as="image" type="image/avif" imagesrcset="{srcset}" imagesizes="{sizes}" fetchpriority="high">')
    attrs = [f'src="/assets/photos/{name}.webp"', f'width="{w}"', f'height="{h}"', f'alt="{escape(alt)}"']
    if cls:
        attrs.append(f'class="{cls}"')
    attrs.append('loading="eager" fetchpriority="high"' if eager else 'loading="lazy"')
    attrs.append('decoding="async"')
    style = []
    if pos:
        style.append(f"object-position: {pos}")
    if zoom:  # Bildausschnitt wie in Figma (CROP > Fläche): Skalierung um den Fokuspunkt
        style.append(f"transform: scale({zoom}); transform-origin: {pos or '50% 50%'}")
    if style:
        attrs.append(f'style="{"; ".join(style)}"')
    parts.append(f'<img {" ".join(attrs)}>')
    parts.append('</picture>')
    return "".join(parts)


def photo_macro(match):
    name = match.group(1)
    opts = {"sizes": "100vw", "class": "", "pos": "", "alt": None, "zoom": ""}
    flags = set()
    for arg in (match.group(2) or "").split("|"):
        if not arg:
            continue
        if "=" in arg:
            k, v = arg.split("=", 1)
            opts[k.strip()] = v.strip()
        else:
            flags.add(arg.strip())
    return photo_tag(name, opts["alt"], opts["sizes"], opts["class"], "eager" in flags, opts["pos"], "deco" in flags, opts["zoom"])


def add_dimensions(html):
    """width/height für alle übrigen lokalen <img> (Layout-Sprünge vermeiden)."""
    def fix(m):
        tag = m.group(0)
        if re.search(r"\swidth=", tag):
            return tag
        src = re.search(r'src="(/assets/[^"]+)"', tag)
        if not src:
            return tag
        p = ROOT / src.group(1).lstrip("/")
        if not p.exists() or p.suffix == ".svg":
            return tag
        w, h = img_dims(p)
        return tag[:-1].rstrip("/").rstrip() + f' width="{w}" height="{h}">'
    return re.sub(r"<img\b[^>]*>", fix, html)


# ---- Formulare (ein Ort für Markup und Texte; Server: server/lib/Validator.php, Skript: main.js) ------
# Texte: Figma-Komponenten «Contact field» (7:589), «Consent checkbox» (7:605) und Zustand «Kontakt – Fehler» (37:2)
# Auswahlliste «Leistung»: gleiche Liste in server/lib/Validator.php (Test prüft Gleichheit)
SERVICES = ["Pflasterarbeiten", "Garten & Landschaft", "Asphalt- & Erdarbeiten", "Havarie", "Sonstiges"]
# Texte: server/messages.json (gleiche Quelle wie server/lib/Validator.php)
MSG = {k: v for k, v in json.loads((ROOT / "server" / "messages.json").read_text(encoding="utf8")).items() if not k.startswith("_")}
CONSENT = ('Ich habe die <a href="/j/privacy/">Datenschutzerklärung</a> gelesen und bin einverstanden, dass meine Angaben '
           'zur Bearbeitung der Anfrage verwendet werden. *')
PRIVACY_NOTE = 'Es gilt die <a href="/j/privacy/">Datenschutzerklärung</a>. Hinweis: Bitte die mit * gekennzeichneten Felder ausfüllen.'


def _field(form, key, label, kind="text", required=False, autocomplete="", help_text="", rows=0, options=None,
           maxlength=0, placeholder="", msg="", inputmode=""):
    fid = f"{form}-{key}"
    star = " *" if required else ""
    attrs = [f'id="{fid}"', f'name="{key}"']
    if required:
        attrs.append("required")
    if autocomplete:
        attrs.append(f'autocomplete="{autocomplete}"')
    if maxlength:
        attrs.append(f'maxlength="{maxlength}"')
    if placeholder:
        attrs.append(f'placeholder="{escape(placeholder)}"')
    if inputmode:
        attrs.append(f'inputmode="{inputmode}"')
    described = [f"{fid}-err"] + ([f"{fid}-help"] if help_text else [])
    attrs.append(f'aria-describedby="{" ".join(described)}"')
    attrs.append(f'data-msg="{escape(msg or MSG["required"])}"')
    a = " ".join(attrs)
    box_cls = "field__box"
    if options is not None:
        opts = f'<option value="">{escape(placeholder or "Bitte wählen")}</option>' + "".join(
            f'<option value="{escape(o)}">{escape(o)}</option>' for o in options)
        a = a.replace(f' placeholder="{escape(placeholder)}"', "") if placeholder else a
        control = f'<select {a}>{opts}</select>{icon("chevron-down", "i field__state field__state--chev")}'
        box_cls += " field__box--select"
    elif rows:
        control = f'<textarea {a} rows="{rows}"></textarea>'
    else:
        control = f'<input {a} type="{kind}">'
    states = icon("alert", "i field__state field__state--err") + icon("check", "i field__state field__state--ok")
    help_html = f'\n            <p class="field__help" id="{fid}-help">{help_text}</p>' if help_text else ""
    return (f'          <div class="field" data-field="{key}">\n'
            f'            <label class="field__label" for="{fid}">{label}{star}</label>\n'
            f'            <div class="{box_cls}">{control}{states}</div>{help_html}\n'
            f'            <p class="field__error" id="{fid}-err" hidden></p>\n'
            f'          </div>')


def _consent(form):
    fid = f"{form}-einwilligung"
    return (f'          <div class="field" data-field="einwilligung">\n'
            f'            <label class="consent" for="{fid}"><input id="{fid}" name="einwilligung" type="checkbox" value="ja" required '
            f'aria-describedby="{fid}-err" data-msg="{escape(MSG["einwilligung"])}"><span class="consent__box">{icon("check")}</span>'
            f'<span class="consent__text"><!-- TEXTVORSCHLAG: vom Kunden freigeben -->{CONSENT}</span></label>\n'
            f'            <p class="field__error sr-only" id="{fid}-err" hidden></p>\n'
            f'          </div>')


def _form(name, title, fields, note, button, extra_cls="", sub="", noicon=False):
    hidden = (f'          <input type="hidden" name="form" value="{name}">\n'
              '          <input type="hidden" name="t" value="">\n'
              '          <div class="hp" aria-hidden="true"><label>Website (bitte leer lassen)<input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>')
    title_html = f'          <h2 class="form__title" id="{name}-title">{title}</h2>\n' if title else ""
    if sub:
        title_html += f'          <p class="form__sub">{sub}</p>\n'
    labelled = f' aria-labelledby="{name}-title"' if title else ""
    msgs = escape(json.dumps({k: MSG[k] for k in ("summary", "network", "rate", "ok", "required")}, ensure_ascii=False))
    return (f'<form class="form{extra_cls}" action="/kontakt.php" method="post" data-form="{name}" data-msgs="{msgs}" novalidate{labelled}>\n'
            f'{title_html}'
            f'          <div class="errsum" role="alert" tabindex="-1" hidden>{icon("alert", "i i--20 errsum__icon")}'
            f'<div><p class="errsum__title">{MSG["summary"]}</p><p class="errsum__text"></p></div></div>\n'
            f'{hidden}\n'
            + "\n".join(fields)
            + (f'\n          <p class="form__note">{"" if noicon else "<!-- TEXTVORSCHLAG: vom Kunden freigeben -->"}{note}</p>' if note else "")
            + f'\n          <div class="form__actions"><button class="btn btn--primary" type="submit">'
            f'<span class="btn__label">{button}</span>{"" if noicon else icon("arrow-right")}</button></div>\n'
            '          <p class="form__status" role="status" aria-live="polite"></p>\n        </form>')


def widerruf_done_html():
    """Bestätigung nach dem Widerruf (spec D-05): mit JS im selben Bereich, ohne JS als Serverseite (server/templates)."""
    return f'''<div class="done" id="widerruf-done" tabindex="-1" role="status" hidden>
            <!-- TEXTVORSCHLAG: vom Kunden freigeben (Bestätigung Widerruf, D-05) -->
            <span class="badge" aria-hidden="true">{icon("check")}</span>
            <h2 class="h3">Widerruf eingegangen</h2>
            <p data-mailed>Vielen Dank. Ihr Widerruf ist bei uns eingegangen. Eine Eingangsbestätigung wurde an die angegebene E-Mail-Adresse gesendet.</p>
            <p data-nomail hidden>Vielen Dank. Ihr Widerruf ist bei uns eingegangen. Die Eingangsbestätigung per E-Mail konnte jedoch nicht versendet werden – bitte rufen Sie uns zur Bestätigung an.</p>
            <p class="small muted">Fragen? Telefon <a class="inline" href="{PHONE_HREF}">{PHONE}</a></p>
          </div>'''


def form_html(name):
    if name == "kontakt":
        return _form("kontakt", "Kontaktformular", [
            _field("kontakt", "name", "Name", required=True, autocomplete="name", maxlength=100, placeholder="Ihr Name"),
            _field("kontakt", "email", "E-Mail", "email", required=True, autocomplete="email", maxlength=200,
                   placeholder="name@beispiel.de", msg=MSG["email"]),
            '          <div class="form__row form__row--2">\n'
            + _field("kontakt", "telefon", "Telefon (optional)", "tel", autocomplete="tel", maxlength=40,
                     placeholder="Für Rückfragen", msg=MSG["telefon"]) + "\n"
            + _field("kontakt", "leistung", "Leistung (optional)", options=SERVICES) + "\n          </div>",
            _field("kontakt", "nachricht", "Nachricht", required=True, rows=4, maxlength=5000,
                   placeholder="Worum geht es? Fläche, Material, Ort, Wunschtermin …", msg=MSG["nachricht"]),
            _consent("kontakt"),
        ], PRIVACY_NOTE, "Anfrage senden", sub="Pflichtfelder sind mit * markiert.")
    if name == "kurz":
        return _form("kurz", "Kurzanfrage", [
            _field("kurz", "name", "Name", required=True, autocomplete="name", maxlength=100, placeholder="Ihr Name"),
            _field("kurz", "telefon", "Telefon", "tel", required=True, autocomplete="tel", maxlength=40,
                   placeholder="Ihre Telefonnummer", msg=MSG["telefon"]),
            _field("kurz", "nachricht", "Anliegen", required=True, rows=4, maxlength=5000,
                   placeholder="Worum geht es? Fläche, Material, Ort …", msg=MSG["nachricht"]),
            _consent("kurz"),
        ], PRIVACY_NOTE, "Anfrage senden")
    if name == "widerruf":
        note = ('<span class="form__warn">' + icon("alert", "i i--20 i--y") + '<span>Ein Klick auf die Schaltfläche unten erklärt verbindlich '
                'den Widerruf des oben angegebenen Vertrags. Dieser Schritt kann nicht rückgängig gemacht werden. '
                'Alle mit * markierten Felder sind Pflichtfelder.</span></span>')
        return _form("widerruf", "Widerrufserklärung", [
            _field("widerruf", "name", "Name", required=True, autocomplete="name", maxlength=100, placeholder="Ihr Name"),
            _field("widerruf", "bestellnummer", "Bestell- oder Buchungsnummer", required=True, maxlength=100,
                   placeholder="z. B. aus der Bestellbestätigung", help_text="Dies ist in der Bestellbestätigung zu finden."),
            _field("widerruf", "email", "E-Mail-Adresse", "email", required=True, autocomplete="email", maxlength=200,
                   placeholder="name@beispiel.de", help_text="Die Eingangsbestätigung wird an diese Adresse gesendet.", msg=MSG["email"]),
            _field("widerruf", "artikel", "Welche Artikel sollen widerrufen werden?", rows=4, maxlength=300,
                   placeholder="Artikel angeben (optional)",
                   help_text="Leer lassen, um den gesamten Vertrag zu widerrufen. Um nur einen Teil der Bestellung zu widerrufen, die Artikel hier angeben."),
            _field("widerruf", "nachricht", "Grund des Widerrufs (optional)", rows=4, maxlength=5000, placeholder="Optional"),
        ], note, "Widerruf erklären", noicon=True)
    raise KeyError(name)


# ---- Brotkrumen, Inhaltsverzeichnis, strukturierte Daten -----------------------------------------------
def crumb_trail(url):
    trail = []
    while url in CRUMBS:
        label, parent = CRUMBS[url]
        trail.append((label, url))
        url = parent
    trail.append(("Start", "/"))
    return list(reversed(trail))


def crumbs_html(url):
    trail = crumb_trail(url)
    items = "".join(f'<li><a href="{u}">{escape(l)}</a></li>' for l, u in trail[:-1])
    items += f'<li><span aria-current="page">{escape(trail[-1][0])}</span></li>'
    return f'<nav class="crumbs" aria-label="Brotkrumen"><ol>{items}</ol></nav>'


def breadcrumb_jsonld(url):
    trail = crumb_trail(url)
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": l, "item": SITE + u} for i, (l, u) in enumerate(trail)]}


def business_jsonld():
    # Nur Felder aus CONTENT.md; kein geo, keine Öffnungszeiten
    return {"@context": "https://schema.org", "@type": "HomeAndConstructionBusiness",
            "name": "Wahl Straßenbau GmbH & Co. KG", "url": SITE + "/", "image": SITE + "/assets/og/home.jpg",
            "telephone": "+49 381 25 22 39 41", "faxNumber": "+49 381 375 667 60", "email": "info@wahl-strassenbau.de",
            "vatID": "DE294970751", "foundingDate": "2005",
            "founder": {"@type": "Person", "name": "Robert Wahl", "jobTitle": "Straßenbaumeister"},
            "address": {"@type": "PostalAddress", "streetAddress": "Ringstraße 25", "postalCode": "18059",
                        "addressLocality": "Papendorf", "addressCountry": "DE"}}


def slugify(text):
    text = re.sub(r"<[^>]+>", "", text).lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("§", "paragraph")):
        text = text.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:60] or "abschnitt"


def add_toc(body):
    """Ids für die h2 der Rechtstexte setzen und Inhaltsverzeichnis erzeugen:
    Desktop: Sticky-Spalte 300 px (TOC item 7:635), Tablet/Mobil: aufklappbare Liste (Legal contents mobile 7:660)."""
    entries, used = [], set()

    def tag(m):
        attrs, inner = m.group(1) or "", re.sub(r"\s+", " ", m.group(2)).strip()
        text = re.sub(r"<[^>]+>", "", inner)
        slug = re.search(r'id="([^"]+)"', attrs)
        slug = slug.group(1) if slug else slugify(text)
        base, n = slug, 2
        while slug in used:
            slug, n = f"{base}-{n}", n + 1
        used.add(slug)
        entries.append((slug, text))
        attrs = re.sub(r'\s*id="[^"]*"', "", attrs)
        return f'<h2 id="{slug}"{attrs}>{inner}</h2>'

    body = re.sub(r"<h2((?:\s[^>]*)?)>(.*?)</h2>", tag, body, flags=re.S)
    lis = "".join(f'<li><a href="#{s}">{escape(t, quote=False)}</a></li>' for s, t in entries)
    n = len(entries)
    side = (f'<nav class="toc" aria-label="Inhaltsverzeichnis"><p class="toc__title eyebrow">Inhalt</p><ol>{lis}</ol></nav>')
    fold = (f'<details class="tocm" open><summary><span class="label yellow">Inhalt</span> <span class="muted small">{n} Abschnitte</span>'
            f'{icon("chevron-down", "i i--20 tocm__chev")}</summary><nav aria-label="Inhaltsverzeichnis (mobil)"><ol>{lis}</ol></nav></details>')
    return body.replace("{{toc}}", side).replace("{{toc-mobile}}", fold).replace("{{toc-count}}", str(n))


# ---- Vorschaubilder für soziale Netzwerke (1200×630, Farben aus Figma) -------------------------------
def anton_ttf():
    ttf = ROOT / "_refs" / "work" / "anton.ttf"
    if not ttf.exists():
        from fontTools.ttLib import TTFont
        ttf.parent.mkdir(parents=True, exist_ok=True)
        f = TTFont(ROOT / "fonts" / "anton-latin.woff2")
        f.flavor = None
        f.save(ttf)
    return ttf


OG_VERSION = "figma-2026-1"


def make_og(url, title):
    """1200x630: Foto der Seite, abgedunkelt (Charcoal), Titel in Anton, gelbe Linie. Rückgabe: URL des Bildes."""
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    slug = "home" if url == "/" else url.strip("/").replace("/", "-").replace(".html", "")
    out = ROOT / "assets" / "og" / f"{slug}.jpg"
    stamp = ROOT / "_refs" / "work" / "og" / f"{slug}.txt"
    photo = PHOTOS / f"{OG_PHOTO.get(url, OG_DEFAULT_PHOTO)}.webp"
    key = f"{OG_VERSION}|{photo.name}|{title}"
    if photo.exists() and (not out.exists() or not stamp.exists() or stamp.read_text() != key):
        out.parent.mkdir(parents=True, exist_ok=True)
        W, H = 1200, 630
        img = ImageOps.fit(Image.open(photo).convert("RGB"), (W, H), Image.LANCZOS, centering=(0.5, 0.55)).convert("RGBA")
        shade = Image.new("RGBA", (W, H))
        d = ImageDraw.Draw(shade)
        for y in range(H):
            d.line([(0, y), (W, y)], fill=(16, 17, 17, int(120 + 110 * y / H)))
        img = Image.alpha_composite(img, shade)
        d = ImageDraw.Draw(img)
        ttf = str(anton_ttf())
        text = title.upper().replace("ß", "SS")
        size = 104
        while size > 48:
            font = ImageFont.truetype(ttf, size)
            words, lines, cur = text.split(), [], ""
            for w_ in words:
                trial = (cur + " " + w_).strip()
                if d.textlength(trial, font=font) <= W - 128:
                    cur = trial
                else:
                    lines.append(cur)
                    cur = w_
            lines.append(cur)
            if len(lines) <= 3:
                break
            size -= 6
        lh = int(size * 1.02)
        y0 = H - 96 - lh * len(lines)
        d.rectangle([64, y0 - 40, 64 + 48, y0 - 37], fill=(244, 196, 49))
        for i, line in enumerate(lines):
            d.text((64, y0 + i * lh), line, font=font, fill=(245, 243, 238))
        small = ImageFont.truetype(ttf, 30)
        d.text((64, 56), "WAHL STRASSENBAU · PAPENDORF BEI ROSTOCK", font=small, fill=(244, 196, 49))
        logo = ROOT / "assets" / "img" / "logo-mark.png"
        if logo.exists():
            lg = Image.open(logo).convert("RGBA").resize((84, 84), Image.LANCZOS)
            img.alpha_composite(lg, (W - 64 - 84, 48))
        img.convert("RGB").save(out, quality=86, optimize=True)
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.write_text(key)
    return f"/assets/og/{slug}.jpg" if out.exists() else "/assets/og/home.jpg"


# ---- Technik (Daten aus CONTENT.md; Summen werden berechnet) --------------------------------------------
TECH = [
    ("Transport", "truck", [
        (1, "LKW 7,5 t"), (1, "Tandem-Dreiseitenkipper 10,5 t"), (1, "Transportmulde Mammut bis 10,5 t"),
        (5, "Mercedes Vito, inkl. kompletter Arbeitsausrüstung"), (2, "Mercedes Sprinter, inkl. kompletter Arbeitsausrüstung"),
        (2, "Tandemanhänger 2,5 t"), (2, "Tandemanhänger 3,0 t")]),
    ("Erdbau", "shovel", [
        (1, "Radlader 0,8 m³"), (2, "Minibagger bis 2,0 t"), (1, "Midibagger Hitachi 5,0 t"),
        (1, "Midibagger Sany bis 6,5 t"), (1, "Erdfräse")]),
    ("Verdichtung &amp; Asphalt", "layers", [
        (3, "Rüttelplatten à 500 kg"), (4, "Rüttelplatten à 200 kg"), (3, "Vibrationsstampfer"),
        (1, "Asphaltwalze"), (5, "Motorflex"), (1, "Abziehhobel bis 7,5 m Abziehbreite")]),
]


def tech_total():
    return sum(n for _, _, items in TECH for n, _ in items)


def tech_count(key):
    return sum(n for _, _, items in TECH for n, t in items if key in t)


def tech_value(key):
    """Kennzahlen der Technik-Seite (Figma 11:1000): Einheiten gesamt, Positionen, Bereiche, Fahrzeuge/Anhänger."""
    if key == "total":
        return tech_total()
    if key == "positions":
        return sum(len(items) for _, _, items in TECH)
    if key == "groups":
        return len(TECH)
    if key in ("transport", "erdbau", "verdichtung"):
        idx = {"transport": 0, "erdbau": 1, "verdichtung": 2}[key]
        return sum(n for n, _ in TECH[idx][2])
    return tech_count(key)


def tech_groups_html():
    """Technik nach Einsatzbereich (Figma 11:1022): Gruppe mit Icon, Einheiten, Titel und Equipment rows (7:678)."""
    cols = []
    for name, ic, items in TECH:
        total = sum(n for n, _ in items)
        lis = "".join(f'<li><span class="equip__n">{n}</span><span>{t}</span></li>' for n, t in items)
        cols.append(f'<li class="techgrp"><p class="techgrp__head eyebrow">{icon(ic, "i techgrp__icon")}{total} Einheiten</p>'
                    f'<h3>{name}</h3><ul class="equip">{lis}</ul></li>')
    return f'<ul class="techgrps" data-stagger>{"".join(cols)}</ul>'


# ---- Makros ------------------------------------------------------------------------------------------
def band_html(heading_level=2):
    """Emergency band (Figma 7:478). Texte aus CONTENT.md (Havariebehebung)."""
    h = f"h{heading_level}"
    return f'''<section class="band" id="havarie" aria-labelledby="band-title">
      <div class="wrap band__grid">
        <div class="band__text">
          <p class="eyebrow band__eyebrow">{icon("clock")}24/7 · Havarie</p>
          <{h} class="h2" id="band-title">24-Stunden-Komplettservice bei Havarien</{h}>
          <p class="band__lead">Baustellensicherung, Erdbau, Pflasterung, Grünflächenwiederherstellung und Baustellenberäumung aus einer Hand.</p>
        </div>
        <div class="band__call">
          <!-- TEXTVORSCHLAG: vom Kunden freigeben («Havarie-Hotline») -->
          <p class="band__label">Havarie-Hotline</p>
          <a class="band__num" href="{PHONE_HREF}">{PHONE}</a>
          <a class="btn btn--emergency" href="{PHONE_HREF}">{icon("phone")}Jetzt anrufen</a>
        </div>
      </div>
    </section>'''


def gallery_html(spec):
    """Gallery tiles (Figma 7:628, 4:3) mit Lightbox. spec: 'name/pos/zoom~Kategorie~Titel ;; …'"""
    tiles = []
    for item in spec.split(";;"):
        img, cat, title = [x.strip() for x in item.split("~")]
        name, *rest = img.split("/")
        pos = rest[0] if rest else ""
        zoom = rest[1] if len(rest) > 1 else ""
        tiles.append(f'<li><a class="tile" href="/assets/photos/{name}.webp" data-lightbox data-alt="{escape(ALT[name])}">'
                     f'{photo_tag(name, None, "(max-width: 767px) 100vw, 50vw", "", False, pos, False, zoom)}'
                     f'<span class="tile__cap"><span class="eyebrow">{cat}</span><b>{title}</b></span>'
                     f'<span class="tile__zoom">{icon("image", "i i--20")}<span class="sr-only">Foto vergrößern</span></span></a></li>')
    return '<ul class="gallery" data-gallery data-stagger>' + "".join(tiles) + "</ul>"


def compare_html(args):
    """Vorher/Nachher-Slider (Figma 36:145): oben links «Fertig», darunter rechts «Während der Verlegung»."""
    top, under = "wappen-gruen", "wappen-bau"
    sizes = "(max-width: 1279px) 100vw, 864px"
    return (f'<div class="compare" data-compare>'
            f'<div class="compare__layer compare__layer--under">{photo_tag(under, None, sizes, "", False, "50% 50%", False, "1.24")}'
            f'<span class="compare__tag">Während der Verlegung</span></div>'
            f'<div class="compare__layer compare__layer--top">{photo_tag(top, None, sizes)}<span class="compare__tag">Fertig</span></div>'
            f'<span class="compare__line" aria-hidden="true"></span><span class="compare__knob" aria-hidden="true">{icon("arrow-left", "i i--16")}{icon("arrow-right", "i i--16")}</span>'
            f'<input type="range" min="0" max="100" value="50" step="1" aria-label="Vergleich: Wappenmosaik fertig und während der Verlegung"></div>')


CTA_ALT = {
    "phone": lambda: f'<a class="btn btn--phone" href="{PHONE_HREF}">{icon("phone")}{PHONE}</a>',
    "leistungen": lambda: f'<a class="btn btn--link btn--l" href="/leistungsangebot/">Alle Leistungen{icon("arrow-right", "i i--y")}</a>',
    "referenzen": lambda: f'<a class="btn btn--link btn--l" href="/referenzen/">Alle Referenzen{icon("arrow-right", "i i--y")}</a>',
}


def cta_html(args=""):
    """CTA band (Figma «CTA band», z. B. 10:571): Eyebrow, Titel, Text, Primary + zweite Aktion.
    Makro: {{cta}} oder {{cta|title=…|text=…|eyebrow=…|alt=phone|leistungen|referenzen}}"""
    o = {"title": "Projekt geplant?", "text": "Schreiben Sie uns kurz, worum es geht, oder rufen Sie direkt an.",
         "eyebrow": "Nächster Schritt", "alt": "phone"}
    for part in args.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            o[k.strip()] = v.strip()
    return f'''<section class="ctaband" aria-labelledby="cta-title">
      <div class="wrap ctaband__row">
        <div class="ctaband__text">
          <!-- TEXTVORSCHLAG: vom Kunden freigeben («{o["eyebrow"]}», «{o["title"]}») -->
          <p class="eyebrow">{o["eyebrow"]}</p>
          <h2 id="cta-title">{o["title"]}</h2>
          <p>{o["text"]}</p>
        </div>
        <div class="ctaband__actions">
          <a class="btn btn--primary" href="/kontakt/">Angebot anfragen{icon("arrow-right")}</a>
          {CTA_ALT[o["alt"]]()}
        </div>
      </div>
    </section>'''


def expand_macros(body, url):
    body = re.sub(r"\{\{form:(\w+)\}\}", lambda m: form_html(m.group(1)), body)
    body = re.sub(r"\{\{photo:([\w-]+)((?:\|[^}]*)?)\}\}", photo_macro, body)
    body = re.sub(r"\{\{icon:([\w-]+)(?:\|([^}]*))?\}\}", lambda m: icon(m.group(1), m.group(2) or "i"), body)
    body = re.sub(r"\{\{tech:(\w+)\}\}", lambda m: str(tech_value(m.group(1))), body)
    body = body.replace("{{tech-groups}}", tech_groups_html())
    body = re.sub(r"\{\{gallery:([^}]*)\}\}", lambda m: gallery_html(m.group(1)), body)
    body = re.sub(r"\{\{compare(:[^}]*)?\}\}", lambda m: compare_html(m.group(1)), body)
    body = re.sub(r"\{\{cta((?:\|[^}]*)?)\}\}", lambda m: cta_html(m.group(1)), body)
    body = body.replace("{{widerruf-done}}", widerruf_done_html())
    body = body.replace("{{band}}", band_html()).replace("{{crumbs}}", crumbs_html(url))
    body = body.replace("{{years}}", str(years_since(2005, 5))).replace("{{maps}}", MAPS)
    body = body.replace("{{phone}}", PHONE).replace("{{phone_href}}", PHONE_HREF)
    return body


def parse(text):
    head, _, body = text.partition("\n---\n")
    meta = {}
    for line in head.splitlines():
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip()
    return meta, body.strip("\n")


def out_path(url):
    if url.endswith(".html"):
        return ROOT / url.lstrip("/")
    return ROOT / url.strip("/") / "index.html" if url != "/" else ROOT / "index.html"


def page_title_text(body, meta):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", body, flags=re.S)
    text = meta.get("og_title") or (m.group(1) if m else meta.get("title", ""))
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text.replace("&nbsp;", " ").replace("&amp;", "&")).strip()


TOTOP = ('  <a class="totop{cls}" href="#top" aria-label="Nach oben" data-totop>' + icon("arrow-up") + '</a>\n')


STRICT_ERRORS = []


def main():
    noindex_urls = {"/404.html", "/kontakt/danke/"}
    layout = (SRC / "layout.html").read_text(encoding="utf8")
    year = str(TODAY.year)
    for url, name, nav in PAGES:
        _current_url[0] = url
        _preload.clear()
        meta, body = parse((SRC / "pages" / f"{name}.html").read_text(encoding="utf8"))
        body = expand_macros(body, url)
        if meta.get("toc") == "yes":
            body = add_toc(body)
        html = layout
        area = NAV_AREA.get(nav, "")
        cur = ' aria-current="page"'
        for key in ("leistungen", "technik", "referenzen", "kontakt"):
            # Kopfzeile: aktueller Bereich; aria-current="page" nur auf der Seite selbst, sonst "true"
            html = html.replace("{{cur_%s}}" % key, "" if area != key else (cur if nav == key else ' aria-current="true"'))
        for key, navkey in (("start", "start"), ("leistungen_exact", "leistungen"), ("pflaster", "pflaster"), ("garten", "garten")):
            html = html.replace("{{cur_%s}}" % key, cur if nav == navkey else "")
        for k in ("title", "description", "class"):
            html = html.replace("{{%s}}" % k, meta.get(k, ""))
        noindex = url in noindex_urls or meta.get("robots") == "noindex"
        canonical = '<meta name="robots" content="noindex">' if noindex else f'<link rel="canonical" href="{SITE}{url}">'
        ld = []
        if url == "/":
            ld.append(business_jsonld())
        elif url in CRUMBS and not noindex:
            ld.append(breadcrumb_jsonld(url))
        jsonld = "".join(f'<script type="application/ld+json">{json.dumps(o, ensure_ascii=False)}</script>\n  ' for o in ld)
        og = SITE + make_og(url, page_title_text(body, meta))
        totop = meta.get("totop", "")
        totop_html = TOTOP.replace("{cls}", " totop--mt" if totop == "mt" else "") if totop else ""
        html = (html.replace("{{canonical}}", canonical).replace("{{jsonld}}", jsonld).replace("{{site}}", SITE)
                .replace("{{og_image}}", og).replace("{{og_url}}", SITE + url).replace("{{year}}", year)
                .replace("{{preload}}", "\n  ".join(_preload)).replace("{{totop}}", totop_html)
                .replace("{{maps}}", MAPS).replace("{{body}}", body))
        html = re.sub(r"\{\{icon:([\w-]+)(?:\|([^}]*))?\}\}", lambda m: icon(m.group(1), m.group(2) or "i"), html)
        html = add_dimensions(html)
        if "{{" in html:
            print(f"WARNUNG: unbekanntes Makro in {name}: " + re.search(r"\{\{[^}]*\}\}", html).group(0))
            STRICT_ERRORS.append(name)
        dest = out_path(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf8")
        print("gebaut:", dest.relative_to(ROOT))

    # Vorlagen für die Server-Antworten ohne JavaScript (server/lib/Page.php): gleiche Kopf-/Fußzeile und Formular-Markup
    tpl = ROOT / "server" / "templates"
    tpl.mkdir(parents=True, exist_ok=True)
    base = layout
    for key in ("leistungen", "technik", "referenzen", "kontakt", "start", "leistungen_exact", "pflaster", "garten"):
        base = base.replace("{{cur_%s}}" % key, "")
    base = (base.replace("{{title}}", "{{page_title}}").replace("{{description}}", "")
            .replace("{{class}}", "page-server").replace("{{canonical}}", '<meta name="robots" content="noindex">')
            .replace("{{jsonld}}", "").replace("{{og_image}}", SITE + "/assets/og/home.jpg").replace("{{og_url}}", SITE + "/")
            .replace("{{year}}", year).replace("{{preload}}", "").replace("{{totop}}", "").replace("{{maps}}", MAPS)
            .replace("{{body}}", "{{page_body}}"))
    base = re.sub(r"\{\{icon:([\w-]+)(?:\|([^}]*))?\}\}", lambda m: icon(m.group(1), m.group(2) or "i"), base)
    (tpl / "layout.html").write_text(base, encoding="utf8")
    for f in ("kontakt", "kurz", "widerruf"):
        (tpl / f"form-{f}.html").write_text(form_html(f), encoding="utf8")
    (tpl / "widerruf-done.html").write_text(widerruf_done_html(), encoding="utf8")

    # sitemap.xml und robots.txt
    urls = "\n".join(f"  <url><loc>{SITE}{u}</loc></url>" for u, _, _ in PAGES if u not in noindex_urls)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n' % urls,
        encoding="utf8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n", encoding="utf8")
    (ROOT / "_refs" / "work").mkdir(parents=True, exist_ok=True)
    (ROOT / "_refs" / "work" / "photo-usage.json").write_text(json.dumps(USED_PHOTOS, ensure_ascii=False, indent=1))
    print("gebaut: sitemap.xml, robots.txt")
    if STRICT_ERRORS:
        raise SystemExit(f"Build mit Fehlern: {', '.join(STRICT_ERRORS)}")


if __name__ == "__main__":
    main()
