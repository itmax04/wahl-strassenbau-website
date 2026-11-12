"""WEB-2026 AC-09: Rechtstexte wortgleich zu master@1ebca29 prüfen.

Aufruf: python3 _refs/tools/legal_textcheck.py   (nach python3 build.py)

Verglichen wird der Text (ohne Tags, Leerraum normalisiert) von
  master: <h1> + <article class="prose"> aus `git show master:src/pages/<datei>.html`
  neu:    <h1> + [data-legal-lead] + [data-legal] der gebauten Seite, ohne Elemente mit [data-legal-extra]
            (zusätzliche Überschriften, Inhaltsverzeichnis, Kontaktbox — erlaubt laut spec R-08.3).
Erwartung: keine Wortabweichung (weder fehlend noch hinzugefügt). Wiederholungen ganzer Sätze (z. B. Lead + Infokachel) sind erlaubt,
wenn der Satz im Original vorkommt.
Zusätzlich: Demo-Werte aus Generativ-Referenzen («Anna Beispiel», «25+», «100+») dürfen nirgends im Build vorkommen.
"""
import difflib
import html
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = {"impressum": "about/index.html", "datenschutz": "j/privacy/index.html",
         "gewaehrleistung": "j/legal-guarantee/index.html", "widerruf": "j/withdrawal/index.html"}
VOID = {"br", "img", "input", "meta", "link", "hr", "source", "wbr"}


def norm(text):
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([:;,.!?)])", r"\1", text)
    text = re.sub(r"([:])(?=\S)", r"\1 ", text)  # «Sitz:Rostock» (dt/dd) == «Sitz: Rostock»
    text = re.sub(r"\(\s+", "(", text)
    return text


class Extract(HTMLParser):
    """Sammelt Text innerhalb von Elementen, deren Start-Tag `want(attrs, tag)` erfüllt; überspringt `skip`-Elemente."""

    def __init__(self, want, skip):
        super().__init__(convert_charrefs=True)
        self.want, self.skip = want, skip
        self.stack, self.out = [], []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            if self.active():
                self.out.append(" ")
            return
        a = dict(attrs)
        self.stack.append((tag, self.want(tag, a), self.skip(tag, a)))
        if self.active():
            self.out.append(" ")

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        while self.stack:
            t, _, _ = self.stack.pop()
            if t == tag:
                break
        self.out.append(" ")

    def active(self):
        return any(w for _, w, _ in self.stack) and not any(s for _, _, s in self.stack)

    def handle_data(self, data):
        if self.active():
            self.out.append(data)

    def handle_comment(self, data):
        pass


def text_of(doc, want, skip=lambda t, a: False):
    p = Extract(want, skip)
    p.feed(doc)
    return norm("".join(p.out))


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?:])\s+", text) if s]


def main():
    ok = True
    for name, built in PAGES.items():
        master = subprocess.run(["git", "show", f"master:src/pages/{name}.html"], cwd=ROOT, capture_output=True, text=True).stdout
        master_body = master.split("\n---\n", 1)[1]
        m_text = text_of(master_body, lambda t, a: t == "h1" or (t == "article" and "prose" in a.get("class", "")))
        new_doc = (ROOT / built).read_text(encoding="utf8")
        n_text = text_of(new_doc, lambda t, a: t == "h1" or "data-legal" in a or "data-legal-lead" in a,
                         lambda t, a: "data-legal-extra" in a or "sr-only" in a.get("class", "") and ":" not in "")
        # sr-only-Doppelpunkte im Impressum sind Teil des Originaltextes: erneut ohne sr-only-Ausnahme lesen
        n_text = text_of(new_doc, lambda t, a: t == "h1" or "data-legal" in a or "data-legal-lead" in a,
                         lambda t, a: "data-legal-extra" in a)
        # Wiederholte Originalsätze entfernen (Lead + Infokachel), Reihenfolge der ersten Vorkommen behalten
        seen, dedup = set(), []
        for s in sentences(n_text):
            if s in seen and len(s) > 40 and s in m_text:
                continue
            seen.add(s)
            dedup.append(s)
        n_words, m_words = " ".join(dedup).split(), m_text.split()
        sm = difflib.SequenceMatcher(a=m_words, b=n_words, autojunk=False)
        diffs = [(op, " ".join(m_words[i1:i2]), " ".join(n_words[j1:j2])) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
        status = "PASS" if not diffs else "FAIL"
        ok &= not diffs
        print(f"{status} {name}: {len(m_words)} Wörter im Original, {len(n_words)} auf der Seite, {len(diffs)} Abweichungen")
        for op, a, b in diffs[:20]:
            print(f"   {op}: master «{a[:120]}» → neu «{b[:120]}»")

    bad = []
    for p in list(ROOT.glob("**/*.html")) + list((ROOT / "src").glob("**/*.html")):
        if any(part in p.parts for part in ("_refs", "node_modules", ".git", "docs")):
            continue
        t = p.read_text(encoding="utf8", errors="ignore")
        for needle in ("Anna Beispiel", "anna@beispiel", "25+", "100+"):
            if needle in t:
                bad.append(f"{p.relative_to(ROOT)}: {needle}")
    print(("FAIL" if bad else "PASS") + f" Demo-Werte: {len(bad)} Treffer")
    for b in bad:
        print("   " + b)
    return 0 if ok and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
