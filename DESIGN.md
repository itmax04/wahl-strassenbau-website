# DESIGN.md: Wahl Straßenbau, дизайн-система «Website 2026»

Статус: **draft**, 2026-10-02. Источник истины — Figma `RftFK0Bf5MXWspQfaAshIj` (страница 00 Foundations `0:1`, переменные
сверены через `get_variable_defs` на узлах `3:2`, `8:2`, `8:485`, `8:925`, `10:653`, `10:939`, `14:2264`).
Если этот файл и Figma расходятся, побеждает Figma, а файл нужно исправить. Значений, которых нет здесь и в Figma, не придумывать.
Прежние стили лежат в `_refs/DESIGN-lamborghini.md` и `_refs/DESIGN-nike.md`. Они **не действуют**.

## 1. Характер
Тёмная индустриальная поверхность (charcoal), тёплый белый текст и сигнальный жёлтый как единственный акцент. Крупные condensed-заголовки
Anton в верхнем регистре, спокойный текст Inter. Настоящие фото камня и садов несут эмоцию, UI остаётся инфраструктурой.
Отдельный визуальный сценарий — «Havarie 24/7» (Emergency band и Emergency button).

## 2. Цвета (CSS custom properties, имена как в Figma)
| Токен | HEX | Роль |
|---|---|---|
| `--color-charcoal` | `#101111` | фон страницы, header, footer; текст на жёлтом и светлом |
| `--color-warm-white` | `#F5F3EE` | основной текст; фон светлой секции «Leistungen» на главной |
| `--color-signal-yellow` | `#F4C431` | Primary CTA, жёлтые линии, активные состояния, eyebrow |
| `--color-stone-gray` | `#85847D` | вторичный текст, только на `#101111` / `#1A1B1B` |
| `--color-surface-raised` | `#1A1B1B` | карточки, полосы, панели |
| `--color-surface-high` | `#232423` | поля ввода |
| `--color-line` | `#2E2F2D` | разделители 1 px |
| `--color-yellow-hover` | `#F7D35C` | hover Primary |
| `--color-error` | `#FF7A6B` | ошибки формы |
| `--color-success` | `#8FD19E` | успешное поле |

Правила контраста: stone-gray не ставить на `#232423` (контраст < 4.5:1). Placeholder — warm-white с непрозрачностью 60 %.
Intro под заголовком — warm-white 80 %.

## 3. Типографика
Шрифты локальные: `fonts/anton-latin.woff2` (Display), `fonts/inter-latin.woff2` (Text), `font-display: swap`, preload. Google Fonts не использовать (DSGVO).
Letter-spacing в Figma задан в процентах: +14 % = `0.14em`.

| Стиль | Desktop | Tablet | Mobile | Шрифт / регистр / трекинг |
|---|---|---|---|---|
| Display/Hero | 104 / 1.00 | 84 / 1.00 | 52 / 1.02 | Anton 400, UPPER |
| Heading/H1 | 88 / 1.00 | 72 / 1.00 | 46 / 1.04 | Anton 400, UPPER |
| Heading/H2 | 56 / 1.04 | 48 / 1.04 | 36 / 1.08 | Anton 400, UPPER |
| Heading/H3 | 28 / 1.14 | 28 / 1.14 | 28 / 1.14 ¹ | Anton 400, UPPER, 0.005em |
| Heading/H4 | 20 / 1.20 | 20 / 1.20 | 20 / 1.20 | Anton 400, UPPER, 0.01em |
| Number/XL · L · M | 72 · 56 · 40 / 1.00 | | | Anton 400 |
| Text/Eyebrow | 13 / 1.5 | | | Inter 600, UPPER, 0.14em, жёлтый |
| Text/Lead | 20 / 1.60 | 20 / 1.60 | 18 / 1.56 | Inter 400 |
| Text/Body · Body Strong | 16 / 1.62 | | | Inter 400 · 600 |
| Text/Small | 14 / 1.57 | | | Inter 400 |
| Text/Caption | 13 / 1.5 | | | Inter 500, 0.02em |
| Text/Button | 15 / 1.2 | | | Inter 600, UPPER, 0.06em |
| Text/Nav | 14 / 1.2 | | | Inter 600, UPPER, 0.08em |
| Text/Label | 13 / 1.3 | | | Inter 600, UPPER, 0.08em |
| Text/Legal Heading | 20 / 1.4 | | | Inter 700 |
| Text/Legal Subheading ² | 17 / 1.5 | | | Inter 600 |

¹ В handoff для mobile указано H3 24/1.16. В переменных mobile-фреймов стоит 28/1.14. Сверять по конкретному фрейму.
² Взято из handoff-брифа, в переменных проверенных узлов не встретилось. Сверить на фреймах юридических страниц.

Минимальный размер основного текста — 16 px. Между брейкпоинтами размеры меняются через `clamp()`. `ß` в верхнем регистре
отображается как `SS` (`lang="de"` + `text-transform: uppercase`); результат проверить.

## 4. Сетка и брейкпоинты
| | Mobile | Tablet | Desktop |
|---|---|---|---|
| Диапазон | ≤ 767 | 768–1279 | ≥ 1280 |
| Макет | 390 | 1024 | 1440 |
| Колонки / gutter | 4 / 16 | 8 / 24 | 12 / 24 |
| Боковые поля | 20 | 48 | 80 (контент max 1280) |

## 5. Отступы, радиусы, эффекты
- Шкала (8-px база): 4, 8, 12, 16, 24, 32, 40, 48, 56, 64, 80, 96, 120, 160.
- Вертикальные отступы секций: 120 / 96 / 64 (desktop / tablet / mobile). Зазоры внутри секций: 56 / 48 / 40.
- Радиусы: 0 у фото и секций; 2 px у кнопок, карточек и полей.
- Тень sticky-шапки: `0 8px 24px rgba(0,0,0,.45)`. Других теней нет: глубину дают поверхности `#101111 → #1A1B1B → #232423`.
- Фокус: кольцо `0 0 0 4px rgba(244,196,49,.35)` + видимый outline, `:focus-visible` на всём интерактивном.
- Жёлтая линия заголовка секции: 48×3. Линия метрики: 40×3. Верхняя граница Emergency band: 3 px.

## 6. Компоненты (кратко; детали и варианты — Figma 01 Components `1:2`, поведение — spec §4)
- **Button**: Primary (жёлтый фон, charcoal текст, стрелка; hover `#F7D35C`), Secondary (прозрачный, рамка 1.5 px warm-white,
  hover — фон warm-white 8 %), Phone (рамка stone-gray, жёлтая иконка), Emergency (фон warm-white, charcoal текст, иконка
  телефона, hover жёлтый), Link (без рамки, жёлтая стрелка). Высота L 56 / M 48, Disabled 40 %. **Одна Primary на экран.**
- **Header** 88 / 80 / 64, Sticky 76 / 68 / 64. **Mobile menu** — полноэкранное. **Footer** — 3 варианта по устройствам.
- **Section heading**, **Service card** (фото 240 px, 4:3), **Reference card** (фото 256 px), **Metric item**, **Emergency band**,
  **Contact field** (Input / Textarea / Select × 5 состояний), **Consent checkbox**, **Gallery tile** (4:3, 16:9, 1:1),
  **TOC item**, **Legal contents mobile**, **Timeline item**, **Process step**, **Chip**, **Equipment row**, **Breadcrumb**.
- **Иконки**: линейные, 24 px, штрих 1.75, цвет жёлтый или warm-white.

## 7. Фото
Только 15 обработанных кадров из `assets/photos/` (AVIF/WebP, 640/1280/полный) через хелпер `{{photo:…}}` в `build.py`.
Одинаковое соотношение сторон внутри одной сетки. Затемнение и кадрирование hero — по фрейму Figma. Alt — из таблицы `39:2`.

## 8. Движение
Только пресеты kinetics.colorion.co, уже записанные в `styles.css` (Underline Draw, Stagger Entrance, Clip Wipe, Number Counter).
Новые кривые не добавлять. Всё отключается при `prefers-reduced-motion: reduce`.

## 9. Можно / нельзя
- Можно: жёлтый для одного главного действия на экране, для линий и активных состояний; верхний регистр для заголовков, label и кнопок.
- Нельзя: жёлтый как фон больших площадей (исключение — плитка «24 h» и кнопки, как в макете); новые акцентные цвета;
  тени на карточках; скругления больше 2 px; описания в верхнем регистре; демо-цифры и тексты из генеративных референсов.
