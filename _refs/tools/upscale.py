"""Шаг 2: AI-апскейл ×2 (EDSR, OpenCV dnn_superres) по тайлам. Запуск: python upscale.py имя [имя ...]
Интерпретатор: venv с opencv-contrib-python-headless (см. отчёт)."""
import sys, time, pathlib, cv2, numpy as np
ROOT = pathlib.Path(__file__).resolve().parents[2]
sr = cv2.dnn_superres.DnnSuperResImpl_create()
sr.readModel(str(ROOT / '_refs/tools/models/EDSR_x2.pb')); sr.setModel('edsr', 2)
cv2.setNumThreads(4)
TILE, PAD = 256, 8
for name in sys.argv[1:]:
    dst = ROOT / f'_refs/work/up/{name}.png'
    if dst.exists():
        print('пропуск', name); continue
    img = cv2.imread(str(ROOT / f'_refs/work/crops/{name}.png'))
    h, w = img.shape[:2]; t = time.time()
    out = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
    for y in range(0, h, TILE):
        for x in range(0, w, TILE):
            y0, x0 = max(y - PAD, 0), max(x - PAD, 0)
            y1, x1 = min(y + TILE + PAD, h), min(x + TILE + PAD, w)
            up = sr.upsample(img[y0:y1, x0:x1])
            oy, ox = (y - y0) * 2, (x - x0) * 2
            th, tw = min(TILE, h - y) * 2, min(TILE, w - x) * 2
            out[y * 2:y * 2 + th, x * 2:x * 2 + tw] = up[oy:oy + th, ox:ox + tw]
    cv2.imwrite(str(dst), out)
    print(f'{name}: {w}x{h} -> {w*2}x{h*2} за {time.time()-t:.0f} c', flush=True)
