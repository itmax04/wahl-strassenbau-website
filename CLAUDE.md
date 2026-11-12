# Wahl Straßenbau: редизайн сайта wahl-strassenbau.de

Статический сайт (HTML/CSS/JS, без фреймворков) на замену Jimdo. 13 страниц с теми же URL, что были на Jimdo.
Тексты и факты только из CONTENT.md и с оригинального сайта; новых фактов не выдумывать.

@DESIGN.md

## Как устроено
- `src/layout.html` — общие шапка, меню, подвал. `src/pages/*.html` — содержимое страниц (заголовок `title/description/class`, затем `---`, затем HTML).
- `python3 build.py` собирает всё в готовые HTML-файлы в корне и в папках (`/leistungsangebot/index.html` и т. д.). Править нужно `src/`, а не собранные файлы.
- Пути в HTML корневые (`/styles.css`), сайт должен лежать в корне домена.
- Превью: `preview_start wahl-preview` (конфиг в `~/Desktop/1/.claude/launch.json`, порт 5178).

## Проектные решения
- Стиль: Nike (DESIGN.md). Nike Futura ND / Helvetica Now заменены на Anton (только заголовки hero) и Inter, как предписывает DESIGN.md. Шрифты в `fonts/` (без запросов к Google: GDPR).
- Анимации с kinetics.colorion.co (значения в комментариях `styles.css`), везде учтён `prefers-reduced-motion`.
- Галереи открываются в нативном `<dialog>` (см. `main.js`).
- `_refs/` содержит исходный код компонентов 21st.dev (Hero 12, Content Grid Section). В продакшн не идёт.
- Юридические страницы (Impressum, Datenschutz, Gewährleistung) перенесены дословно из Jimdo и требуют юридической проверки перед публикацией.
