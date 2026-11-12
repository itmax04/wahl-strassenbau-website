# Спецификация WEB-2026: сайт Wahl Straßenbau по Figma 2026

| Поле | Значение |
|---|---|
| Статус | **draft** (владелец переводит в `accepted`; после этого любое изменение требований — новая версия и повторное согласование) |
| Версия / дата | 0.1 · 2026-10-02 |
| Основание | [intent.md](intent.md) |
| Решения | [ADR-0001 backend форм](../../decisions/ADR-0001-forms-backend.md) |
| Реализация | [plan.md](plan.md) |
| Дизайн-токены | [DESIGN.md](../../../DESIGN.md) (производное от Figma Variables) |
| Figma | `RftFK0Bf5MXWspQfaAshIj`, «Wahl Straßenbau — Website 2026», проверено 2026-10-02 через Figma MCP |

> Этот файл — **единственный источник требований** WEB-2026. `PROMPT-FOR-DEVELOPER.md` из handoff-папки
> (`~/Documents/Codex/2026-09-29/pdf-imagegen-x20/outputs/wahl-figma-handoff/`) — исходный материал. Его нормы перенесены сюда
> и в DESIGN.md. Если handoff и этот документ расходятся, действует этот документ.

---

## 1. Источники истины и приоритет

| Что | Источник | Примечание |
|---|---|---|
| Внешний вид, вёрстка, состояния, маршруты | Figma (страницы 00–05) | node-id в §3 |
| Токены (цвет, шрифт, отступы, радиусы) | Figma Variables → `DESIGN.md` | при расхождении побеждает Figma; DESIGN.md исправить |
| Факты о компании | `CONTENT.md`; `BRIEF-FOR-FIGMA.md` (раздел «Проверенные данные»); `content-extracts/*.txt` | новые факты не добавлять |
| Юридические тексты | `src/pages/{impressum,datenschutz,gewaehrleistung,widerruf}.html` на `master@1ebca29` | дословно (§8) |
| Фото и alt-тексты | `assets/photos/` + таблица «Fotos & Alt-Texte» (Figma `39:2`) | только 15 существующих кадров |
| Поведение backend | ADR-0001 + §6 | |
| Требования | этот файл | |

Правило конфликтов: **вид — по Figma, факты — по CONTENT/legal, поведение — по spec**. Каждое найденное противоречие
исполнитель записывает в `report.md` (раздел «Отклонения и решения») и продолжает работу по этому правилу.

## 2. Брейкпоинты и сетка (R-01)
- Mobile ≤ 767 px (макет 390), Tablet 768–1279 px (макет 1024), Desktop ≥ 1280 px (макет 1440).
- Контент: desktop max 1280, поля 80, 12 колонок, gutter 24 · tablet поля 48, 8 колонок, gutter 24 · mobile поля 20, 4 колонки, gutter 16.
- Ширина 1280 вместо 1200 из брифа выбрана сознательно: иначе не помещается шапка.
- Между опорными ширинами размеры шрифтов масштабируются через `clamp()`. Без горизонтального скролла на 320–1920 px.

## 3. Карта страниц (R-02)

URL, файлы и навигационные ключи сохраняются, как в `build.py → PAGES`. «Über uns» — якорь `/#ueber-uns` на главной.

| # | Страница | URL | `src/pages` | Desktop | Tablet | Mobile | Proto D / M |
|---|---|---|---|---|---|---|---|
| 01 | Startseite | `/` | index | `8:2` | `8:485` | `8:925` | `38:13470` / `38:14452` |
| 02 | Leistungen | `/leistungsangebot/` | leistungen | `10:390` | `10:653` | `10:939` | `38:13577` / `38:14559` |
| 03 | Pflasterarbeiten | `/leistungsangebot/pflasterarbeiten/` | pflasterarbeiten | `10:1212` | `10:1436` | `10:1644` | `38:13638` / `38:14620` |
| 04 | Garten & Landschaft | `/leistungsangebot/garten-landschaft/` | garten-landschaft | `10:1846` | `10:2079` | `10:2299` | `38:13684` / `38:14666` |
| 05 | Technik | `/technikangebot/` | technik | `11:956` | `11:1198` | `11:1456` | `38:13731` / `38:14713` |
| 06 | Referenzen | `/referenzen/` | referenzen | `11:1701` | `11:1954` | `11:2194` | `38:13796` / `38:14778` |
| 07 | Kontakt | `/kontakt/` | kontakt | `11:4352` | `11:4583` | `11:4801` | `38:13860` / `38:14841` |
| 07F | Kontakt – Fehler (состояние) | `/kontakt/` | — | `37:2` | `37:331` | `37:611` | `38:14393` / `38:15379` |
| 08 | Danke | `/kontakt/danke/` | danke | `11:5013` | `11:5200` | `11:5376` | `38:13914` / `38:14895` |
| 09 | Impressum | `/about/` | impressum | `12:1781` | `12:1968` | `12:2168` | `38:13960` / `38:14941` |
| 10 | Datenschutz | `/j/privacy/` | datenschutz | `14:2264` | `14:2563` | `14:2853` | `38:14211` / `38:15195` |
| 11 | Gewährleistung | `/j/legal-guarantee/` | gewaehrleistung | `12:2353` | `12:2544` | `12:2719` | `38:14036` / `38:15019` |
| 12 | Widerruf | `/j/withdrawal/` | widerruf | `12:2888` | `12:3066` | `12:3233` | `38:14110` / `38:15094` |
| 13 | Sitemap | `/sitemap/` | sitemap | `12:3394` | `12:3573` | `12:3741` | `38:14150` / `38:15134` |
| 14 | 404 | `/404.html` | 404 | `11:5546` | `11:5674` | `11:5791` | `38:13942` / `38:14923` |
| M | Menü (mobile/tablet) | — | layout | — | `17:7074` | `18:5256` | — / `38:15377` |

Страницы Figma: 00 Foundations `0:1` (токены `3:2`, фото/alt `39:2`), 01 Components `1:2`, 02 Desktop `1:3`, 03 Tablet `1:4`,
04 Mobile `1:5`, 05 Prototype `1:6` (доска «Prototype routes» `19:11360`).

Состав каждой страницы задаёт Figma: скриншот фрейма плюс `get_design_context` по секциям. Краткий перечень секций
(для контроля полноты, не вместо Figma):
1. **Startseite**: Hero (фото `weg`, «Pflaster- und Straßenbau in Rostock», Primary + Phone) · 4 метрики
   (21 Jahre Erfahrung · 18 Facharbeiter, Stand 04/2023 · 24 h Komplettservice · 2003 Meisterbrief) · светлая секция
   «Leistungen» (3 Service card + чипы «Außerdem») · фото-полоса «Natursteinpflaster nach alten Handwerksregeln» · Emergency band ·
   «Unsere Technik» (6 метрик + ссылка) · «Referenzen» (3 карточки + строка заказчиков) · «Über uns» (`id="ueber-uns"`, фото команды,
   таймлайн) · «Kontakt» + Kurzanfrage · Footer.
2. **Leistungen**: Hero `segmentbogen` · 9 нумерованных услуг · Emergency band · Spezialgebiete + плитка `logo-hammer` · «Einblicke» (2 карточки) · CTA.
3. **Pflasterarbeiten**: Hero `weg` · Verlegearten 01–06 · «So arbeiten wir» (4 шага) · галерея 2×2 · CTA.
4. **Garten & Landschaft**: Hero `rundplatz` · 6 услуг · галерея 2×2 · «So entsteht Ihr Garten» (4 шага) · CTA.
5. **Technik**: Hero (деталь `weg`) · цифры 37/14/6/17 (считаются из списка техники `build.py → TECH`, не вводятся вручную) · 3 группы техники · CTA.
6. **Referenzen**: Hero `wappen-gruen` · строка заказчиков · 3 кейса (Wappen со слайдером до/после; Logo-Mosaike; Stern im Beet) · «Weitere Arbeiten» · CTA.
7. **Kontakt**: Hero без фото (Phone + Emergency) · контактные данные · форма `kontakt` · Emergency band.
8. **Danke** (`noindex`): Hero `rundplatz`, «So geht es jetzt weiter» (3 шага), 3 карточки услуг.
9. **Impressum**, 10. **Datenschutz**, 11. **Gewährleistung** (+ QR-код SVG на `https://europa.eu/youreurope/garantien` и ссылка рядом),
   12. **Widerruf** (3 инфо-плитки + форма `widerruf`): юридические страницы с TOC (§4.8).
13. **Sitemap**: 4 группы ссылок. 14. **404** (`noindex`): «Seite nicht gefunden», Primary + 2 Secondary, телефон, фото-деталь.

## 4. Компоненты и поведение (R-03)
Все компоненты — из страницы 01 Components (`1:2`), со всеми вариантами. Ниже перечислено то, чего не видно на статичных макетах.

1. **Header** (`6:266`): fixed. Desktop 88 px (лого, навигация Leistungen/Technik/Referenzen/Über uns/Kontakt, телефон
   `0381 25 22 39 41`, Primary «Angebot anfragen»). Tablet 80 px (лого, иконка-телефон, Primary, бургер). Mobile 64 px
   (лого, жёлтая кнопка-телефон 48×48, бургер). После прокрутки > 8 px — вариант Sticky (76 / 68 / 64, фон charcoal 96 %,
   тень `0 8px 24px rgba(0,0,0,.45)`). Активный пункт: `aria-current="page"` + жёлтая линия 2 px. `scroll-margin-top`
   у якорей = высота шапки + 16.
2. **Mobile menu** (`6:437`; фреймы Menü): полноэкранная панель (Startseite, Leistungen → Pflasterarbeiten, Garten & Landschaft,
   Technik, Referenzen, Über uns, Kontakt; внизу Emergency «24/7 Havarie: 0381 25 22 39 41», Primary, строки Mobil/E-Mail).
   `aria-expanded`, `aria-controls`, фокус-ловушка, Esc и «Schließen» закрывают меню, прокрутка страницы блокируется,
   фокус возвращается на кнопку.
3. **Button** (`4:374`): типы Primary / Secondary / Phone / Emergency / Link × состояния Default / Hover / Focus / Disabled × L 56 / M 48.
   Минимальная цель касания 48×48. **Не больше одной Primary на экран.** Emergency визуально отличается от Primary.
4. **Section heading** (`6:650`): eyebrow → заголовок → жёлтая линия 48×3 → intro.
5. **Service card** (`7:342`) и **Reference card** (`7:406`): вся карточка — одна ссылка, hover — жёлтая рамка 1.5 px,
   карточки в ряду одинаковой высоты, только настоящие фото.
6. **Metric item** (`7:421`), **Emergency band** (`7:478`, кнопка `tel:`), **Timeline** (`7:665`), **Process step** (`7:668`),
   **Chip** (`7:676`), **Equipment row** (`7:678`), **Breadcrumb** (`6:663`, уровни 2/3), **Footer** (`6:632`) — как в макете.
   Копирайт в футере: `© {текущий год сборки} Wahl Straßenbau GmbH & Co. KG · USt-IdNr. DE 294 970 751`.
7. **Gallery tile** (`7:628`) открывает лайтбокс на нативном `<dialog>`: стрелки, Esc, свайп, фокус возвращается на плитку.
   **Vorher/Nachher-Slider**: `<input type="range">` поверх двух изображений с `clip-path`, управляется с клавиатуры,
   `aria-label="Vergleich: Wappenmosaik fertig und während der Verlegung"`.
8. **Legal TOC** (`7:635`, `7:660`): на desktop sticky-колонка 300 px со scroll-spy и активным пунктом с жёлтой линией слева.
   На tablet и mobile — список «INHALT · N ABSCHNITTE» над текстом (раскрывается, как в `7:660`). Ссылки — якоря на заголовки.
9. **«Nach oben»**: жёлтая кнопка 48×48, появляется после прокрутки > 600 px. Показывается на Datenschutz (все брейкпоинты),
   Impressum и Gewährleistung (tablet и mobile).
10. **Иконки**: линейные SVG из `Icon / *` (24 px, штрих 1.75), спрайт или inline. У декоративных — `aria-hidden="true"`.
11. **Hero-фото**: `object-fit: cover`, градиентное затемнение и кадрирование по фрейму (значения брать из `get_design_context`).
12. **Анимации**: только существующие значения kinetics из `styles.css` (Underline Draw, Stagger Entrance, Clip Wipe, Number Counter)
    там, где они не противоречат макету. Новые кривые и пружины не придумывать. При `prefers-reduced-motion: reduce` анимации
    и плавный скролл отключены.

## 5. Формы: клиент (R-04)
Разметку и тексты форм генерирует `build.py` (`form_html`) — это единственное место. Тексты ошибок те же, что на сервере (ADR-0001).

| Форма | Где | Поля (`name`) | Обязательно |
|---|---|---|---|
| `kontakt` | /kontakt/ | `name`, `email`, `telefon`, `leistung` (select из `SERVICES`), `nachricht`, `einwilligung` | name, email, nachricht, einwilligung |
| `kurz` | / (#kontakt) | `name`, `telefon`, `nachricht` (label «Anliegen»), `einwilligung` | все |
| `widerruf` | /j/withdrawal/ | `name`, `bestellnummer`, `email`, `artikel`, `nachricht` (Grund) | name, bestellnummer, email |

Служебные поля во всех формах: `form`, honeypot `website` (скрыт от людей и ассистивных технологий), `t` (время загрузки, ставит JS).

Состояния (по `7:589`, `7:605` и фрейму 07F):
- Поле: Default / Focus (жёлтая рамка 2 px + кольцо) / Filled / Error (рамка error, иконка, текст под полем, `aria-invalid`,
  `aria-describedby`) / Success (рамка success с галочкой).
- После неудачной отправки над формой появляется **сводка ошибок** (`role="alert"`, получает фокус, ссылки на поля).
  Тексты — из фрейма 07F: «Bitte prüfen Sie die markierten Felder.» и строка с перечнем полей.
- Тексты ошибок полей: из 07F и компонентов (например, «Bitte geben Sie eine gültige E-Mail-Adresse ein.», «Bitte beschreiben Sie
  kurz Ihr Anliegen.»; для пустого обязательного поля — «Bitte füllen Sie dieses Pflichtfeld aus.»). Точная формулировка берётся
  из слоёв Figma. Существующие тексты в `kontakt.php` заменяются текстами Figma.
- Отправка: кнопка disabled + индикатор, повторный клик игнорируется. Сетевая ошибка — общая ошибка с телефоном.
- Успех `kontakt` / `kurz`: переход на `/kontakt/danke/`. Успех `widerruf`: см. D-05.
- Демо-значения из макета («Anna Beispiel», «anna@beispiel») в код **не переносить**; placeholder-тексты брать из Figma.
- Без JS все формы работают: обычный POST, ответ сервера (ADR-0001 п. 4).

## 6. Формы: сервер и данные (R-05, R-06)
Архитектура, файлы и угрозы описаны в ADR-0001. Нормы:
- R-05.1 `POST /kontakt.php`; другие методы → 405.
- R-05.2 Проверки по порядку: Origin/Referer → honeypot (тихий успех) → `t` < `MIN_FILL_SECONDS` (тихий успех) → rate limit (429) → валидация (422).
- R-05.3 Серверная валидация не слабее клиентской. Длины: name 100, email 200, telefon 40, leistung из списка, nachricht 5000,
  bestellnummer 100, artikel 300. CR/LF в однострочных полях удаляются.
- R-05.4 `einwilligung` обязательно для `kontakt` и `kurz`. В БД сохраняется `consent_at` (время), а не текст.
- R-05.5 Валидная заявка → строка в SQLite → письмо владельцу (`RECIPIENT`, Reply-To = email отправителя, если он есть) →
  для `widerruf` письмо-подтверждение отправителю (текст из текущего `kontakt.php`). `mail_status` фиксируется.
- R-05.6 Сбой транспорта: заявка сохранена, пользователю показывается ошибка с телефоном, HTTP 502 для JSON.
- R-05.7 Ответы: JSON (`{ok, errors, error}`) или без JS — 303 на успех / HTML-страница ошибки со значениями (экранированными).
- R-06.1 Ретеншен: строки старше `RETENTION_DAYS` (по умолчанию **90**) удаляются при каждой записи и командой `purge`.
- R-06.2 Rate limit: по умолчанию 5 отправок за 10 минут с одного ключа `sha256(IP + суточная соль)`. Сырой IP не хранится.
- R-06.3 Транспорт по умолчанию — `log`. Локально реальные письма не отправляются.
- R-06.4 `storage/`, `server/`, `*.sqlite`, `*.log`, `config.local.php` недоступны по HTTP (Apache `.htaccess` и локальный роутер).
- R-06.5 Секреты только в `server/config.local.php` или env. Файл в `.gitignore`, в репозитории лежит `config.example.php`.
- R-06.6 CLI `php server/bin/submissions.php list|export|purge` работает только из командной строки (`PHP_SAPI === 'cli'`).

## 7. Локальный запуск (R-07)
- R-07.1 Одна команда из корня репозитория: `python3 build.py && php -S localhost:5178 server/router.php`. Транспорт `log`,
  заявки в `storage/`.
- R-07.2 В `~/Desktop/1/.claude/launch.json` добавляется конфигурация `wahl-php` (порт 5178, PHP-роутер). Старая `wahl-preview` остаётся.
- R-07.3 Роутер отдаёт статику с корректными MIME-типами (в т. ч. avif/woff2), `index.html` для каталогов, `/404.html` со статусом 404.

## 8. Контент (R-08)
- R-08.1 Факты только из источников §1. Демо-цифры генеративных референсов («25+», «100+») запрещены.
- R-08.2 «18 Facharbeiter im Team» всегда с пометкой «Stand 04/2023». «21 Jahre Erfahrung» вычисляется при сборке от мая 2005
  (на 2026-10-02 = 21); копирайт-год — от даты сборки.
- R-08.3 Юридические тексты (Impressum, Datenschutz, Gewährleistung, Widerruf) переносятся **дословно** из `master@1ebca29`.
  Разрешено только добавлять подзаголовки, якоря и TOC. Смысловые правки запрещены, расхождения идут в `docs/KUNDENFRAGEN.md`.
- R-08.4 Тексты из макета, не подтверждённые заказчиком (шаги процесса, «So geht es jetzt weiter», текст согласия, тексты ошибок,
  eyebrow вроде «Nächster Schritt», «Havarie-Hotline», «Weitere Arbeiten», «Handwerk», подписи галерей, лид Sitemap),
  помечаются в `src` комментарием `<!-- TEXTVORSCHLAG: vom Kunden freigeben -->` и собираются в отчёт.
- R-08.5 Alt-тексты на немецком — из таблицы `39:2` или имён слоёв `Foto: …`. Повторы фото между страницами — только как в макете;
  `_refs/tools/dupcheck.py` обновляется под макет.

## 9. Качество (R-09 … R-11)
- R-09 **Доступность (WCAG 2.2 AA)**: `lang="de"`, skip link «Zum Inhalt springen», landmarks, ровно один `h1` на странице,
  видимый `:focus-visible` (кольцо `0 0 0 4px rgba(244,196,49,.35)` + outline), контраст текста ≥ 4.5:1 (stone-gray не используется
  на `#232423`; placeholder — warm-white 60 %), цели ≥ 48 px, работа с клавиатуры, reduced-motion. `ß` → `SS` в верхнем регистре проверяется
  («STRASSENBAU»).
- R-10 **Производительность**: Lighthouse mobile ≥ 90 во всех категориях; LCP < 2.5 s; CLS < 0.1; шрифты локальные,
  `font-display: swap`, preload Anton и Inter; hero — `fetchpriority="high"`, остальные изображения lazy; никакого стороннего JS и трекеров.
- R-11 **SEO**: title и description страниц сохраняются; canonical и OG на `SITE` из `build.py`; OG-картинки; `sitemap.xml`; JSON-LD
  LocalBusiness + BreadcrumbList; `noindex` на Danke и 404; `robots.txt` без изменений по смыслу.
- R-12 **Печать**: юридические страницы печатаются без шапки, меню и кнопок (сохранить поведение текущего `@media print`).

## 10. Критерии приёмки

| AC | Требования | Проверка (метод → ожидаемое свидетельство) | План |
|---|---|---|---|
| AC-01 | R-02, R-07 | `python3 build.py` без ошибок; краулер (`_refs/tools/e2e_figma.py`, новый) по 14 URL → 200; несуществующий URL → 404 с телом `/404.html` | P-03…P-06, P-10 |
| AC-02 | R-01, R-03, R-02 | для 16 состояний (14 страниц + 07F + Menü) × 3 ширины: скриншот сайта и PNG фрейма Figma рядом в `_refs/shots/figma-compare/`; отступы ≤ 8 px, типографика, цвета и кадрирование как в макете; отклонения с причиной в report | P-03…P-06, P-10 |
| AC-03 | R-01 | Playwright на 320, 390, 768, 1024, 1280, 1440, 1920: `scrollWidth ≤ clientWidth` на всех URL | P-10 |
| AC-04 | R-03 | из метаданных Figma `1:3`, `1:4`, `1:5` извлечены все слои «… → цель» (`_refs/figma/routes.json`, новый, ≈126); для каждого есть соответствующий `href` или действие на странице; 0 несоответствий | P-02, P-10 |
| AC-05 | R-04, R-05, R-06 | `php tests/php/run.php` (новый, без зависимостей): валидное / невалидное / honeypot / быстро / rate limit / чужой Origin / CRLF / XSS / SQL-кавычки / сбой транспорта / purge / SMTP против фейкового сервера → все PASS; Playwright: состояния как в 07F, сводка с фокусом, отправка без JS (JS выключен), успех → Danke | P-07, P-08, P-10 |
| AC-06 | R-09, R-12 | Playwright: skip link, один h1, landmarks, клавиатура по меню, лайтбоксу и слайдеру, фокус-ловушка, Esc, reduced-motion, «STRASSENBAU»; Lighthouse Accessibility ≥ 95 | P-08, P-10 |
| AC-07 | R-10 | `lighthouse` mobile и desktop для `/`, `/referenzen/`, `/kontakt/`, `/j/privacy/` → JSON-отчёты в `_refs/shots/lighthouse/`; все категории ≥ 90, LCP < 2.5 s, CLS < 0.1 | P-10 |
| AC-08 | R-11 | скрипт проверяет на каждом URL title, description, canonical, og:image, JSON-LD (валидный JSON), noindex для Danke/404; `sitemap.xml` содержит 12 индексируемых URL | P-09, P-10 |
| AC-09 | R-08 | нормализованное сравнение текста юридических страниц с `git show master:src/pages/<file>.html` (без тегов и пробелов) → совпадение, кроме добавленных заголовков и якорей; `grep` на «Anna Beispiel», «25+», «100+» → 0; список TEXTVORSCHLAG в report | P-06, P-10 |
| AC-10 | R-06.4, R-06.5 | curl к локальному роутеру: `/storage/`, `/server/config.local.php`, `/storage/submissions.sqlite`, `/storage/mail.log`, `/build.py`, `/_refs/` → 404; `git ls-files` не содержит `config.local.php`, `*.sqlite`, `*.log`; `.htaccess` проверен review (**Apache локально NOT RUN**) | P-07, P-10 |
| AC-11 | все | `/code-review high` по диффу `master...figma-2026`: находки P0/P1 исправлены или обоснованно отклонены, остальное — в report | P-10 |
| AC-12 | R-07 | сервер запущен, `curl -sI http://localhost:5178/` → 200; ссылка выдана пользователю; `report.md`, README, CLAUDE.md, KUNDENFRAGEN обновлены | P-11 |

Статусы в отчёте: `PASS | FAIL | BLOCKED | NOT RUN`, у каждого — команда, коммит и причина для NOT RUN.

## 11. Решения и допущения

| ID | Тип | Содержание |
|---|---|---|
| D-01 | решение владельца | тот же репозиторий, ветка `figma-2026`; стек прежний (статика + `build.py` + PHP) |
| D-02 | решение владельца | backend: формы + SQLite без админки; транспорт `log/mail/smtp`; ретеншен 90 дней |
| D-03 | решение владельца | юридические тексты дословно; расхождения → KUNDENFRAGEN (блокер публикации, не разработки) |
| D-04 | решение владельца | цифры как в Figma, с датой актуальности |
| D-05 | допущение исполнителя | успех `widerruf`: с JS форма заменяется подтверждением в той же панели; без JS сервер отдаёт страницу подтверждения в стиле сайта; текст подтверждения — TEXTVORSCHLAG |
| D-06 | допущение | пара `wappen-gruen` / `wappen-bau` — один объект «до/после» (как в Figma), в KUNDENFRAGEN |
| D-07 | допущение | на фото `logo-mosaik`, `stier-ziegel`, `stiere-bau` видны товарные знаки Red Bull; фото используются, как в Figma, вопрос в KUNDENFRAGEN |
| D-08 | решение | Danke и 404 не индексируются; `/kontakt/danke/` открывается и напрямую (статическая страница) |
| D-09 | факт среды | Firefox и Apache локально не установлены → кросс-браузер: Chrome + Safari (WebKit Playwright, если устанавливается локально), Firefox NOT RUN |
| D-10 | решение | 21st.dev и внешние DESIGN.md не используются: Figma — дизайн-система проекта (приоритет 1 глобальных правил) |

## 12. Не входит (см. intent)
Деплой, хостинг, DNS, реальная почта, админка, CMS, правка юр. смысла, новые фото и факты, аналитика, изменения Figma, push/merge.
Изменение любого из этих пунктов — новый intent.

## 13. Открытые вопросы
Не блокируют разработку. Ведутся в [docs/KUNDENFRAGEN.md](../../KUNDENFRAGEN.md); исполнитель дополняет список.
