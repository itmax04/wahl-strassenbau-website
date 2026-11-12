# Отчёт WEB-2026: сайт Wahl Straßenbau по Figma «Website 2026»

| Поле | Значение |
|---|---|
| Статус | **готово к приёмке владельцем** (локально); публикация заблокирована юридической проверкой (`docs/KUNDENFRAGEN.md`, A) |
| Ветка / коммиты | `figma-2026`: `8963575` P-00 … `f4bd66b` P-10, отчёт — коммит P-11 (`git log master..figma-2026`); `master@1ebca29` не изменён |
| Исполнитель | Claude Code (desktop), `claude-opus-5-5`, effort high; 2026-10-02, ~12:45–13:55 и ~18:40–19:15 (пауза — лимит сессии) |
| Локальный запуск | `python3 build.py && php -S localhost:5178 server/router.php` → http://localhost:5178 (или `preview_start wahl-php`) |
| Эскалация до xhigh | не потребовалась: ни одна проверка не упала дважды подряд |

## Итог по критериям приёмки
| AC | Статус | Свидетельство (команда → результат) | Коммит |
|---|---|---|---|
| AC-01 | PASS | `python3 build.py` без ошибок (строгий режим макросов); `e2e_figma.py`: 14 URL → 200, `/gibt-es-nicht/` → 404 с телом `/404.html` | f4bd66b |
| AC-02 | PASS | `python3 _refs/tools/figma_compare.py`: 16 состояний (14 страниц + 07F + Menü; desktop-меню в Figma нет) × 1440/1024/390 = 47 пар в `_refs/shots/figma-compare/`; Δ высоты страниц ≤ 3.1 %, секции сверены визуально; отклонения — R-3…R-29 | f4bd66b |
| AC-03 | PASS | `e2e_figma.py`: 14 URL × 320/390/768/1024/1280/1440/1920 — `scrollWidth ≤ clientWidth` | f4bd66b |
| AC-04 | PASS | `figma_routes.py` → `_refs/figma/routes.json` (382 слоя, 126/128/128 по устройствам); `e2e_figma.py`: 120 уникальных маршрутов (страница, слой, цель) → 0 несоответствий; маршруты внутри инстансов Header/Footer/Menü проверены по компонентам (R-2) | f4bd66b |
| AC-05 | PASS | `php tests/php/run.php` → 25/25 (валидные/невалидные, honeypot, быстрое заполнение, rate limit, чужой Origin/Referer, `Origin: null`, CRLF, XSS, SQL-кавычки, сбой транспорта, отказ хранилища, purge, CLI, SMTP против фейка, длинные строки, IP за прокси); `e2e_figma.py`: 07F, сводка с фокусом, успех → Danke (kontakt, kurz), D-05, сетевая ошибка, без JS (303 и страница ошибки) | f4bd66b |
| AC-06 | PASS | `e2e_figma.py`: skip link, один h1, landmarks, lang=de, меню (ловушка/Esc/фокус назад/scroll-lock), лайтбокс, слайдер с клавиатуры, фокус-кольцо, reduced-motion, печать, «STRASSENBAU»; Lighthouse Accessibility 100 на 8 замерах | f4bd66b |
| AC-07 | PASS (с оговоркой) | Lighthouse 13.5 (`_refs/shots/lighthouse/`): все категории ≥ 95 на 8 замерах; LCP < 2.5 s везде, кроме разброса главной mobile: 2.41 / 2.43 / 2.56 s в трёх прогонах (медиана 2.43 s, сохранена как `home-mobile.json`); CLS 0 | f4bd66b |
| AC-08 | PASS | `e2e_figma.py`: title, description, canonical, og:image (файл существует), JSON-LD валиден, noindex Danke/404, `sitemap.xml` = 12 URL | f4bd66b |
| AC-09 | PASS | `python3 _refs/tools/legal_textcheck.py`: Impressum 397/397, Datenschutz 5117/5117, Gewährleistung 200/200, Widerruf 24/24 слов, 0 расхождений; «Anna Beispiel», «anna@beispiel», «25+», «100+» → 0; негативный тест ловит подмену слова | f14075e |
| AC-10 | PASS (Apache NOT RUN) | curl к роутеру: `/storage/`, `/storage/submissions.sqlite`, `/storage/mail.log`, `/server/config.local.php`, `/server/bin/submissions.php`, `/build.py`, `/_refs/`, `/docs/`, `/tests/php/run.php`, `/src/layout.html`, `/.git/HEAD` → 404; `git ls-files` без config.local/sqlite/log; `SMTP_PASS` не задан; `.htaccess` проверен ревью (RewriteRule 404 для server/storage/docs/tests, FilesMatch для sqlite/log/config.local); Apache локально не установлен | f4bd66b |
| AC-11 | PASS | `/code-review high` по `master...figma-2026`: 9 находок (6 корректность, 1 согласованность, 1 UI-состояние, 1 архитектура) → все исправлены и перепроверены (R-28) | f4bd66b |
| AC-12 | PASS | сервер `wahl-php` запущен, `curl -sI http://localhost:5178/` → 200; README, CLAUDE.md, KUNDENFRAGEN, report обновлены | P-11 |

## Страницы, фреймы Figma и URL
| # | Страница | URL | Desktop / Tablet / Mobile | Δ высоты 1440 / 1024 / 390 |
|---|---|---|---|---|
| 01 | Startseite | `/` | 8:2 / 8:485 / 8:925 | −0.3 / −1.1 / −1.3 % |
| 02 | Leistungen | `/leistungsangebot/` | 10:390 / 10:653 / 10:939 | −0.3 / −0.8 / −0.2 % |
| 03 | Pflasterarbeiten | `/leistungsangebot/pflasterarbeiten/` | 10:1212 / 10:1436 / 10:1644 | −0.5 / +0.1 / +1.6 % |
| 04 | Garten & Landschaft | `/leistungsangebot/garten-landschaft/` | 10:1846 / 10:2079 / 10:2299 | −0.3 / +0.4 / +2.8 % |
| 05 | Technik | `/technikangebot/` | 11:956 / 11:1198 / 11:1456 | −1.0 / −1.0 / +0.2 % |
| 06 | Referenzen | `/referenzen/` | 11:1701 / 11:1954 / 11:2194 | −0.6 / −2.7 / −3.1 % |
| 07 | Kontakt | `/kontakt/` | 11:4352 / 11:4583 / 11:4801 | −1.1 / −1.4 / −2.2 % |
| 07F | Kontakt – Fehler | `/kontakt/` (после отправки) | 37:2 / 37:331 / 37:611 | −1.2 / −1.5 / −2.2 % |
| 08 | Danke | `/kontakt/danke/` | 11:5013 / 11:5200 / 11:5376 | −0.8 / −0.8 / +0.8 % |
| 09 | Impressum | `/about/` | 12:1781 / 12:1968 / 12:2168 | −0.6 / −1.7 / −1.9 % |
| 10 | Datenschutz | `/j/privacy/` | 14:2264 / 14:2563 / 14:2853 | −1.2 / −1.9 / −0.7 % |
| 11 | Gewährleistung | `/j/legal-guarantee/` | 12:2353 / 12:2544 / 12:2719 | −1.2 / −0.7 / −0.7 % |
| 12 | Widerruf | `/j/withdrawal/` | 12:2888 / 12:3066 / 12:3233 | −0.9 / −0.6 / −1.3 % |
| 13 | Sitemap | `/sitemap/` | 12:3394 / 12:3573 / 12:3741 | −1.7 / −0.7 / −1.0 % |
| 14 | 404 | `/404.html` | 11:5546 / 11:5674 / 11:5791 | −1.8 / −0.2 / −0.6 % |
| M | Menü | (кнопка меню) | — / 17:7074 / 18:5256 | — / −3.0 / 0.0 % (высота экрана) |

Пары скриншотов: `_refs/shots/figma-compare/<NN>-<ширина>.png` (слева Figma 1:1, справа сайт). Δ — разница полной высоты страницы.

## Lighthouse (локальный роутер с gzip, Lighthouse 13.5, `_refs/shots/lighthouse/`)
| Страница | Mobile: Perf / A11y / BP / SEO · LCP | Desktop: Perf / A11y / BP / SEO · LCP |
|---|---|---|
| `/` | 97 / 100 / 100 / 100 · 2.43 s (3 прогона: 2.41–2.56 s) | 100 / 100 / 100 / 100 · 0.65 s |
| `/referenzen/` | 98 / 100 / 100 / 100 · 2.48 s | 99 / 100 / 100 / 100 · 0.86 s |
| `/kontakt/` | 100 / 100 / 100 / 100 · 1.43 s | 100 / 100 / 100 / 100 · 0.34 s |
| `/j/privacy/` | 100 / 100 / 100 / 100 · 1.58 s | 100 / 100 / 100 / 100 · 0.41 s |

CLS = 0 везде. LCP главной mobile на границе 2.5 s: на хостинге с HTTP/2 и кэшем ожидаемо быстрее, но это не измерено (NOT RUN).

## Тексты-предложения (TEXTVORSCHLAG, утвердить у заказчика)
Помечены в `src/` комментарием `<!-- TEXTVORSCHLAG: vom Kunden freigeben -->`:
- Текст согласия в формах (Einwilligung) и подсказка «Es gilt die Datenschutzerklärung …» — `build.py` (форма kontakt, kurz).
- Тексты ошибок форм и сводки (`server/messages.json`), в т. ч. новый текст о превышении длины (R-23).
- Eyebrow/заголовки CTA-полос «Nächster Schritt» + «Projekt geplant?», «Pflasterarbeiten planen?», «Garten planen?», «Einsatz planen?», «Ihr Projekt als nächste Referenz?» — `build.py` (`cta_html`).
- «Havarie-Hotline» (Emergency band) — `build.py`.
- «Handwerk» (Startseite, Leistungen/Spezialgebiete), «Weitere Arbeiten» (Referenzen), лид Sitemap.
- Шаги «So arbeiten wir» (Pflasterarbeiten), «So entsteht Ihr Garten» (Garten & Landschaft), «So geht es jetzt weiter» (Danke).
- Подписи галерей (Pflasterarbeiten, Garten & Landschaft).
- Блоки «Fragen zu diesen Angaben? / zur Gewährleistung? / zum Datenschutz?» на юр. страницах.
- Подтверждение Widerruf (D-05), включая вариант при неотправленной Eingangsbestätigung.

## Не проверено (NOT RUN) и причины
| Что | Причина |
|---|---|
| Apache-правила `.htaccess` в работе | Apache локально не установлен (D-09); правила проверены ревью, роутер повторяет запреты (AC-10) |
| Реальный SMTP/`mail()` у хостера | хостинг не выбран (KUNDENFRAGEN C1/C2); SMTP проверен против фейкового сервера, реальная отправка запрещена задачей |
| Firefox | не установлен (D-09); проверены Chrome (Playwright) и WebKit/Safari-движок (Playwright, 390 px, 14 URL) |
| Lighthouse на реальном хостинге | нет деплоя |
| Юридическая корректность текстов | вне компетенции и задачи (блокер публикации, KUNDENFRAGEN A) |

## Как перепроверить
```bash
python3 build.py && php tests/php/run.php && python3 _refs/tools/legal_textcheck.py && python3 _refs/tools/dupcheck.py
```
При запущенном сервере: `python3 _refs/tools/e2e_figma.py http://localhost:5178 --webkit` и `python3 _refs/tools/figma_compare.py`.

## Отклонения и решения
| # | Фаза | Решение / отклонение | Основание |
|---|---|---|---|
| R-1 | P-00 | PNG фреймов Figma для сверки выгружены в масштабе 1:1 (`maxDimension` = высота фрейма) прямо на диск через URL; в контекст они не загружаются, просматриваются вырезками ≤ 1600 px. Мобильный Datenschutz (`14:2853`, 34 452 px) Figma ограничила 32 768 px → PNG 371 px шириной | правило «maxDimension ≤ 1600» служит экономии контекста; для сверки с допуском 8 px нужен масштаб 1:1 |
| R-2 | P-00 | В метаданных 382 слоя с «→» (desktop 126, tablet 128, mobile 128): маршруты внутри инстансов Header/Footer/Menü в метаданные не попадают и проверяются по компонентам | `get_metadata` не раскрывает инстансы |
| R-3 | P-03 | В tablet/mobile-фреймах Figma фото в карточках услуг и референсов не отрисованы (пустые тёмные блоки; на desktop фото есть). На сайте фото показаны на всех ширинах | spec §4.5 «только настоящие фото»; фото из desktop-фрейма того же компонента |
| R-4 | P-03 | Карточки в ряду одинаковой высоты (ссылка прижата к низу), в Figma высота карточек разная | spec §4.5 (поведение по spec) |
| R-5 | P-03 | Правило «одна Primary на экран» проверяется без шапки: в Figma шапка (CTA) и Hero/форма показывают вторую Primary на одном экране | макет Figma (вид — по Figma) |
| R-6 | P-03 | Placeholder полей — warm-white 60 % (в Figma текст placeholder ярче) | DESIGN.md §2, контраст WCAG |
| R-7 | P-03 | Ссылка «Datenschutzerklärung» в подсказке и в тексте согласия подчёркнута (в Figma не выделена) | WCAG 1.4.1: ссылка не только цветом |
| R-8 | P-03 | Подписи кнопок, различающиеся по брейкпоинтам в Figma («Pflasterarbeiten ansehen» / «Mehr erfahren», «Gesamten Maschinenpark ansehen» / «Maschinenpark ansehen»), выводятся по брейкпоинтам | Figma |
| R-9 | P-03 | Ссылки чипов «Außerdem» и карточки «Mosaik & Logopflasterung» ведут на якоря страницы Leistungen (`#erdbauarbeiten`, `#havarie`, `#spezialgebiete` …), в Figma цель — страница Leistungen | точнее для пользователя, цель та же |
| R-10 | P-04 | Регулятор слайдера до/после — жёлтый круг 48 px (радиус 24), как в Figma `36:150`, хотя DESIGN.md ограничивает радиусы 2 px | вид — по Figma |
| R-11 | P-04 | Кадрирование фото повторяет `CROP` Figma через `object-position` и `transform: scale()` (параметр `zoom` хелпера `{{photo}}`); на mobile/tablet используется тот же фокус | Figma (кадрирование hero) |
| R-12 | P-04 | Хлебные крошки на mobile не переносятся (как в Figma, где строка шире 350 px), а прокручиваются по горизонтали внутри своей строки — без горизонтального скролла страницы | Figma + R-01 (без горизонтального скролла) |
| R-13 | P-05 | Ошибка согласия (Consent Error 7:602) без видимого текста под чекбоксом, как в Figma; текст ошибки доступен скринридерам (`sr-only`) и через сводку | Figma + WCAG 3.3.1 |
| R-14 | P-05 | Проверка поля при уходе фокуса включается только после первой попытки отправки (иначе сообщение сдвигает кнопку под курсором) | поведение (spec §5) + UX |
| R-15 | P-05 | Сводка ошибок перечисляет поля ссылками («3 Pflichtfelder fehlen oder sind ungültig: Name, E-Mail, Nachricht. Außerdem ist die Einwilligung erforderlich.»), формулировка — по 07F | spec §5 |
| R-16 | P-06 | Юр. тексты: только разметка. Datenschutz: нумерованные `h3` → `h2` (17 пунктов TOC как в Figma), `h4` → `h3`; Impressum: добавлен заголовок «Angaben zum Unternehmen», реквизиты в виде таблицы `dl` (двоеточия сохранены в тексте для скринридеров); Gewährleistung: добавлены 4 заголовка по Figma, первая фраза — в лиде hero, перечисления — списками; Widerruf: текст распределён по lead и инфоплиткам. `legal_textcheck.py` → 0 расхождений | spec R-08.3 |
| R-17 | P-06 | QR-код Gewährleistung — SVG из Figma (`26:11691`), проверен декодированием (BarcodeDetector) → `https://europa.eu/youreurope/garantien` | spec §3 п. 11 |
| R-18 | P-06 | Мобильный TOC («Inhalt · N Abschnitte») раскрыт по умолчанию, как в mobile/tablet-фреймах Figma; на desktop — sticky-колонка 300 px со scroll-spy | Figma |
| R-19 | P-06 | Длинные слова в заголовках (`Datenschutzerklärung`) переносятся без дефиса (`overflow-wrap: break-word`), как в mobile-фрейме Figma; автоматическая расстановка переносов отключена (она делила «STRAS-SENBAU», найдено на финальном скриншоте P-11); на 320 px уменьшены логотип и 24/7-номер — горизонтального скролла нет на 320–1920 px | R-01 |
| R-20 | P-07 | Единый источник текстов форм — `server/messages.json` (читают `build.py` и `Validator.php`); тест проверяет совпадение текстов и списка услуг | ADR-0001 п. 2 |
| R-21 | P-07 | Widerruf без JS: сервер отвечает страницей подтверждения (200) вместо 303 на Danke — по D-05 (конкретнее, чем R-05.7) | spec D-05 |
| R-22 | P-07 | Запрос без Origin и без Referer не блокируется (строгие настройки приватности); чужой Origin или Referer → 403 | ADR-0001 угрозы (CSRF) |
| R-23 | P-07 | Сообщение 422 при превышении длины поля («Bitte kürzen Sie Ihre Eingabe auf höchstens N Zeichen.») — новый текст, в Figma нет; клиент предотвращает через `maxlength` | R-05.3; TEXTVORSCHLAG |
| R-24 | P-09 | Фото в карточках-ссылках (Service card) — `alt=""` (декоративные: заголовок карточки уже называет ссылку); фото с самостоятельным смыслом (hero, референсы, галереи, команда) — alt из таблицы 39:2 | WCAG 1.1.1, избежание дублирования |
| R-25 | P-09 | Правило повторов фото взято из фреймов Figma (таблица 39:2 перечисляет не все использования, напр. «weg» в карточке Pflasterarbeiten на Startseite/Danke) | spec R-08.5 |
| R-26 | P-10 | Добавлены варианты фото 960 px (`*-960.avif/webp`, те же настройки cwebp -q 82 / avifenc -q 60, из полноразмерного WebP) — на mobile (DPR ≈ 1.75) hero больше не грузит 1280 px; LCP mobile главной 3.76 → 2.43 s | R-10 (LCP < 2.5 s) |
| R-27 | P-10 | Локальный роутер отдаёт HTML/CSS/JS/SVG со сжатием gzip, как `mod_deflate` в `.htaccess` продакшна (иначе Lighthouse мерил несжатые 48 + 60 КБ) | R-07.3, сопоставимость замеров |
| R-28 | P-10 | По итогам `/code-review high` (9 находок, все исправлены): тело письма quoted-printable (строки > 998 символов), `t` = секунды с загрузки страницы (не зависит от часов клиента), отказ SQLite не теряет заявку (письмо уходит), `CLIENT_IP_HEADER` для работы за прокси/CDN, `Origin: null` → проверка Referer, сбой письма-подтверждения Widerruf показывается пользователю, единые тексты для пустых полей, шаблон подтверждения Widerruf генерирует build.py | AC-11 |
| R-29 | P-10 | Регрессия, найденная полным прогоном `figma_compare.py`: правило подвала для 320 px перебивало десктопную сетку (+670 px на всех страницах 1440) — ограничено mobile; повторный прогон Δ −0.2…−2.7 % | AC-02 |
