<?php
declare(strict_types=1);

/**
 * Router für den eingebauten PHP-Server (nur lokal):
 *   php -S localhost:5178 server/router.php        (aus dem Projektordner)
 *
 * - liefert statische Dateien mit korrekten MIME-Typen (u. a. avif, woff2),
 * - führt nur /kontakt.php aus,
 * - Verzeichnisse → index.html, Unbekanntes → /404.html mit Status 404,
 * - gesperrte Pfade (server/, storage/, _refs/, docs/, tests/, *.sqlite, *.log, Build-Dateien …) → 404 (wie .htaccess).
 */

$root = dirname(__DIR__);
$path = rawurldecode(parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/');

const MIME = [
    'html' => 'text/html; charset=utf-8', 'css' => 'text/css; charset=utf-8', 'js' => 'text/javascript; charset=utf-8',
    'json' => 'application/json; charset=utf-8', 'xml' => 'application/xml; charset=utf-8', 'txt' => 'text/plain; charset=utf-8',
    'svg' => 'image/svg+xml', 'png' => 'image/png', 'jpg' => 'image/jpeg', 'jpeg' => 'image/jpeg', 'webp' => 'image/webp',
    'avif' => 'image/avif', 'ico' => 'image/x-icon', 'woff2' => 'font/woff2', 'woff' => 'font/woff', 'pdf' => 'application/pdf',
    'webmanifest' => 'application/manifest+json',
];

function send_404(string $root): void
{
    http_response_code(404);
    header('Content-Type: text/html; charset=utf-8');
    readfile($root . '/404.html');
}

function security_headers(): void
{
    header('X-Content-Type-Options: nosniff');
    header('Referrer-Policy: strict-origin-when-cross-origin');
    header('X-Frame-Options: SAMEORIGIN');
    header('Permissions-Policy: camera=(), microphone=(), geolocation=()');
}

security_headers();

// Gesperrte Bereiche (siehe ADR-0001 Punkt 6 und .htaccess)
$blocked = '#^/(?:server|storage|_refs|docs|tests|src|cloudflare|fonts/src|\.git|\.claude|\.agents|node_modules)(?:/|$)'
    . '|\.(?:sqlite\d?|sqlite-(?:wal|shm|journal)|log|py|md|php\.example|lock|sh|ini|bak|swp)$'
    . '|/\.(?!well-known)'
    . '|^/(?:build\.py|skills-lock\.json|README|CLAUDE|DESIGN|CONTENT)#i';
if (preg_match($blocked, $path) || str_contains($path, "\0") || str_contains($path, '..')) {
    send_404($root);
    return true;
}

if ($path === '/kontakt.php') {
    chdir($root);
    require $root . '/kontakt.php';
    return true;
}
if (str_ends_with($path, '.php')) {
    send_404($root);
    return true;
}

$file = $root . $path;
if (is_dir($file)) {
    if (!str_ends_with($path, '/')) {
        header('Location: ' . $path . '/', true, 301);
        return true;
    }
    $file = rtrim($file, '/') . '/index.html';
}
$real = realpath($file);
if ($real === false || !is_file($real) || !str_starts_with($real, $root . DIRECTORY_SEPARATOR)) {
    send_404($root);
    return true;
}

$ext = strtolower(pathinfo($real, PATHINFO_EXTENSION));
if (!isset(MIME[$ext])) {
    send_404($root);
    return true;
}
header('Content-Type: ' . MIME[$ext]);
header('Vary: Accept-Encoding');
if (in_array($ext, ['avif', 'webp', 'jpg', 'png', 'woff2', 'svg', 'ico'], true)) {
    header('Cache-Control: public, max-age=604800');
} else {
    header('Cache-Control: no-cache');
}
// Textdateien komprimiert ausliefern wie mod_deflate in .htaccess (Produktion)
$gzip = in_array($ext, ['html', 'css', 'js', 'json', 'svg', 'xml', 'txt', 'webmanifest'], true)
    && str_contains((string) ($_SERVER['HTTP_ACCEPT_ENCODING'] ?? ''), 'gzip');
if ($gzip) {
    $payload = gzencode((string) file_get_contents($real), 6);
    header('Content-Encoding: gzip');
    header('Content-Length: ' . strlen($payload));
    if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'HEAD') {
        echo $payload;
    }
    return true;
}
header('Content-Length: ' . filesize($real));
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'HEAD') {
    readfile($real);
}
return true;
