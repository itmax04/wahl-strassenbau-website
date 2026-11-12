# Wahl Straßenbau на Cloudflare (Workers + Static Assets)

Пакет публикует сайт как **один Cloudflare Worker**: 14 страниц, стили, фото и шрифты раздаются как статические файлы (`dist/`),
а Worker выполняет только форму `POST /kontakt.php`. PHP на Cloudflare не работает, поэтому логика `server/` (ADR-0001)
перенесена на JavaScript ([worker/app.js](worker/app.js), [worker/mail.js](worker/mail.js)): те же проверки, антиспам
(honeypot, минимальное время заполнения, лимит 5 заявок за 10 минут по хешу IP), те же ответы для `main.js`, те же страницы без
JavaScript. Вместо SQLite используется база Cloudflare **D1**, заявки хранятся 90 дней и удаляются ежедневно по расписанию.

> ⚠️ Перед публикацией на домене `wahl-strassenbau.de` нужна юридическая проверка: `docs/KUNDENFRAGEN.md`, разделы A и E
> (в Datenschutz сказано, что хостинг обрабатывает данные только в ЕС, а это не относится к Cloudflare). Адрес `*.workers.dev`
> подходит для показа заказчику.

## Состав пакета
| Файл | Назначение |
|---|---|
| `wrangler.jsonc` | конфигурация Worker: статика, D1, расписание, переменные |
| `worker/index.js` | точка входа: `/kontakt.php` идёт в обработчик форм, остальное отдают статические файлы |
| `worker/app.js`, `worker/mail.js` | обработчик форм и отправка почты (SMTP через TCP-сокеты Cloudflare) |
| `worker/generated.js` | тексты ошибок (`server/messages.json`) и HTML-шаблоны (`server/templates/`), собирается `build.py` |
| `dist/` | готовый сайт и `_headers` (заголовки безопасности и кэша, как в `.htaccess`) |
| `schema.sql` | схема D1 (Worker создаёт её и сам при первой заявке) |

## Вариант A: весь сайт с формами (рекомендуется)
Нужны Node.js 18+ и аккаунт Cloudflare. Команды выполняются в папке пакета (`wahl-strassenbau-cloudflare/` из ZIP или
`cloudflare/` в репозитории). Wrangler (CLI Cloudflare) запускается через `npx` и при первом запуске скачивается.

1. Войдите в Cloudflare (откроется браузер):
   ```bash
   npx wrangler login
   ```
2. Создайте базу для заявок в Западной Европе:
   ```bash
   npx wrangler d1 create wahl-forms --location=weur
   ```
   Скопируйте `database_id` из ответа в `wrangler.jsonc` вместо `00000000-0000-0000-0000-000000000000`.
3. (Необязательно, Worker сделает это сам) создайте таблицы:
   ```bash
   npx wrangler d1 execute wahl-forms --remote --file schema.sql
   ```
4. Опубликуйте:
   ```bash
   npx wrangler deploy
   ```
   Wrangler выведет адрес вида `https://wahl-strassenbau.<ваш-поддомен>.workers.dev`. Сайт и формы работают сразу.

**Почта.** По умолчанию `MAIL_TRANSPORT` равен `log`: заявки сохраняются в D1, но **письма не отправляются**.
Чтобы заявки приходили на `info@wahl-strassenbau.de`, укажите в `wrangler.jsonc` → `vars` SMTP почтового ящика
(`MAIL_TRANSPORT: "smtp"`, `SMTP_HOST`, `SMTP_PORT` 587 и `SMTP_SECURE: "tls"` либо 465 и `"ssl"`, `SMTP_USER`,
`FROM_ADDRESS` с разрешённым для этого ящика адресом). Пароль храните только как секрет:
```bash
npx wrangler secret put SMTP_PASS
```
После этого снова выполните `npx wrangler deploy`. Порт 25 Cloudflare закрывает.

**Свой домен.** Добавьте `wahl-strassenbau.de` в Cloudflare (Websites → Add a domain) и смените NS-серверы у регистратора.
Перед этим проверьте, что Cloudflare перенёс **все** DNS-записи, особенно MX/SPF почты. Затем: Workers & Pages →
`wahl-strassenbau` → Settings → Domains & Routes → Add → Custom domain `www.wahl-strassenbau.de` (и `wahl-strassenbau.de`).
Переадресацию без `www` на `www` настройте в Rules → Redirect Rules (шаблон «Redirect from root to WWW»): так ведёт себя
`.htaccess`, и на этот адрес указывают canonical и sitemap. В настройках зоны выключите Rocket Loader и автоматическую
Web Analytics: они добавляют скрипты, не описанные в Datenschutz.

**Просмотр заявок** (вместо `server/bin/submissions.php`):
```bash
npx wrangler d1 execute wahl-forms --remote --command "SELECT id, created_at, form, name, email, phone, service, mail_status FROM submissions ORDER BY id DESC LIMIT 50"
```
Или через панель: Storage & databases → D1 → `wahl-forms` → Console.

## Вариант B: только статика через панель (без форм)
Workers & Pages → Create → загрузка статических файлов → перетащите папку `dist/`. Сайт откроется, но формы работать
не будут: при отправке посетитель увидит «Senden fehlgeschlagen. Bitte rufen Sie uns an: 0381 25 22 39 41». Подходит только
для показа дизайна.

## Обновление
В репозитории (ветка `figma-2026`) после правок в `src/`:
```bash
python3 cloudflare/build.py
```
Скрипт собирает страницы (`build.py`), `cloudflare/dist/`, `worker/generated.js` и `cloudflare/wahl-strassenbau-cloudflare.zip`.
Потом из папки `cloudflare/` выполните `npx wrangler deploy`.

## Проверки
| Что | Команда | Результат |
|---|---|---|
| Обработчик форм: ответы, D1, антиспам, хранение 90 дней, SMTP с фейковым сервером, совпадение страницы ошибки с PHP | `node cloudflare/tests/run.mjs` | 36/36 |
| Локально в настоящем рантайме Cloudflare | `npx wrangler dev` (в папке `cloudflare/`) | NOT RUN: wrangler не установлен |
| SMTP с STARTTLS/TLS у реального провайдера | после настройки почты | NOT RUN |

Бесплатного тарифа хватает: запросы к статике бесплатны и не ограничены, Worker вызывается только на отправку формы
(лимит 100 000 вызовов в сутки).
