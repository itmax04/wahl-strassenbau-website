"""WEB-2026 P-00: Prototyp-Routen aus Figma-Metadaten extrahieren.

Eingabe: _refs/figma/meta-{desktop,tablet,mobile}.xml (get_metadata von 1:3, 1:4, 1:5).
Ausgabe: _refs/figma/routes.json — Liste {device, frame_id, frame, layer_id, layer, target}.
Ein Layer mit Route hat den Namen «… → Ziel» (Konvention aus dem Figma-Handoff).
"""
import json, re, sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / '_refs' / 'figma'


def load(device):
    raw = (FIG / f'meta-{device}.xml').read_text()
    raw = raw[:raw.rindex('</canvas>') + len('</canvas>')]
    return ET.fromstring(raw)


def main():
    routes = []
    for device in ('desktop', 'tablet', 'mobile'):
        canvas = load(device)
        for frame in canvas:
            for el in frame.iter():
                name = el.get('name', '')
                if '→' not in name or el is frame:
                    continue
                layer, target = name.rsplit('→', 1)
                routes.append({'device': device, 'frame_id': frame.get('id'), 'frame': frame.get('name'),
                               'layer_id': el.get('id'), 'layer': layer.strip(), 'target': target.strip()})
    (FIG / 'routes.json').write_text(json.dumps(routes, ensure_ascii=False, indent=1))
    targets = sorted({r['target'] for r in routes})
    print(f'{len(routes)} Routen, {len(targets)} Ziele: {", ".join(targets)}')


if __name__ == '__main__':
    sys.exit(main())
