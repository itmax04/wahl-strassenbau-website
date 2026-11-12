<?php
declare(strict_types=1);

/**
 * Anfragen verwalten (nur Kommandozeile, ADR-0001):
 *   php server/bin/submissions.php list [--days N]
 *   php server/bin/submissions.php export --format csv|json [--days N]
 *   php server/bin/submissions.php purge
 * Optional als täglicher Cronjob: php /pfad/server/bin/submissions.php purge
 */

if (PHP_SAPI !== 'cli') {
    http_response_code(404);
    exit;
}

require __DIR__ . '/../bootstrap.php';

use Wahl\Config;

$args = array_slice($argv, 1);
$cmd = $args[0] ?? 'help';
$opt = static function (string $name, ?string $default = null) use ($args): ?string {
    $i = array_search('--' . $name, $args, true);
    return $i !== false && isset($args[$i + 1]) ? $args[$i + 1] : $default;
};
$days = $opt('days');
$days = $days !== null ? max(1, (int) $days) : null;
$store = Wahl\store();

switch ($cmd) {
    case 'list':
        $rows = $store->list($days);
        foreach ($rows as $r) {
            printf("#%d  %s  %-8s  %-24s  %-28s  %s\n", $r['id'], $r['created_at'], $r['form'], mb_strimwidth((string) $r['name'], 0, 24, '…'),
                mb_strimwidth((string) ($r['email'] ?: $r['phone']), 0, 28, '…'), $r['mail_status']);
        }
        fwrite(STDERR, count($rows) . " Anfrage(n)\n");
        break;
    case 'export':
        $rows = $store->list($days);
        if ($opt('format', 'csv') === 'json') {
            echo json_encode($rows, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES), "\n";
        } else {
            $out = fopen('php://output', 'w');
            fputcsv($out, ['id', 'created_at', 'form', 'name', 'email', 'phone', 'service', 'message', 'order_no', 'items', 'consent_at', 'mail_status'], ';', '"', '');
            foreach ($rows as $r) {
                // Formel-Injection in Tabellenprogrammen vermeiden
                $r = array_map(static fn ($v) => is_string($v) && preg_match('/^[=+\-@\t\r]/', $v) ? "'" . $v : $v, $r);
                fputcsv($out, array_values($r), ';', '"', '');
            }
        }
        break;
    case 'purge':
        $n = $store->purge(max(1, Config::int('RETENTION_DAYS')));
        echo "$n Anfrage(n) älter als " . Config::int('RETENTION_DAYS') . " Tage gelöscht\n";
        break;
    default:
        echo "Verwendung: php server/bin/submissions.php list [--days N] | export --format csv|json [--days N] | purge\n";
        exit($cmd === 'help' ? 0 : 1);
}
