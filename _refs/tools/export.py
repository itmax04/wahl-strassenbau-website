"""Шаг 4: коррекция + экспорт. Из _refs/work/up (если есть апскейл) или _refs/work/crops -> assets/photos/*.{webp,avif}.
Размеры: 640, 1280 (если хватает ширины) и полный (не шире 2560). WebP: cwebp -q 82. AVIF: avifenc -q 60."""
import subprocess, sys, pathlib, tempfile, shutil
from PIL import Image
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from grade import grade
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/photos'
OUT.mkdir(parents=True, exist_ok=True)
NAMES = ['weg', 'tritt', 'rundplatz', 'ornament', 'rosette', 'medaillon', 'wappen-bau', 'logo-hammer', 'stiere-bau',
         'stern-beet', 'stier-ziegel', 'wappen-gruen', 'logo-mosaik', 'team-2020', 'segmentbogen']
only = sys.argv[1:] or NAMES
MAXW = 2560

def encode(img, dst_base):
    with tempfile.TemporaryDirectory() as td:
        png = pathlib.Path(td) / 'x.png'
        img.save(png)
        subprocess.run(['cwebp', '-quiet', '-q', '82', '-m', '6', str(png), '-o', f'{dst_base}.webp'], check=True)
        subprocess.run(['avifenc', '-q', '60', '-s', '6', '-j', '4', str(png), f'{dst_base}.avif'], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for name in only:
    up = ROOT / f'_refs/work/up/{name}.png'
    src = up if up.exists() else ROOT / f'_refs/work/crops/{name}.png'
    im = grade(Image.open(src))
    if im.width > MAXW:
        im = im.resize((MAXW, round(im.height * MAXW / im.width)), Image.LANCZOS)
    for old in OUT.glob(f'{name}*'):
        if old.stem == name or old.stem.startswith(name + '-') and old.stem.split('-')[-1].isdigit():
            old.unlink()
    for w in (640, 1280):
        if w < im.width - 120:
            encode(im.resize((w, round(im.height * w / im.width)), Image.LANCZOS), OUT / f'{name}-{w}')
    encode(im, OUT / name)
    print(f'{name:14s} {"апскейл" if up.exists() else "черновик"}  {im.size}  {(OUT / (name + ".webp")).stat().st_size // 1024} KB')
