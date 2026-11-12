# Handoff: восстановление исходников и выкладка wahl-strassenbau.de

## Identity
- Задача: восстановить удалённые исходники сайта и подготовить их к git и выкладке.
- Рабочая папка: `~/Desktop/wahl-strassenbau-recovered`. Git **не инициализирован**, коммитов нет.
- Готовая сборка (эталон): `~/Desktop/wahl-strassenbau-dist`. Это тоже не git-репозиторий.
- GitHub: `itmax04/wahl-strassenbau-website` существует, но пустой (только README, ветки `main` и `stage-00-contract` на `2efce86`).

## Goal and scope
- Пользователь спросил, можно ли пушить и выкладывать сайт. Оригинальная папка `~/Desktop/1/wahl-strassenbau`
  удалена, поэтому сначала восстановили исходники («Да, восстанови»).
- Хостинг пока не выбран. Решение владельца: Cloudflare (Worker + Static Assets, папка `cloudflare/`)
  или PHP-хостинг (`kontakt.php` + `server/` + `.htaccess`). Без одного из этих бэкендов форма `/kontakt.php` не работает.
- В dist все пути завязаны на домен `https://www.wahl-strassenbau.de` (canonical, sitemap, OG); он задан в `SITE` в `build.py`.

## Done
- Восстановление из истории сессий Claude: скрипт `_refs/recovery/recover.py`, происхождение файлов в `_refs/recovery/recovery-meta.json`.
- `styles.css`, `main.js`, `assets/`, `fonts/` скопированы из dist.
- Собраны заново: `src/pages/datenschutz.html` (из `/j/privacy/`), 18 иконок `src/icons/*.svg` (из собранных страниц),
  `.gitignore`, отметки `_refs/work/og/*.txt`. В `src/pages/widerruf.html` блок заменён на `{{widerruf-done}}`.
- Отчёт: `RECOVERY.md`. Память: `~/.claude/projects/-Users-macbook-Desktop-wahl-strassenbau-dist/memory/wahl-source-recovered.md`.

## Verified (2026-11-12, на копии папки в scratchpad, без коммита)
- `python3 build.py && python3 cloudflare/build.py --no-site`, затем `diff -rq ~/Desktop/wahl-strassenbau-dist cloudflare/dist`:
  разницы нет (151 файл). Проверено на неизменённом `build.py`.
- `php tests/php/run.php`: 25/25. `node cloudflare/tests/run.mjs` (node v26): 36/36.
- NOT RUN: `wrangler deploy`, реальная отправка почты (SMTP / `mail()`), проверка на боевом хостинге.

## Open
- Потеряно: git-история (master, figma-2026), исходные фото, `fonts/src/`, `_refs/shots/`.
- Документы могут быть промежуточными версиями: `CLAUDE.md` (от 29.09), `docs/changes/WEB-2026/spec.md`, `DESIGN.md`.
- Если заголовок страницы изменится, `build.py` пересоздаст OG-картинку, а для этого нужен `pip install brotli`.
- Desktop синхронизируется с iCloud: файлы бывают `dataless`, после удаления папок остаются пустые папки «… 2».
  Перед коммитом удалить их командой `find . -type d -empty -delete`.
- Из старой памяти проекта: юридические тексты (Datenschutz и др.) требуют проверки юристом перед публикацией,
  открытые вопросы для заказчика в `docs/KUNDENFRAGEN.md`.

## Next
1. В `~/Desktop/wahl-strassenbau-recovered`: удалить пустые папки, сделать `git init -b main`,
   первый коммит (attribution из system-reminder) и показать пользователю `git status`.
2. Push только после явного согласия пользователя: в `itmax04/wahl-strassenbau-website`
   (там уже есть коммит с README, понадобится pull/rebase или отдельная ветка). Спросить, публичный ли репозиторий.
3. Спросить, где хостинг: Cloudflare или PHP. От ответа зависит, какой бэкенд формы готовить и проверять.
