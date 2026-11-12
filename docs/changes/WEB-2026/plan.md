# Технический план WEB-2026

| Поле | Значение |
|---|---|
| Статус | **draft** (исполнение только после того, как владелец переведёт spec и plan в `accepted` и отдельно скомандует «начать») |
| Версия / дата | 0.1 · 2026-10-02 |
| Требования | [spec.md](spec.md) (R-xx, AC-xx) · [ADR-0001](../../decisions/ADR-0001-forms-backend.md) · [DESIGN.md](../../../DESIGN.md) |
| Ветка / база | `figma-2026` от `master@1ebca29`; коммит с документами SDLC — см. `git log` (первый коммит ветки) |
| Исполнитель | Claude Code (desktop), Opus 5.5 `claude-opus-5-5`, effort **high** |

Пометки: **[есть]** — путь или команда существует и проверены 2026-10-02; **[новый]** — создаёт исполнитель.

---

## 0. Правила исполнения (обязательны на всех фазах)
1. Перед кодом прочитать: `CLAUDE.md`, `DESIGN.md`, `intent.md`, `spec.md`, ADR-0001, этот план, `handoff.md`, `docs/KUNDENFRAGEN.md`, `git status`, `git log --oneline -5`.
2. Работать только на ветке `figma-2026`. Каждая фаза заканчивается локальным коммитом `WEB-2026 P-NN: <что>`. Push, merge, rebase `master`,
   `reset --hard`, `clean`, `branch -D`, `rm -rf` запрещены (часть закрыта deny-правилами в `.claude/settings.json`).
3. Вопросов пользователю не задавать. Неясность решать по правилу spec §1 (вид — Figma, факты — CONTENT/legal, поведение — spec)
   и записывать в `report.md` → «Отклонения и решения».
4. Править `src/`, `build.py`, `styles.css`, `main.js`, `server/`; собранные HTML не править руками, только через `python3 build.py`.
5. После каждой фазы обновить `handoff.md`: сделано, коммит, проверки (команда → результат), следующий шаг.
6. Не ослаблять проверки ради зелёного результата. Упавшая проверка остаётся FAIL до исправления причины.
7. Экономия контекста: Figma читать по фрейму или секции (`get_screenshot` с `maxDimension` ≤ 1600, `get_design_context` по
   узлам секций). Огромные фреймы Datenschutz (17–34 тыс. px) целиком не загружать: текст брать из `src/pages/datenschutz.html`,
   из Figma — только оформление TOC и заголовков.
8. Эскалация: если одна и та же проверка не проходит после 2 осмысленных попыток, повысить effort до xhigh (предложить пользователю
   в отчёте, сам не переключать). Если и это не помогло, зафиксировать FAIL с причиной в handoff и report и перейти к следующей фазе,
   если она не зависит от упавшей.

## 1. Стоп-условия (остановиться, закоммитить состояние, записать блокер в handoff и report)
- Figma MCP недоступен или отвечает ошибкой авторизации дольше 3 попыток (без макета работа теряет смысл).
- Требуется push, merge, деплой, внешняя запись, платный сервис, реальные учётные данные или реальная отправка письма.
- Требуется смысловая правка юридического текста или новые факты о компании.
- Требуется разрушительная git-операция или удаление файлов вне задачи.
- Сборка сломана, и исправить её не удаётся (тогда `git revert` последнего коммита фазы — разрешено, это не разрушает историю).

## 2. Фазы

### P-00 Baseline и подготовка
- Команды:
  - `git status --short && git branch --show-current && git log --oneline -3` → чистое дерево, ветка `figma-2026`.
  - `php -v; node -v; python3 --version; lighthouse --version` → записать в handoff.
  - `python3 build.py` **[есть]** → без ошибок (baseline).
  - Проверить deny-правило: `git push --dry-run` должен быть отклонён Claude Code. Remote отсутствует, так что push невозможен в любом случае.
    Записать результат.
  - Опционально: `python3 -m playwright install webkit` (локальная dev-зависимость; если не ставится — Safari/WebKit NOT RUN, D-09).
- Figma-экспорт (только чтение):
  - `get_metadata` для `1:3`, `1:4`, `1:5` → `_refs/tools/figma_routes.py` **[новый]** извлекает все слои с `→` в
    `_refs/figma/routes.json` **[новый]** (`frame`, `layer`, `target`). Ожидается ≈126 уникальных целей.
  - `get_screenshot` всех фреймов из spec §3 (D/T/M + 07F + Menü), `curl` PNG в `_refs/shots/figma/<node>.png` (каталог в `.gitignore`).
- Добавить в `~/Desktop/1/.claude/launch.json` конфигурацию `wahl-php`: `php -S localhost:5178 server/router.php` с `cwd` проекта
  (или эквивалент с `--directory`). Существующую `wahl-preview` не трогать. Конфиг лежит вне репозитория, изменение описать в handoff.
- Свидетельство: handoff заполнен, `routes.json` и PNG на месте. Коммит `WEB-2026 P-00: figma routes export, baseline`.

### P-01 Токены и основа (R-01, DESIGN.md)
- `styles.css` **[есть → переписать]**: `:root` с токенами §2–§5 DESIGN.md, `@font-face` (Anton, Inter, swap), типографическая шкала
  с `clamp()`, контейнер и сетки 4/8/12, утилиты отступов, фокус-стиль, reduced-motion, `@media print`. Kinetics-переменные сохранить.
- `src/layout.html` **[есть]**: `<html lang="de">`, preload шрифтов, skip link.
- Проверка: `python3 build.py` → открыть `/` в preview; computed styles (`javascript_tool`) совпадают с токенами (цвет body, шрифты).
- Коммит `WEB-2026 P-01: design tokens and base styles`.

### P-02 Компоненты (R-03; spec §4)
- `src/layout.html`: Header (3 варианта + sticky), Mobile menu, Footer по `6:266`, `6:437`, `6:632`.
- `build.py` **[есть]**: хелперы для повторяемых блоков — `icon()` (SVG-спрайт `assets/img/icons.svg` **[новый]** из `Icon / *`
  через `get_design_context` / SVG-экспорт), section heading, service/reference card, metric, emergency band, process step, timeline,
  chip, equipment row, breadcrumb, gallery tile, TOC. Переиспользовать существующие `photo_tag`, `bento_html`, `crumbs_html`, `tech_html`, `add_toc`.
- `main.js` **[есть]**: sticky-шапка (> 8 px), меню (aria, ловушка, Esc, scroll-lock), лайтбокс `<dialog>`, слайдер до/после,
  TOC scroll-spy, «Nach oben». Существующие обработчики адаптировать, а не дублировать.
- Проверка: временная страница-витрина не нужна; компоненты проверяются на P-03. Клавиатурная проверка меню в preview.
- Коммит `WEB-2026 P-02: components`.

### P-03 Startseite (01)
- `src/pages/index.html` по `8:2` / `8:485` / `8:925`: все секции из spec §3 п. 1. Kurzanfrage — через `form_html("kurz")`.
- Метрики: «21» вычисляется в `build.py` (май 2005 → дата сборки), «18 … Stand 04/2023».
- Визуальная сверка (AC-02): `_refs/tools/figma_compare.py` **[новый]** делает Playwright-скриншоты 1440/1024/390 (full page)
  и склеивает их рядом с PNG фрейма в `_refs/shots/figma-compare/01-*.png`. Расхождения > 8 px, шрифты, цвета и кадрирование исправить.
- Коммит `WEB-2026 P-03: Startseite`.

### P-04 Страницы услуг и референсов (02–06)
- `src/pages/{leistungen,pflasterarbeiten,garten-landschaft,technik,referenzen}.html` по фреймам spec §3. Слайдер Wappen — на Referenzen.
- Технику брать из `build.py → TECH` (числа 37/14/6/17 считаются).
- Сверка AC-02 и AC-03 для каждой страницы; коммит после каждых 1–2 страниц: `WEB-2026 P-04: <страница>`.

### P-05 Kontakt, Fehler-состояние, Danke, 404, Sitemap (07, 07F, 08, 13, 14)
- `src/pages/{kontakt,danke,404,sitemap}.html`; форма `kontakt` с новым полем `einwilligung` (Consent `7:605`) в `build.py → form_html`.
- Состояние 07F воспроизводится клиентской валидацией (P-08). Для сверки AC-02: Playwright отправляет пустую или невалидную форму и делает скриншот.
- Коммит `WEB-2026 P-05: Kontakt, Danke, 404, Sitemap`.

### P-06 Юридические страницы (09–12)
- `src/pages/{impressum,datenschutz,gewaehrleistung,widerruf}.html`: **текст не менять** (R-08.3). Добавить разметку TOC, якоря и
  заголовки по Figma. На Gewährleistung — QR-код SVG, сгенерированный локально в `build.py` (без внешних сервисов; если нет
  QR-генератора на чистом Python — небольшой генератор в `_refs/tools/qr.py` **[новый]** или готовый SVG из Figma-узла `22:2` через
  экспорт), плюс ссылка рядом. Widerruf — форма `widerruf`.
- Проверка AC-09 (скрипт сравнения текста, см. P-10). Коммит `WEB-2026 P-06: legal pages`.

### P-07 Backend по ADR-0001 (R-05, R-06)
- Новые файлы: `server/bootstrap.php`, `server/config.example.php`, `server/lib/{Validator,Mailer,LogMailer,MailFunctionMailer,SmtpMailer,SubmissionStore,RateLimiter}.php`,
  `server/bin/submissions.php`, `server/router.php`, `storage/.htaccess` (`Require all denied`), `storage/index.html` (пустая заглушка).
- `kontakt.php` **[есть]** → тонкий вход: `require server/bootstrap.php` и обработка. Логику и тексты подтверждения Widerruf перенести, не потерять.
- `.gitignore` **[есть]**: `server/config.local.php`, `storage/*.sqlite*`, `storage/*.log`, `_refs/shots/`, `_refs/figma/*.png`.
- `.htaccess` **[есть]**: закрыть `server/`, `storage/`, `*.sqlite`, `config.local.php`; `kontakt.php` оставить доступным.
- Тесты **[новые]**: `tests/php/run.php` (мини-раннер без зависимостей: поднимает `php -S` на свободном порту с env
  `MAIL_TRANSPORT=log`, временным `STORAGE_PATH`, делает HTTP-запросы через `stream_context`), `tests/php/fake_smtp.php`
  (`stream_socket_server`, отвечает 220/250/354/221, пишет диалог в файл). Кейсы — список AC-05.
- Команда: `php tests/php/run.php` → все PASS, код выхода 0.
- Коммит `WEB-2026 P-07: forms backend (ADR-0001)`.

### P-08 Клиентская логика форм и интерактив (R-04, R-09)
- `main.js`: валидация с текстами из `data-*`-атрибутов, которые генерирует `build.py` (один источник текстов), состояния полей, сводка ошибок
  с фокусом, отправка `fetch` (`Accept: application/json`), обработка 422/429/502, успех (redirect или D-05), поле `t`.
- Проверка: Playwright-сценарии из AC-05 (клиентская часть) и AC-06; отдельно отправка с отключённым JS (`java_script_enabled=False`).
- Коммит `WEB-2026 P-08: client forms and interactions`.

### P-09 SEO, OG, sitemap, контроль фото
- `build.py`: canonical, OG, JSON-LD, sitemap — сохранить; `make_og` перевести на цвета Figma; `noindex` для Danke и 404 (уже есть, проверить).
- `_refs/tools/dupcheck.py` **[есть]** обновить: допустимые повторы — по таблице `39:2` («Einsatz»).
- Коммит `WEB-2026 P-09: SEO, OG, photo usage`.

### P-10 Полная проверка и review
- Сервер: `python3 build.py && php -S localhost:5178 server/router.php` (или `preview_start wahl-php`).
- `_refs/tools/e2e_figma.py` **[новый]**, заменяет правило «золото ≤ 1» на «Primary ≤ 1 на экран». Покрывает AC-01, AC-03, AC-04
  (по `routes.json`), AC-06, AC-08, консоль без ошибок, отсутствие 404 ресурсов, печать и reduced-motion. Старые `e2e.py` и `e2e2.py`
  оставить как историю; в README указать, что действующий — `e2e_figma.py`.
- `_refs/tools/legal_textcheck.py` **[новый]**: AC-09 (сравнение с `git show master:src/pages/<f>.html`).
- `_refs/tools/figma_compare.py`: полный прогон AC-02 по всем 16 состояниям × 3 ширины.
- Lighthouse (AC-07), mobile и desktop:
  `lighthouse http://localhost:5178/<url> --output=json --output-path=_refs/shots/lighthouse/<name>-mobile.json --chrome-flags="--headless=new" --quiet`
  и то же с `--preset=desktop`.
- curl-проверки AC-10; `git ls-files | grep -E 'config.local|\.sqlite|\.log$'` → пусто; `git grep -nE 'SMTP_PASS\s*=\s*.+'` → только example с пустым значением.
- Review (AC-11): `/code-review high` по диффу ветки против `master`. Затем отдельная проверка соответствия spec: пройти таблицу AC,
  у каждого критерия указать свидетельство. Чеклист review: корректность, безопасность (ADR-угрозы), доступность, отсутствие
  выдуманного контента, лишний объём диффа, секреты, совместимость URL.
- Исправления → повторный прогон затронутых проверок. Коммит `WEB-2026 P-10: verification fixes`.

### P-11 Документация, отчёт, запуск
- Обновить `README.md` (команды, конфиг почты и хранилища, что выкладывать на хостинг, cron для purge — опционально), `CLAUDE.md`
  (команды и инструменты, если изменились), `docs/KUNDENFRAGEN.md` (новые вопросы).
- `docs/changes/WEB-2026/report.md` **[новый]**: модель, effort и время; таблица AC → статус → команда → коммит; таблица
  «страница → фрейм → URL»; отклонения и решения; TEXTVORSCHLAG-список; Lighthouse; непроверенное (NOT RUN) с причинами; ссылки на
  `_refs/shots/figma-compare/`.
- Запустить сервер (`preview_start wahl-php` или фоновый `php -S`), проверить `curl -sI http://localhost:5178/` → 200, сделать
  финальный скриншот главной.
- Коммит `WEB-2026 P-11: docs and report`. Сообщить пользователю ссылку `http://localhost:5178`, путь к report и KUNDENFRAGEN. **Остановиться.**

## 3. Зависимости
- Новых runtime-зависимостей нет (PHP stdlib + `pdo_sqlite`; Python stdlib + PIL/numpy/playwright уже установлены).
- Допустимые локальные dev-установки: браузеры Playwright (`python3 -m playwright install webkit|chromium`). Остальное — NOT RUN с причиной.

## 4. Риски и откат
| Риск | Митигирующее действие |
|---|---|
| Контекст переполняется на 48+ фреймах | handoff после каждой фазы; читать фреймы по секциям; при сжатии продолжать по handoff |
| Расхождение Figma-текстов и фактов | правило spec §1, запись в report |
| Нативный SMTP-клиент работает иначе у реального хостера | `log` и `mail` по умолчанию; SMTP проверен только против фейкового сервера (NOT RUN на реальном) |
| Apache-правила не проверены локально | review `.htaccess` + роутер повторяет запреты; NOT RUN в report |
| Потеря работы | коммит в конце каждой фазы; откат — `git revert <sha>` или возврат к `master` (не тронут) |

## 5. Готово, когда
AC-01…AC-12 имеют статус PASS или NOT RUN с причиной, которую принимает владелец. `report.md` заполнен, сервер запущен, ссылка выдана,
дерево чистое (`git status`), все коммиты на `figma-2026`, `master` не изменён.
