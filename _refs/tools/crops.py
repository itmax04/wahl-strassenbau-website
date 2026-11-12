"""Шаг 1: убрать рамки, пересвет, мусор по краям. Оригиналы не трогаем."""
from PIL import Image
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / '_refs/originals/jimdo'
OUT = ROOT / '_refs/work/crops'

# имя: (файл, (x0, y0, x1, y1), причина)
CROPS = {
    'weg':          ('garten-01',   (6, 6, 1081, 847),   'рамка 4 px'),
    'tritt':        ('garten-02',   (6, 6, 1081, 527),   'рамка 4 px'),
    'rundplatz':    ('garten-03',   (0, 185, 1024, 768), 'пересвеченное небо сверху'),
    'ornament':     ('garten-04',   (0, 205, 1024, 665), 'блики светильника и белые доски'),
    'rosette':      ('garten-05',   (0, 0, 567, 378),    'без обрезки'),
    'medaillon':    ('pflaster-02', (0, 120, 1024, 520), 'пол и баннеры'),
    'wappen-bau':   ('pflaster-03', (0, 140, 1024, 600), 'машины сверху, песок снизу'),
    'logo-hammer':  ('pflaster-04', (0, 185, 576, 585),  'чёрная плёнка и доски'),
    'stiere-bau':   ('pflaster-05', (0, 310, 1024, 730), 'забор и чужая вывеска'),
    'stern-beet':   ('pflaster-06', (0, 290, 576, 560),  'фасад, вёдра, инструмент'),
    'stier-ziegel': ('pflaster-07', (30, 195, 1010, 665), 'выставочный хлам'),
    'wappen-gruen': ('pflaster-08', (0, 240, 1280, 960), 'небо и верх крон'),
    'logo-mosaik':  ('referenz-06', (10, 240, 1015, 650), 'склад материалов сверху'),
    'team-2020':    ('home-2',      (0, 380, 4808, 2488), 'пересвеченное небо'),
    'segmentbogen': ('hintergrund', (5, 5, 1425, 1495),  'рамка 3 px'),
}
if __name__ == '__main__':
    info = {}
    for name, (f, box, why) in CROPS.items():
        im = Image.open(SRC / f'{f}.jpg').convert('RGB')
        c = im.crop(box)
        c.save(OUT / f'{name}.png')
        info[name] = {'src': f, 'box': box, 'size': c.size, 'why': why}
        print(f'{name:14s} {im.size} -> {c.size}  ({why})')
    (ROOT / '_refs/work/crops.json').write_text(json.dumps(info, ensure_ascii=False, indent=1))
