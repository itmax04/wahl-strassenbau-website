# Передача WEB-2026

Статус: draft. Обновлено: 2026-10-02 (исполнение идёт, см. журнал фаз).
Исполнитель обновляет этот файл **после каждой фазы plan.md** и перед любым сжатием контекста или сменой модели.

| Поле | Значение |
|---|---|
| Ветка / последний коммит | `figma-2026` / коммит с документами SDLC (`git log -1`) |
| Модель / effort / версия клиента | `claude-opus-5-5`, effort high, Claude Code desktop (Code tab) |
| Цель и границы | [spec.md](spec.md) (статус: draft → должен быть accepted до начала) |
| Текущая фаза | не начата; следующая — P-00 |

## Сделано
- SDLC-документы: intent, spec, ADR-0001, plan, handoff, executor-prompt, DESIGN.md (Figma), KUNDENFRAGEN, README, CLAUDE.md, `.claude/settings.json` (deny).

## Следующий шаг
P-00 из [plan.md](plan.md): baseline, экспорт маршрутов и скриншотов Figma, конфигурация `wahl-php`.

## Проверки
| Команда | Коммит | Результат |
|---|---|---|
| — | — | NOT RUN (реализация не начиналась) |

## Открытые вопросы
См. [docs/KUNDENFRAGEN.md](../../KUNDENFRAGEN.md). Блокеров разработки нет.

## Права
Разрешено: локальные коммиты на `figma-2026`, локальные dev-установки (Playwright-браузеры), запуск локальных серверов, чтение Figma MCP.
Запрещено: push, merge и rebase `master`, `reset --hard`, `clean`, `branch -D`, `rm -rf`, деплой, реальная отправка писем, платные сервисы,
смысловая правка юридических текстов. Основание: решения владельца от 2026-10-02 (intent, spec §11).

## Риски / откат
Точка возврата — `master@1ebca29` (не меняется). Откат фазы — `git revert <sha>`.

## Журнал фаз
<!-- Шаблон записи:
### P-NN <название> — <дата>
Коммит: <sha>. Файлы: <основные>. Проверки: <команда → PASS/FAIL/NOT RUN>. Решения: <D/отклонения>. Следующий шаг: <P-NN+1>.
-->

### P-00 Baseline — 2026-10-02
Среда: PHP 8.5.11, Node 26.0.0, Python 3.13.5, Lighthouse 13.5.0, Playwright (python) с `channel='chrome'` (Google Chrome), Safari.app; Firefox нет.
Baseline: `python3 build.py` → OK (14 страниц). `git push`: remote отсутствует + deny-правило `Bash(git push *)` в `.claude/settings.json` (не запускалось).
Figma: `get_metadata` 1:3/1:4/1:5 → `_refs/figma/meta-*.xml`; `_refs/tools/figma_routes.py` → `_refs/figma/routes.json` (382 маршрута, 47 целей).
PNG 47 фреймов (15 D + 16 T + 16 M) в `_refs/shots/figma/<node>.png` (1:1, gitignored).
`~/Desktop/1/.claude/launch.json`: добавлена `wahl-php` (`php -S localhost:5178 -t wahl-strassenbau wahl-strassenbau/server/router.php`), `wahl-preview` не тронута.
WebKit Playwright: установка запущена в фоне (лог в scratchpad).
Следующий шаг: P-01 токены.

### P-01…P-03 Токены, компоненты, Startseite — 2026-10-02
Коммит: см. `git log` («WEB-2026 P-01–P-03»). Файлы: `styles.css` (переписан: токены Figma, clamp-типографика 390→1024→1440, компоненты),
`src/layout.html` (Header 6:266, Mobile menu 6:437, Footer 6:632), `build.py` (icon(), формы с data-msg, crumbs, TOC, OG в цветах Figma),
`main.js` (sticky > 8 px, меню с фокус-ловушкой/Esc/scroll-lock, счётчики, stagger, лайтбокс, слайдер, TOC scroll-spy, «Nach oben», формы),
`src/icons/*.svg` (30 иконок Figma 4:4), `src/pages/index.html`, `server/router.php` (минимальный роутер, полный backend — P-07),
`_refs/tools/figma_compare.py` (AC-02), `_refs/figma/photos.json` (таблица 39:2).
Проверки: `python3 _refs/tools/figma_compare.py --only 01` → высота 1440: −0.3 %, 1024: −1.1 %, 390: −0.9 %; визуально совпадает.
`python3 build.py` → index OK; 5 страниц (leistungen, pflasterarbeiten, garten-landschaft, technik, referenzen) ещё на старых макросах → строгий
режим сборки сообщает ошибку до P-04 (ожидаемо, не скрыто).
Порт 5178 был занят старым `python3 -m http.server` этого проекта (PID 6313, 2 дня) — остановлен, запущен `wahl-php`.
Следующий шаг: P-04 (страницы 02–06).

### P-04 Страницы 02–06 — 2026-10-02
Файлы: `src/pages/{leistungen,pflasterarbeiten,garten-landschaft,technik,referenzen}.html`, `build.py` (макросы `{{cta|…}}`, `{{gallery:…}}`,
`{{compare}}`, `{{tech:…}}`, `{{tech-groups}}`, параметр `zoom` у `{{photo}}`), `styles.css` (phero, svc, split, checks, ctaband, verlege, techsum,
techgrp, cases, compare).
Проверки: `python3 build.py` → OK (без ошибок макросов). `figma_compare.py --only 02,03,04,05,06`: Δ высоты 1440: −1.0…+0.5 %; 1024: −2.7…+0.4 %;
390: −3.1…+3.7 %; визуально по секциям совпадает (сверено 02/03/04/05 D+M, 06 T).
Следующий шаг: P-05 (Kontakt, 07F, Danke, 404, Sitemap).

### P-05 Kontakt, 07F, Danke, 404, Sitemap — 2026-10-02
Файлы: `src/pages/{kontakt,danke,404,sitemap}.html`, `build.py` (форма kontakt: Name/E-Mail во всю ширину, Telefon+Leistung в ряд,
заголовок «Kontaktformular», сводка ошибок по 07F), `main.js` (сводка «N Pflichtfelder fehlen …», проверка на blur только после первой
отправки — иначе сообщение сдвигало кнопку и первый клик промахивался), `_refs/tools/figma_compare.py` (сценарий 07F), `styles.css`.
Проверки: `figma_compare.py --only 07,07F,08,13,14` → Δ высоты ≤ 1.8 % (кроме 404 tablet, см. выше; визуально совпадает).
Следующий шаг: P-06 юридические страницы.

### P-06 Юридические страницы — 2026-10-02
Файлы: `src/pages/{impressum,datenschutz,gewaehrleistung,widerruf}.html` (тексты из `master`, только разметка), `assets/img/qr-europa-garantien.svg`,
`_refs/tools/legal_textcheck.py` (новый, AC-09), `build.py` (TOC: sticky + mobile details, `{{toc-count}}`; форма widerruf по Figma 12:2930), `styles.css`.
Проверки: `python3 _refs/tools/legal_textcheck.py` → PASS ×4 (0 расхождений), Demo-Werte 0; негативный тест (подмена слова) → FAIL как ожидалось.
`figma_compare.py --only 09,10,11,12` → Δ высоты −1.9…+0.5 %. Горизонтальный скролл: 14 URL × 320/360/390/768/1024/1280/1440/1920 → нет.
Следующий шаг: P-07 backend по ADR-0001.

### P-07 Backend по ADR-0001 — 2026-10-02
Файлы: `kontakt.php` (тонкий вход), `server/{bootstrap.php,config.example.php,messages.json,router.php,.htaccess}`,
`server/lib/{Validator,Mailer,Message,LogMailer,MailFunctionMailer,SmtpMailer,SubmissionStore,RateLimiter,FormHandler,Page}.php`,
`server/bin/submissions.php`, `server/templates/*` (генерирует build.py: layout + формы для ответов без JS), `storage/{.htaccess,index.html}`,
`tests/php/{run.php,fake_smtp.php}`, `.gitignore`, `.htaccess`.
Проверки: `php tests/php/run.php` → 22/22 PASS (405, valid kontakt/kurz/widerruf, 422, consent, длины, honeypot, быстрое заполнение, чужой
Origin/Referer 403, CRLF, XSS, SQL-кавычки, без JS 303/D-05, роутер 404 + MIME, тексты client=server, rate limit 429 без сырого IP,
сбой транспорта 502 + запись, SMTP против фейка, purge, CLI).
Решения: тексты ошибок — единый `server/messages.json` (build.py и Validator); widerruf без JS → страница подтверждения 200 (D-05, приоритет над R-05.7).
Следующий шаг: P-08 клиентская часть форм и интерактив (Playwright).

### P-08 Клиентская логика форм и интерактив — 2026-10-02
Файлы: `_refs/tools/e2e_figma.py` (новый; поднимает свой php -S для форм), `styles.css` (чекбокс согласия: настоящий input поверх
декоративного квадрата), `main.js` (сводка 07F, проверка после первой отправки, D-05, сетевая ошибка).
Проверки: `python3 _refs/tools/e2e_figma.py http://localhost:5178 --webkit` → 38/38 PASS: 14 URL (200, один h1, landmarks, lang, skip link,
консоль и ресурсы без ошибок), 404, без горизонтального скролла 7 ширин, 120 маршрутов Figma, SEO, ß→SS, меню (ловушка/Esc/фокус),
лайтбокс, слайдер, фокус-кольцо, sticky 76 px, «Nach oben» + scroll-spy, reduced-motion, печать, ≤ 1 Primary на экран, 07F, успех → Danke
(kontakt, kurz), D-05, сетевая ошибка, без JS (303 и страница ошибки), WebKit 390 px.
Следующий шаг: P-09 SEO/OG/фото.

### P-09 SEO, OG, фото — 2026-10-02
Файлы: `_refs/tools/dupcheck.py` (переписан: повторы как во фреймах Figma, alt по 39:2, dHash), `build.py` (OG в цветах Figma —
перегенерированы `assets/og/*.jpg`; canonical/OG/JSON-LD/sitemap/noindex сохранены; `og:url` добавлен).
Проверки: `python3 _refs/tools/dupcheck.py` → «Keine Verstöße»; SEO — в `e2e_figma.py` (AC-08 PASS).
Следующий шаг: P-10 полная проверка (Lighthouse, curl AC-10, code review).

### P-10 Полная проверка и review — 2026-10-02
Lighthouse (`_refs/shots/lighthouse/*.json`): desktop `/`, `/referenzen/`, `/kontakt/`, `/j/privacy/` → 99–100 во всех категориях;
mobile → perf 97/98/100/100, остальные 100; LCP mobile главной 2.41–2.56 s в трёх прогонах (медиана 2.43 s), Referenzen 2.48 s, CLS 0.
AC-10 curl: 11 закрытых путей → 404; `git ls-files` без config.local/sqlite/log; SMTP_PASS не задан в git.
`/code-review high` (master...figma-2026): 9 находок → все исправлены; `php tests/php/run.php` 25/25; `e2e_figma.py --webkit` 38/38;
`figma_compare.py` (16 состояний × 3 ширины) Δ высоты ≤ 3.7 %; `legal_textcheck.py` PASS; `dupcheck.py` OK.
Следующий шаг: P-11 документация, отчёт, запуск.

### P-11 Документация, отчёт, запуск — 2026-10-02
Файлы: `README.md` (команды, проверки, конфиг, деплой-список), `CLAUDE.md` (превью wahl-php, инструменты, формы), `docs/KUNDENFRAGEN.md`
(C6, C7, D6), `docs/changes/WEB-2026/report.md` (итог: AC-01…AC-12, страницы ↔ фреймы, Lighthouse, TEXTVORSCHLAG, NOT RUN, R-1…R-29).
Сервер: `preview_start wahl-php` → http://localhost:5178, `curl -sI` → 200.
Состояние: реализация WEB-2026 завершена локально; push/merge/deploy не выполнялись. Следующий шаг — приёмка владельцем и ответы на KUNDENFRAGEN.

## После P-11: пакет для Cloudflare (2026-10-02, по запросу владельца)
- `cloudflare/`: Worker + Static Assets. Формы перенесены с PHP на JS (`worker/app.js`, `worker/mail.js`), хранение в D1
  (90 дней, cron), почта `log` | `smtp` (TCP-сокеты Cloudflare). Сборка `python3 cloudflare/build.py` → `dist/`, `generated.js`, ZIP.
- Проверки: `node cloudflare/tests/run.mjs` 36/36 (D1 заменён node:sqlite, SMTP на `fake_smtp.php`, страница ошибки = PHP);
  `php tests/php/run.php` 25/25. NOT RUN: `wrangler dev`/deploy (wrangler не установлен; деплой выполняет владелец), реальный SMTP.
- `/cloudflare/` закрыт в `server/router.php` и `.htaccess`. Вопросы: `docs/KUNDENFRAGEN.md`, раздел E (E1 — блокер публикации на домене).
