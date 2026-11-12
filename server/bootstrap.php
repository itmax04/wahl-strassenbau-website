<?php
declare(strict_types=1);

/**
 * Gemeinsamer Einstieg für kontakt.php und server/bin/submissions.php (ADR-0001).
 * - lädt die Konfiguration: Standardwerte → server/config.local.php → Umgebungsvariablen (höchste Priorität),
 * - registriert den Autoloader für server/lib (Namespace Wahl\),
 * - zeigt keine Fehlerdetails an (Fehler gehen ins PHP-Fehlerlog, nicht an Besucher).
 */

namespace Wahl;

const ROOT = __DIR__ . '/..';

ini_set('display_errors', '0');
ini_set('log_errors', '1');
error_reporting(E_ALL);
mb_internal_encoding('UTF-8');
date_default_timezone_set('Europe/Berlin');

spl_autoload_register(static function (string $class): void {
    if (str_starts_with($class, 'Wahl\\')) {
        $file = __DIR__ . '/lib/' . str_replace('\\', '/', substr($class, 5)) . '.php';
        if (is_file($file)) {
            require $file;
        }
    }
});

final class Config
{
    /** Sichere Standardwerte: Transport «log», Speicher in storage/ (per .htaccess/Router gesperrt). */
    private const DEFAULTS = [
        'RECIPIENT'        => 'info@wahl-strassenbau.de',
        'FROM_ADDRESS'     => 'noreply@wahl-strassenbau.de',
        'MAIL_TRANSPORT'   => 'log',               // log | mail | smtp
        'SMTP_HOST'        => '',
        'SMTP_PORT'        => '587',
        'SMTP_USER'        => '',
        'SMTP_PASS'        => '',
        'SMTP_SECURE'      => 'tls',               // tls (STARTTLS) | ssl | none
        'SMTP_TIMEOUT'     => '10',
        'STORAGE_PATH'     => ROOT . '/storage',
        'RETENTION_DAYS'   => '90',
        'RATE_LIMIT'       => '5/600',             // Anzahl / Sekunden
        'MIN_FILL_SECONDS' => '3',
        'ALLOWED_ORIGINS'  => '',
        'CLIENT_IP_HEADER' => '',                  // nur hinter Proxy/CDN: z. B. HTTP_X_FORWARDED_FOR                  // zusätzliche Origins, kommagetrennt (z. B. https://www.wahl-strassenbau.de)
        'SITE_NAME'        => 'Wahl Straßenbau',
        'PHONE'            => '0381 25 22 39 41',
    ];

    private static ?array $values = null;

    public static function get(string $key): string
    {
        if (self::$values === null) {
            $values = self::DEFAULTS;
            $local = __DIR__ . '/config.local.php';
            if (is_file($local)) {
                $file = require $local;
                if (is_array($file)) {
                    foreach ($file as $k => $v) {
                        if (array_key_exists($k, self::DEFAULTS)) {
                            $values[$k] = (string) $v;
                        }
                    }
                }
            }
            foreach (array_keys(self::DEFAULTS) as $k) {
                $env = getenv($k);
                if ($env !== false && $env !== '') {
                    $values[$k] = $env;
                }
            }
            self::$values = $values;
        }
        return self::$values[$key] ?? '';
    }

    public static function int(string $key): int
    {
        return (int) self::get($key);
    }

    public static function storageDir(): string
    {
        $dir = rtrim(self::get('STORAGE_PATH'), '/');
        if (!is_dir($dir)) {
            mkdir($dir, 0700, true);
        }
        return $dir;
    }

    /** Nur für Tests: Werte neu laden (Umgebung geändert). */
    public static function reset(): void
    {
        self::$values = null;
    }
}

function messages(): array
{
    static $m = null;
    if ($m === null) {
        $m = json_decode((string) file_get_contents(__DIR__ . '/messages.json'), true, 4, JSON_THROW_ON_ERROR);
    }
    return $m;
}

function mailer(): Mailer
{
    return match (Config::get('MAIL_TRANSPORT')) {
        'mail' => new MailFunctionMailer(),
        'smtp' => new SmtpMailer(
            Config::get('SMTP_HOST'),
            Config::int('SMTP_PORT'),
            Config::get('SMTP_USER'),
            Config::get('SMTP_PASS'),
            Config::get('SMTP_SECURE'),
            max(1, Config::int('SMTP_TIMEOUT')),
        ),
        default => new LogMailer(Config::storageDir() . '/mail.log'),
    };
}

function store(): SubmissionStore
{
    static $s = null;
    return $s ??= new SubmissionStore(Config::storageDir() . '/submissions.sqlite');
}
