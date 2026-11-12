# Wahl Straßenbau: сайт wahl-strassenbau.de

Статический сайт (HTML/CSS/JS без фреймворков) с PHP-обработчиком форм для Wahl Straßenbau GmbH & Co. KG (Papendorf/Rostock).
Заменяет сайт на Jimdo, URL сохранены. Дизайн — Figma «Website 2026» (`RftFK0Bf5MXWspQfaAshIj`, см. `DESIGN.md`).

> Ветка `figma-2026` (задача WEB-2026): реализация завершена локально, итог и проверки — `docs/changes/WEB-2026/report.md`.
> Перед публикацией обязательна юридическая проверка и решения по хостингу: `docs/KUNDENFRAGEN.md`.

## Требования
- Python 3.10+ с `Pillow` и `fontTools` (сборка, OG-картинки), PHP 8.1+ с `pdo_sqlite`, `mbstring`, `openssl` (формы).
- Для проверок: Google Chrome, Python-пакет `playwright` (опционально WebKit: `python3 -m playwright install webkit`), `lighthouse`.

## Быстрый запуск
```bash
python3 build.py
```
```bash
php -S localhost:5178 server/router.php
```
Затем откройте `http://localhost:5178` (в Claude Code: `preview_start wahl-php`). Роутер отдаёт статику (gzip, корректные MIME, 404 через
`/404.html`), исполняет только `kontakt.php` и закрывает служебные пути. Локально письма не отправляются: транспорт `log` пишет их в
`storage/mail.log`, заявки — в `storage/submissions.sqlite`.

## Проверки
| Что | Команда |
|---|---|
| Backend форм (25 тестов, фейковый SMTP) | `php tests/php/run.php` |
| Сайт целиком: статусы, переполнение 320–1920, маршруты Figma, формы с JS и без, доступность, SEO | `python3 _refs/tools/e2e_figma.py http://localhost:5178 --webkit` |
| Сравнение с Figma (16 состояний × 1440/1024/390) | `python3 _refs/tools/figma_compare.py` → `_refs/shots/figma-compare/` |
| Юридические тексты дословно как в `master` | `python3 _refs/tools/legal_textcheck.py` |
| Использование фото и alt-тексты по Figma 39:2 | `python3 _refs/tools/dupcheck.py` |
| Маршруты прототипа из метаданных Figma | `python3 _refs/tools/figma_routes.py` |
| Lighthouse | `lighthouse http://localhost:5178/ --output=json --output-path=_refs/shots/lighthouse/home-mobile.json --chrome-flags="--headless=new"` (+ `--preset=desktop`) |

`e2e.py` и `e2e2.py` в `_refs/tools/` — проверки прежнего стиля (Lamborghini), оставлены как история.

## Структура
- `src/layout.html`, `src/pages/*.html` — исходники страниц; `src/icons/*.svg` — иконки Figma. `build.py` собирает HTML в корень и подпапки,
  OG-картинки, `sitemap.xml`, `robots.txt` и шаблоны `server/templates/` (ответы сервера без JavaScript). Собранные файлы руками не править.
- `styles.css`, `main.js`, `fonts/`, `assets/` — фронтенд. Фото: 15 кадров в `assets/photos/` (AVIF/WebP, 640/960/1280/полный).
- `kontakt.php` — endpoint форм; `server/` — backend (ADR-0001); `storage/` — SQLite и лог писем, закрыт для веба.
- `docs/` — SDLC: `changes/WEB-2026/` (intent, spec, plan, handoff, report), `decisions/` (ADR), `KUNDENFRAGEN.md`.
- `_refs/` — инструменты, данные Figma (`_refs/figma/`), отчёты (`_refs/shots/`, не в git). На хостинг не выкладывается.

## Конфигурация форм
Скопируйте `server/config.example.php` в `server/config.local.php` (файл не попадает в git) или задайте переменные окружения
(они имеют приоритет): `RECIPIENT`, `FROM_ADDRESS`, `MAIL_TRANSPORT` (`log` | `mail` | `smtp`), `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
`SMTP_PASS`, `SMTP_SECURE` (`tls` | `ssl` | `none`), `STORAGE_PATH`, `RETENTION_DAYS` (90), `RATE_LIMIT` (`5/600`), `MIN_FILL_SECONDS` (3),
`ALLOWED_ORIGINS`, `CLIENT_IP_HEADER` (только за прокси/CDN). Без конфигурации действует `log` — реальные письма не уходят.
Подробнее: `docs/decisions/ADR-0001-forms-backend.md`.

Заявки (только CLI): `php server/bin/submissions.php list [--days N]`, `export --format csv|json`, `purge`.
Заявки старше `RETENTION_DAYS` удаляются при каждой новой заявке; при желании дополнительно ежедневный cron:
`php /pfad/server/bin/submissions.php purge`.

## Что выкладывать на хостинг
Собранные HTML (корень и папки `about/`, `j/`, `kontakt/`, `leistungsangebot/`, `referenzen/`, `sitemap/`, `technikangebot/`), `404.html`,
`styles.css`, `main.js`, `fonts/`, `assets/`, `kontakt.php`, `server/` (с `config.local.php`), `storage/` (пустой, с `.htaccess`),
`.htaccess`, `robots.txt`, `sitemap.xml`. Не выкладывать: `src/`, `_refs/`, `docs/`, `tests/`, `build.py`, `.git`, `.claude`, `.agents`.
Хранилище по возможности вынести за пределы webroot (`STORAGE_PATH`).
**Cloudflare** (без PHP): пакет `cloudflare/` — Worker с формами на D1 и статикой; сборка `python3 cloudflare/build.py`,
инструкция [cloudflare/README.md](cloudflare/README.md), тесты `node cloudflare/tests/run.mjs`. Деплой не входил в WEB-2026; вопросы по хостингу — `docs/KUNDENFRAGEN.md`, раздел C.

## Ограничения и безопасность
- Секреты (SMTP) только в `server/config.local.php` или в окружении; в логи не пишутся.
- Юридические тексты перенесены дословно и **требуют юридической проверки перед публикацией** (`docs/KUNDENFRAGEN.md`, раздел A).
- Никаких сторонних скриптов, трекеров и шрифтов с CDN (DSGVO). Внешняя ссылка — только «Route planen» (Google Maps, по клику).
