<?php
declare(strict_types=1);

/**
 * Backend-Tests ohne Abhängigkeiten (WEB-2026 AC-05, ADR-0001): php tests/php/run.php
 * Startet eigene `php -S`-Instanzen auf freien Ports mit temporärem STORAGE_PATH und MAIL_TRANSPORT=log
 * (bzw. smtp gegen tests/php/fake_smtp.php) und prüft Antworten, Datenbank und Mail-Protokoll.
 * Exit-Code 0 = alle Tests bestanden.
 */

const ROOT = __DIR__ . '/../..';
$results = [];
$procs = [];

function free_port(): int
{
    $s = stream_socket_server('tcp://127.0.0.1:0');
    $name = stream_socket_get_name($s, false);
    fclose($s);
    return (int) substr($name, strrpos($name, ':') + 1);
}

function wait_port(int $port): void
{
    for ($i = 0; $i < 100; $i++) {
        $c = @fsockopen('127.0.0.1', $port, $e, $s, 0.1);
        if ($c) {
            fclose($c);
            return;
        }
        usleep(50_000);
    }
    throw new RuntimeException("Port $port nicht erreichbar");
}

function tmpdir(string $tag): string
{
    $d = sys_get_temp_dir() . '/wahl-test-' . $tag . '-' . bin2hex(random_bytes(4));
    mkdir($d, 0700, true);
    return $d;
}

/** Startet php -S mit Router und Umgebung; Rückgabe [port, storage]. */
function start_server(array $env, string $tag): array
{
    global $procs;
    $port = free_port();
    $storage = tmpdir($tag);
    $env = array_merge(getenv(), ['MAIL_TRANSPORT' => 'log', 'STORAGE_PATH' => $storage, 'RATE_LIMIT' => '100/600', 'MIN_FILL_SECONDS' => '3'], $env);
    $cmd = [PHP_BINARY, '-S', "127.0.0.1:$port", '-t', ROOT, ROOT . '/server/router.php'];
    $p = proc_open($cmd, [0 => ['file', '/dev/null', 'r'], 1 => ['file', '/dev/null', 'w'], 2 => ['file', '/dev/null', 'w']], $pipes, ROOT, $env);
    $procs[] = $p;
    wait_port($port);
    return [$port, $storage];
}

/** HTTP-Anfrage ohne Weiterleitung; Rückgabe [status, headers(lower), body]. */
function http(int $port, string $method, string $path, array $fields = [], array $headers = []): array
{
    $headers += ['Origin' => "http://127.0.0.1:$port", 'Content-Type' => 'application/x-www-form-urlencoded'];
    $h = '';
    foreach ($headers as $k => $v) {
        if ($v !== null) {
            $h .= "$k: $v\r\n";
        }
    }
    $ctx = stream_context_create(['http' => ['method' => $method, 'header' => $h, 'content' => http_build_query($fields),
        'ignore_errors' => true, 'follow_location' => 0, 'timeout' => 20]]);
    $body = @file_get_contents("http://127.0.0.1:$port$path", false, $ctx);
    $status = 0;
    $hdrs = [];
    foreach ($http_response_header ?? [] as $line) {
        if (preg_match('#^HTTP/\S+ (\d+)#', $line, $m)) {
            $status = (int) $m[1];
        } elseif (str_contains($line, ':')) {
            [$k, $v] = explode(':', $line, 2);
            $hdrs[strtolower(trim($k))] = trim($v);
        }
    }
    return [$status, $hdrs, (string) $body];
}

function json_post(int $port, array $fields, array $headers = []): array
{
    [$s, $h, $b] = http($port, 'POST', '/kontakt.php', $fields, $headers + ['Accept' => 'application/json']);
    return [$s, json_decode($b, true) ?? [], $b];
}

function rows(string $storage): array
{
    $f = "$storage/submissions.sqlite";
    if (!is_file($f)) {
        return [];
    }
    $pdo = new PDO("sqlite:$f");
    return $pdo->query('SELECT * FROM submissions ORDER BY id')->fetchAll(PDO::FETCH_ASSOC);
}

function maillog(string $storage): string
{
    return is_file("$storage/mail.log") ? (string) file_get_contents("$storage/mail.log") : '';
}

function test(string $name, callable $fn): void
{
    global $results;
    try {
        $fn();
        $results[] = [true, $name, ''];
        echo "PASS  $name\n";
    } catch (Throwable $e) {
        $results[] = [false, $name, $e->getMessage()];
        echo "FAIL  $name — {$e->getMessage()}\n";
    }
}

function check(bool $cond, string $msg): void
{
    if (!$cond) {
        throw new RuntimeException($msg);
    }
}

$valid = ['form' => 'kontakt', 'name' => 'Erika Muster', 'email' => 'erika@beispiel.de', 'telefon' => '0381 123456',
          'leistung' => 'Pflasterarbeiten', 'nachricht' => 'Hofeinfahrt pflastern, ca. 60 m².', 'einwilligung' => 'ja', 't' => '30'];

[$port, $storage] = start_server([], 'main');

test('GET /kontakt.php → 405 mit Allow: POST', function () use ($port) {
    [$s, $h] = http($port, 'GET', '/kontakt.php');
    check($s === 405, "Status $s");
    check(($h['allow'] ?? '') === 'POST', 'Allow fehlt');
});

test('gültige Anfrage «kontakt» (JSON) → 200, Datensatz, Mail an Inhaber mit Reply-To', function () use ($port, $storage, $valid) {
    [$s, $j] = json_post($port, $valid);
    check($s === 200 && ($j['ok'] ?? false) === true, "Status $s");
    check(($j['redirect'] ?? '') === '/kontakt/danke/', 'redirect fehlt');
    $r = rows($storage);
    check(count($r) === 1, 'Zeilen: ' . count($r));
    check($r[0]['form'] === 'kontakt' && $r[0]['name'] === 'Erika Muster' && $r[0]['service'] === 'Pflasterarbeiten', 'Felder falsch');
    check($r[0]['consent_at'] !== null && $r[0]['mail_status'] === 'sent', 'consent_at/mail_status');
    $log = maillog($storage);
    check(str_contains($log, 'An: info@wahl-strassenbau.de') && str_contains($log, 'Reply-To: erika@beispiel.de'), 'Mail-Log');
    check(!str_contains(implode(' ', array_keys($r[0])), 'ip'), 'IP-Spalte vorhanden');
});

test('gültige Anfrage «kurz» → 200', function () use ($port, $storage) {
    [$s, $j] = json_post($port, ['form' => 'kurz', 'name' => 'Max', 'telefon' => '+49 172 1234567', 'nachricht' => 'Bitte Rückruf', 'einwilligung' => 'ja']);
    check($s === 200 && $j['ok'] === true, "Status $s");
    $r = rows($storage);
    check(end($r)['form'] === 'kurz', 'Datensatz');
});

test('gültiger Widerruf → 200, Mail an Inhaber + Eingangsbestätigung an Absender', function () use ($port, $storage) {
    $before = substr_count(maillog($storage), '] An: ');
    [$s, $j] = json_post($port, ['form' => 'widerruf', 'name' => 'Ina Test', 'bestellnummer' => 'B-123', 'email' => 'ina@beispiel.de']);
    check($s === 200 && $j['ok'] === true && $j['redirect'] === null, "Status $s");
    $log = maillog($storage);
    check(substr_count($log, '] An: ') - $before === 2, 'erwartet 2 Mails');
    check(str_contains($log, 'An: ina@beispiel.de') && str_contains($log, 'Ihr Widerruf zur Bestell- oder Buchungsnummer B-123'), 'Bestätigung');
    $r = rows($storage);
    check(end($r)['consent_at'] === null, 'Widerruf ohne consent_at');
});

test('ungültige Anfrage → 422 mit Feldfehlern (Texte aus messages.json)', function () use ($port) {
    $m = json_decode((string) file_get_contents(ROOT . '/server/messages.json'), true);
    [$s, $j] = json_post($port, ['form' => 'kontakt', 'name' => '', 'email' => 'anna@beispiel', 'nachricht' => '']);
    check($s === 422, "Status $s");
    check(($j['errors']['name'] ?? '') === $m['required'], 'name');
    check(($j['errors']['email'] ?? '') === $m['email'], 'email');
    check(($j['errors']['nachricht'] ?? '') === $m['nachricht'], 'nachricht');
    check(($j['errors']['einwilligung'] ?? '') === $m['einwilligung'], 'einwilligung');
});

test('fehlende Einwilligung → 422 nur «einwilligung»', function () use ($port, $valid) {
    $f = $valid;
    unset($f['einwilligung']);
    [$s, $j] = json_post($port, $f);
    check($s === 422 && array_keys($j['errors']) === ['einwilligung'], "Status $s " . json_encode($j['errors'] ?? []));
});

test('zu lange Eingabe (Name > 100) → 422', function () use ($port, $valid) {
    [$s, $j] = json_post($port, ['name' => str_repeat('a', 101)] + $valid);
    check($s === 422 && isset($j['errors']['name']), "Status $s");
});

test('Honeypot gefüllt → stiller Erfolg, nichts gespeichert', function () use ($port, $storage, $valid) {
    $n = count(rows($storage));
    [$s, $j] = json_post($port, ['website' => 'http://spam.example'] + $valid);
    check($s === 200 && $j['ok'] === true, "Status $s");
    check(count(rows($storage)) === $n, 'Datensatz angelegt');
});

test('zu schnell ausgefüllt (t = Sekunden seit Laden < MIN_FILL_SECONDS) → stiller Erfolg, nichts gespeichert', function () use ($port, $storage, $valid) {
    $n = count(rows($storage));
    [$s, $j] = json_post($port, ['t' => '1'] + $valid);
    check($s === 200 && $j['ok'] === true, "Status $s");
    check(count(rows($storage)) === $n, 'Datensatz angelegt');
});

test('«Origin: null» mit eigenem Referer → angenommen; mit fremdem Referer → 403', function () use ($port, $valid) {
    [$s] = json_post($port, $valid, ['Origin' => 'null', 'Referer' => "http://127.0.0.1:$port/kontakt/"]);
    check($s === 200, "eigener Referer: $s");
    [$s2] = json_post($port, $valid, ['Origin' => 'null', 'Referer' => 'https://evil.example/']);
    check($s2 === 403, "fremder Referer: $s2");
});

test('fremder Origin → 403', function () use ($port, $storage, $valid) {
    $n = count(rows($storage));
    [$s] = json_post($port, $valid, ['Origin' => 'https://evil.example']);
    check($s === 403, "Status $s");
    [$s2] = json_post($port, $valid, ['Origin' => null, 'Referer' => 'https://evil.example/form']);
    check($s2 === 403, "Referer-Status $s2");
    check(count(rows($storage)) === $n, 'Datensatz angelegt');
});

test('CR/LF-Injection: keine zusätzlichen Kopfzeilen, Name einzeilig gespeichert', function () use ($port, $storage, $valid) {
    [$s] = json_post($port, ['name' => "Eve\r\nBcc: victim@example.com", 'email' => "eve@beispiel.de\r\nCc: x@example.com"] + $valid);
    check($s === 422, 'E-Mail mit CRLF muss ungültig sein, Status ' . $s);
    $before = maillog($storage);
    [$s2] = json_post($port, ['name' => "Eve\r\nBcc: victim@example.com"] + $valid);
    check($s2 === 200, "Status $s2");
    $new = substr(maillog($storage), strlen($before));
    check(!preg_match('/^(Bcc|Cc):/mi', $new), 'Header-Injection im Mail-Log');
    $r = rows($storage);
    check(end($r)['name'] === 'Eve Bcc: victim@example.com', 'Name nicht bereinigt');
});

test('XSS: Fehlerseite ohne JavaScript escaped Eingaben', function () use ($port) {
    [$s, , $b] = http($port, 'POST', '/kontakt.php', ['form' => 'kontakt', 'name' => '<script>alert(1)</script>', 'email' => 'x', 'nachricht' => '"><img src=x onerror=alert(2)>']);
    check($s === 422, "Status $s");
    check(!str_contains($b, '<script>alert(1)</script>') && !str_contains($b, '<img src=x onerror'), 'unescaped HTML');
    check(str_contains($b, '&lt;script&gt;alert(1)&lt;/script&gt;'), 'Wert nicht erhalten');
    check(str_contains($b, 'class="errsum"') && str_contains($b, 'aria-invalid="true"'), 'Fehlerübersicht/aria-invalid fehlt');
});

test('SQL-Sonderzeichen werden wörtlich gespeichert (vorbereitete Anweisungen)', function () use ($port, $storage, $valid) {
    $evil = "O'Brien\"; DROP TABLE submissions;--";
    [$s] = json_post($port, ['name' => $evil] + $valid);
    check($s === 200, "Status $s");
    $r = rows($storage);
    check(end($r)['name'] === $evil, 'Name verändert');
});

test('ohne JavaScript: Erfolg → 303 auf /kontakt/danke/', function () use ($port, $valid) {
    [$s, $h] = http($port, 'POST', '/kontakt.php', $valid);
    check($s === 303 && ($h['location'] ?? '') === '/kontakt/danke/', "Status $s");
});

test('ohne JavaScript: Widerruf → Bestätigungsseite (D-05)', function () use ($port) {
    [$s, , $b] = http($port, 'POST', '/kontakt.php', ['form' => 'widerruf', 'name' => 'Ina', 'bestellnummer' => 'B-9', 'email' => 'ina@beispiel.de']);
    check($s === 200 && str_contains($b, 'Widerruf eingegangen') && str_contains($b, 'class="hdr"'), "Status $s");
});

test('Router sperrt interne Pfade (AC-10) → 404', function () use ($port) {
    foreach (['/storage/', '/storage/submissions.sqlite', '/storage/mail.log', '/server/config.local.php', '/server/config.example.php',
              '/server/bin/submissions.php', '/server/messages.json', '/build.py', '/_refs/', '/src/layout.html', '/docs/', '/tests/php/run.php',
              '/.git/config', '/README.md'] as $p) {
        [$s] = http($port, 'GET', $p);
        check($s === 404, "$p → $s");
    }
    [$s, $h] = http($port, 'GET', '/fonts/anton-latin.woff2');
    check($s === 200 && ($h['content-type'] ?? '') === 'font/woff2', 'woff2 MIME');
    [$s, $h] = http($port, 'GET', '/assets/photos/weg.avif');
    check($s === 200 && ($h['content-type'] ?? '') === 'image/avif', 'avif MIME');
    [$s, , $b] = http($port, 'GET', '/gibt-es-nicht/');
    check($s === 404 && str_contains($b, 'Seite nicht gefunden'), '404-Seite');
});

test('Texte und Leistungsliste: Client (build.py) = Server', function () {
    $m = json_decode((string) file_get_contents(ROOT . '/server/messages.json'), true);
    $html = (string) file_get_contents(ROOT . '/kontakt/index.html');
    check(str_contains($html, 'data-msg="' . htmlspecialchars($m['email'], ENT_QUOTES) . '"'), 'data-msg email');
    check(str_contains($html, 'data-msg="' . htmlspecialchars($m['einwilligung'], ENT_QUOTES) . '"'), 'data-msg einwilligung');
    require_once ROOT . '/server/bootstrap.php';
    preg_match('/^SERVICES = (\[.*\])$/m', (string) file_get_contents(ROOT . '/build.py'), $mm);
    check(json_decode($mm[1] ?? '[]', true) === Wahl\Validator::SERVICES, 'SERVICES unterschiedlich');
});

// Rate-Limit mit eigener Instanz (5 je 10 Minuten)
[$rport, $rstorage] = start_server(['RATE_LIMIT' => '5/600'], 'rate');
test('Rate-Limit: 6. Anfrage in 10 Minuten → 429, IP nicht gespeichert', function () use ($rport, $rstorage, $valid) {
    for ($i = 1; $i <= 5; $i++) {
        [$s] = json_post($rport, $valid);
        check($s === 200, "Anfrage $i: $s");
    }
    [$s, $j] = json_post($rport, $valid);
    check($s === 429 && ($j['error'] ?? '') !== '', "6. Anfrage: $s");
    $db = (string) file_get_contents("$rstorage/submissions.sqlite");
    check(!str_contains($db, '127.0.0.1'), 'rohe IP in der Datenbank');
});

// Versandfehler: SMTP auf geschlossenem Port
$closed = free_port();
[$fport, $fstorage] = start_server(['MAIL_TRANSPORT' => 'smtp', 'SMTP_HOST' => '127.0.0.1', 'SMTP_PORT' => (string) $closed, 'SMTP_SECURE' => 'none', 'SMTP_TIMEOUT' => '2'], 'fail');
test('Versandfehler → 502 mit Telefonnummer, Anfrage trotzdem gespeichert (mail_status=failed)', function () use ($fport, $fstorage, $valid) {
    [$s, $j] = json_post($fport, $valid);
    check($s === 502 && str_contains($j['error'] ?? '', '0381 25 22 39 41'), "Status $s");
    $r = rows($fstorage);
    check(count($r) === 1 && $r[0]['mail_status'] === 'failed', 'Datensatz/mail_status');
});

// SMTP gegen Fake-Server
$sport = free_port();
$slog = sys_get_temp_dir() . '/wahl-fake-smtp-' . bin2hex(random_bytes(4)) . '.log';
$procs[] = proc_open([PHP_BINARY, __DIR__ . '/fake_smtp.php', (string) $sport, $slog], [0 => ['file', '/dev/null', 'r'], 1 => ['file', '/dev/null', 'w'], 2 => ['file', '/dev/null', 'w']], $pp);
wait_port($sport);
[$mport] = start_server(['MAIL_TRANSPORT' => 'smtp', 'SMTP_HOST' => '127.0.0.1', 'SMTP_PORT' => (string) $sport, 'SMTP_SECURE' => 'none',
                         'SMTP_USER' => 'testuser', 'SMTP_PASS' => 'testpass'], 'smtp');
test('SMTP (Fake-Server): AUTH LOGIN, MAIL FROM, RCPT TO, MIME-Betreff, Daten', function () use ($mport, $slog, $valid) {
    [$s] = json_post($mport, ['nachricht' => 'Hofeinfahrt pflastern, ca. 60 m². ' . str_repeat('Lange Zeile ohne Umbruch. ', 80)] + $valid);
    check($s === 200, "Status $s");
    $d = (string) file_get_contents($slog);
    $longest = max(array_map('strlen', explode("\n", $d)));
    check($longest <= 1000, "Zeile mit $longest Zeichen im SMTP-Dialog (Limit 998 + CRLF)");
    check(str_contains($d, 'C: Content-Transfer-Encoding: quoted-printable'), 'quoted-printable');
    check(str_contains($d, 'C: AUTH LOGIN') && str_contains($d, 'C: ' . base64_encode('testuser')), 'AUTH');
    check(str_contains($d, 'C: MAIL FROM:<noreply@wahl-strassenbau.de>') && str_contains($d, 'C: RCPT TO:<info@wahl-strassenbau.de>'), 'Umschlag');
    // RFC 2047: nur die Wörter mit Umlauten werden kodiert («Anfrage =?UTF-8?B?…?=»)
    check(preg_match('/C: Subject: Anfrage =\?UTF-8\?B\?[A-Za-z0-9+\/=]+\?=$/m', $d) === 1 && str_contains($d, 'C: Reply-To: erika@beispiel.de'), 'Kopfzeilen');
    check(str_contains($d, 'C: Hofeinfahrt pflastern, ca. 60 m=C2=B2.') && str_contains($d, 'S: 250 2.0.0 queued'), 'Daten (QP-kodiert)');
    check(!str_contains($d, 'testpass'), 'Passwort im Klartext');
});

// Speicher nicht beschreibbar: Anfrage geht trotzdem per Mail raus
$ro = tmpdir('ro');
[$xport, $xstorage] = start_server(['STORAGE_PATH' => $ro . '/nicht/da', 'MAIL_TRANSPORT' => 'smtp', 'SMTP_HOST' => '127.0.0.1', 'SMTP_PORT' => (string) $sport, 'SMTP_SECURE' => 'none'], 'ro');
chmod($ro, 0500);
test('Speicher nicht verfügbar → Mail wird trotzdem gesendet (200), kein Datenverlust', function () use ($xport, $slog, $valid, $ro) {
    [$s, $j] = json_post($xport, ['name' => 'Ohne Speicher'] + $valid);
    chmod($ro, 0700);
    check($s === 200 && ($j['ok'] ?? false) === true, "Status $s");
    check(str_contains((string) file_get_contents($slog), 'Ohne Speicher'), 'Mail nicht gesendet');
});

// Hinter Proxy: Rate-Limit je Besucher-IP aus CLIENT_IP_HEADER
[$pport] = start_server(['RATE_LIMIT' => '2/600', 'CLIENT_IP_HEADER' => 'HTTP_X_FORWARDED_FOR'], 'proxy');
test('CLIENT_IP_HEADER: Rate-Limit getrennt je weitergeleiteter IP', function () use ($pport, $valid) {
    foreach (['203.0.113.1', '203.0.113.1'] as $ip) {
        [$s] = json_post($pport, $valid, ['X-Forwarded-For' => $ip]);
        check($s === 200, "erste IP: $s");
    }
    [$s] = json_post($pport, $valid, ['X-Forwarded-For' => '203.0.113.1']);
    check($s === 429, "dritte Anfrage gleiche IP: $s");
    [$s] = json_post($pport, $valid, ['X-Forwarded-For' => '198.51.100.7']);
    check($s === 200, "andere IP: $s");
});

test('Aufbewahrung: purge löscht Anfragen älter als RETENTION_DAYS, neuere bleiben', function () use ($storage) {
    $pdo = new PDO("sqlite:$storage/submissions.sqlite");
    $pdo->exec("INSERT INTO submissions (created_at, form, name) VALUES ('" . gmdate('Y-m-d\TH:i:s\Z', time() - 91 * 86400) . "', 'kontakt', 'Alt')");
    $before = count(rows($storage));
    $out = shell_exec('STORAGE_PATH=' . escapeshellarg($storage) . ' RETENTION_DAYS=90 ' . escapeshellarg(PHP_BINARY) . ' ' . escapeshellarg(ROOT . '/server/bin/submissions.php') . ' purge');
    $after = rows($storage);
    check(str_contains((string) $out, '1 Anfrage(n)'), 'Ausgabe: ' . trim((string) $out));
    check(count($after) === $before - 1 && !in_array('Alt', array_column($after, 'name'), true), 'alter Datensatz noch da');
});

test('CLI: list und export (csv/json) funktionieren nur auf der Kommandozeile', function () use ($storage) {
    $env = 'STORAGE_PATH=' . escapeshellarg($storage) . ' ';
    $bin = escapeshellarg(PHP_BINARY) . ' ' . escapeshellarg(ROOT . '/server/bin/submissions.php');
    $csv = (string) shell_exec($env . $bin . ' export --format csv');
    check(str_starts_with($csv, 'id;created_at;form;'), 'CSV-Kopf');
    $json = json_decode((string) shell_exec($env . $bin . ' export --format json'), true);
    check(is_array($json) && count($json) > 3, 'JSON');
    check(str_contains((string) shell_exec($env . $bin . ' list 2>&1'), 'Anfrage(n)'), 'list');
});

foreach ($procs as $p) {
    proc_terminate($p);
}
$failed = array_filter($results, static fn ($r) => !$r[0]);
echo "\n" . (count($results) - count($failed)) . '/' . count($results) . " Tests bestanden\n";
exit($failed ? 1 : 0);
