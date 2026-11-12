"""Шаг 3: единая мягкая цветокоррекция (одна и та же для всех кадров).
1) баланс белого к нейтрали по средним тонам (ослаблен на 35 %),
2) автоуровни по яркости с отсечением 0,5 % с обеих сторон,
3) лёгкий S-контраст,
4) общий чуть тёплый тон (одинаковый множитель для всех кадров) и +6 % насыщенности."""
import numpy as np
from PIL import Image

W = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
WARM = np.array([1.03, 1.005, 0.955], dtype=np.float32)


def grade(img: Image.Image) -> Image.Image:
    a = np.asarray(img.convert('RGB')).astype(np.float32) / 255
    lum = a @ W
    mid = (lum > 0.15) & (lum < 0.85)
    means = a[mid].mean(axis=0) if mid.sum() > 1000 else a.reshape(-1, 3).mean(axis=0)
    gain = np.clip(means.mean() / means, 0.88, 1.12)
    a = np.clip(a * (1 + (gain - 1) * 0.65), 0, 1)
    lum = a @ W
    lo, hi = np.percentile(lum, [0.5, 99.5])
    a = np.clip((a - lo) / max(hi - lo, 1e-3), 0, 1)
    s = a * a * (3 - 2 * a)
    a = a + 0.35 * (s - a)
    a = np.clip(a * WARM, 0, 1)
    lum = (a @ W)[..., None]
    a = np.clip(lum + (a - lum) * 1.06, 0, 1)
    return Image.fromarray((a * 255 + 0.5).astype(np.uint8))
