# Восстановление проекта (2026-11-12)

Исходная папка `~/Desktop/1/wahl-strassenbau` была удалена. Копий не было: Time Machine не настроен, репозиторий
`itmax04/wahl-strassenbau-website` на GitHub пустой. Корзину проверить не удалось.

## Откуда взяты файлы
- **Текстовые файлы** восстановлены из истории сессий Claude Code (`~/.claude/projects/-Users-macbook-Desktop-1/`).
  Все записи, правки, чтения и shell-изменения файлов проигрывались в хронологическом порядке.
  Скрипт лежит в `_refs/recovery/recover.py`, происхождение каждого файла — в `_refs/recovery/recovery-meta.json`.
- **`styles.css`, `main.js`, `assets/`, `fonts/`** скопированы из готовой сборки `~/Desktop/wahl-strassenbau-dist`
  (это финальные версии).
- **`src/pages/datenschutz.html`** в истории не сохранился. Он восстановлен из собранной страницы `/j/privacy/`
  (тело страницы плюс макросы `{{toc}}` и `{{toc-mobile}}`), поэтому иконки и хлебные крошки в нём уже развёрнуты в HTML.
- **18 иконок в `src/icons/`** извлечены из собранных страниц.
- **`src/pages/widerruf.html`**: блок подтверждения заменён на макрос `{{widerruf-done}}`, как в финальной версии.
- **`.gitignore`** написан заново, оригинал не сохранился.

## Проверка
- `python3 build.py && python3 cloudflare/build.py --no-site`: результат `cloudflare/dist/` **побайтно совпадает**
  с `~/Desktop/wahl-strassenbau-dist` (151 файл). Значит, исходники сайта (`src/`, `build.py`, `styles.css`, `main.js`,
  ассеты) соответствуют выложенной версии.
- `php tests/php/run.php`: 25/25. `node cloudflare/tests/run.mjs`: 36/36.

## Что потеряно или может быть устаревшим
- История git (ветки `master` и `figma-2026`, коммиты P-00…P-11).
- Исходники фото до обработки, модели апскейла, `fonts/src/`, скриншоты в `_refs/shots/`.
- Документы могут быть промежуточными версиями: `CLAUDE.md` (версия от 29.09, без поздних разделов),
  `docs/changes/WEB-2026/spec.md`, `DESIGN.md`. На сборку сайта это не влияет.
- Генерация OG-картинок в `build.py` требует модуль `brotli` (`pip install brotli`), так как читает шрифты woff2.
  Готовые картинки уже лежат в `assets/og/`, отметки `_refs/work/og/*.txt` восстановлены. Пока заголовки страниц
  не меняются, картинки не пересоздаются и `brotli` не нужен.
