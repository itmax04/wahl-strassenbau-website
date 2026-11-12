<?php
declare(strict_types=1);

namespace Wahl;

/**
 * Ablauf (ADR-0001 Punkt 3): POST → Origin/Referer → Honeypot (stiller Erfolg) → Mindestzeit (stiller Erfolg)
 * → Rate-Limit (429) → Validierung (422) → SQLite → Mail an Inhaber → bei Widerruf Eingangsbestätigung → mail_status → Antwort.
 */
final class FormHandler
{
    private bool $json;
    private string $form = 'kontakt';

    public function __construct(private readonly array $server, private readonly array $post)
    {
        $accept = (string) ($server['HTTP_ACCEPT'] ?? '');
        $this->json = stripos($accept, 'application/json') !== false || ($server['HTTP_X_REQUESTED_WITH'] ?? '') === 'fetch';
    }

    public function handle(): void
    {
        header('X-Content-Type-Options: nosniff');
        header('Cache-Control: no-store');
        header('Referrer-Policy: same-origin');
        $m = messages();

        if (($this->server['REQUEST_METHOD'] ?? '') !== 'POST') {
            header('Allow: POST');
            $this->fail(405, [], $m['method']);
            return;
        }
        $form = Validator::line($this->post['form'] ?? '');
        $this->form = in_array($form, Validator::FORMS, true) ? $form : 'kontakt';

        if (!$this->originAllowed()) {
            $this->fail(403, [], $m['origin']);
            return;
        }
        // Honeypot: für Menschen unsichtbar; gefüllt = Bot → stiller Erfolg, nichts wird gespeichert oder gesendet
        if (Validator::line($this->post['website'] ?? '') !== '') {
            $this->success(true);
            return;
        }
        // Mindestausfüllzeit: «t» setzt main.js beim Absenden = Sekunden seit dem Laden der Seite (relativ, daher unabhängig
        // von der Uhr des Besuchers). Ohne JavaScript fehlt das Feld → keine Prüfung.
        $t = $this->post['t'] ?? '';
        if (is_string($t) && $t !== '' && ctype_digit($t) && strlen($t) < 9 && (int) $t < Config::int('MIN_FILL_SECONDS')) {
            $this->success(true);
            return;
        }

        // Speicher: fällt SQLite aus (Rechte, Plattenplatz), wird die Anfrage trotzdem per E-Mail zugestellt (ADR-0001: nichts verlieren)
        $store = null;
        try {
            $store = store();
        } catch (\Throwable $e) {
            error_log('kontakt.php: Speicher nicht verfügbar: ' . $e->getMessage());
        }
        if ($store !== null && !RateLimiter::fromConfig($store)->hit($this->clientIp())) {
            header('Retry-After: ' . max(1, (int) explode('/', Config::get('RATE_LIMIT') . '/600')[1]));
            $this->fail(429, [], $m['rate']);
            return;
        }

        [$data, $errors] = Validator::validate($this->form, $this->post);
        if ($errors) {
            $this->fail(422, $errors, '', $data);
            return;
        }

        $consentAt = $this->form === 'widerruf' ? null : gmdate('Y-m-d\TH:i:s\Z');
        $id = null;
        if ($store !== null) {
            try {
                $id = $store->insert($this->form, $data, $consentAt);
                $store->purge(max(1, Config::int('RETENTION_DAYS')));
            } catch (\Throwable $e) {
                error_log('kontakt.php: Speichern fehlgeschlagen: ' . $e->getMessage());
            }
        }

        $mailer = mailer();
        $sent = $mailer->send($this->ownerMessage($data));
        $status = $sent ? 'sent' : 'failed';
        $confirmed = null;
        if ($sent && $this->form === 'widerruf') {
            $confirmed = $mailer->send($this->confirmation($data));
            $status = $confirmed ? 'sent' : 'sent_owner_only';
        }
        if ($id !== null) {
            $store->setMailStatus($id, $status);
        }
        error_log('kontakt.php: Anfrage #' . ($id ?? '-') . " ({$this->form}) mail_status=$status");

        if (!$sent && $id === null) {
            $this->fail(500, [], $m['network'], $data);   // weder gespeichert noch gesendet
            return;
        }
        if (!$sent) {
            $this->fail(502, [], $m['network'], $data);
            return;
        }
        $this->success(false, $confirmed);
    }

    /**
     * IP für das Rate-Limit. Hinter einem Proxy/CDN liefert REMOTE_ADDR nur die Proxy-Adresse; dann den Header aus
     * CLIENT_IP_HEADER (z. B. HTTP_X_FORWARDED_FOR oder HTTP_CF_CONNECTING_IP) setzen — nur, wenn der Proxy ihn zuverlässig setzt.
     */
    private function clientIp(): string
    {
        $header = Config::get('CLIENT_IP_HEADER');
        if ($header !== '' && !empty($this->server[$header])) {
            $first = trim(explode(',', (string) $this->server[$header])[0]);
            if (filter_var($first, FILTER_VALIDATE_IP) !== false) {
                return $first;
            }
        }
        return (string) ($this->server['REMOTE_ADDR'] ?? '');
    }

    private function originAllowed(): bool
    {
        $host = strtolower((string) ($this->server['HTTP_HOST'] ?? ''));
        $allowed = array_filter(array_map(static fn ($o) => strtolower(rtrim(trim($o), '/')), explode(',', Config::get('ALLOWED_ORIGINS'))));
        $origin = (string) ($this->server['HTTP_ORIGIN'] ?? '');
        // «Origin: null» (Datenschutzmodi, Weiterleitungen) wie fehlender Origin behandeln → Referer prüfen
        $check = ($origin !== '' && $origin !== 'null') ? $origin : (string) ($this->server['HTTP_REFERER'] ?? '');
        if ($check === '') {
            return true; // weder Origin noch Referer (z. B. strikte Datenschutz-Einstellungen): nicht blockieren
        }
        $parts = parse_url($check);
        if (!is_array($parts) || empty($parts['host'])) {
            return false;
        }
        $checkHost = strtolower($parts['host']) . (isset($parts['port']) ? ':' . $parts['port'] : '');
        $checkOrigin = strtolower(($parts['scheme'] ?? 'http') . '://' . $checkHost);
        return $checkHost === $host || in_array($checkOrigin, $allowed, true);
    }

    /** @param array<string,string> $d */
    private function ownerMessage(array $d): Message
    {
        $name = $d['name'];
        if ($this->form === 'widerruf') {
            $subject = 'Widerruf über die Webseite: ' . $name;
            $body = "Widerruf über die Webseite\n\n"
                . "Name: $name\n"
                . 'Bestell- oder Buchungsnummer: ' . $d['bestellnummer'] . "\n"
                . 'E-Mail: ' . $d['email'] . "\n"
                . 'Betroffene Artikel: ' . ($d['artikel'] !== '' ? $d['artikel'] : '(gesamter Vertrag)') . "\n\n"
                . "Grund:\n" . ($d['nachricht'] !== '' ? $d['nachricht'] : '(nicht angegeben)') . "\n";
        } else {
            $subject = ($this->form === 'kurz' ? 'Rückrufwunsch über die Webseite: ' : 'Anfrage über die Webseite: ') . $name;
            $body = "Anfrage über die Webseite ({$this->form})\n\n"
                . "Name: $name\n"
                . 'E-Mail: ' . (($d['email'] ?? '') !== '' ? $d['email'] : '(nicht angegeben)') . "\n"
                . 'Telefon: ' . (($d['telefon'] ?? '') !== '' ? $d['telefon'] : '(nicht angegeben)') . "\n"
                . 'Leistung: ' . (($d['leistung'] ?? '') !== '' ? $d['leistung'] : '(nicht angegeben)') . "\n\n"
                . "Nachricht:\n" . $d['nachricht'] . "\n\n"
                . "Einwilligung zur Datenverarbeitung: erteilt\n";
        }
        $body .= "\n--\nGesendet über wahl-strassenbau.de am " . date('d.m.Y H:i') . " Uhr\n";
        return new Message(Config::get('RECIPIENT'), $subject, $body, $d['email'] ?? '');
    }

    /** Eingangsbestätigung Widerruf (Text aus dem bisherigen kontakt.php). */
    private function confirmation(array $d): Message
    {
        $body = "Guten Tag {$d['name']},\n\nIhr Widerruf zur Bestell- oder Buchungsnummer {$d['bestellnummer']} ist bei uns eingegangen.\n\n"
            . 'Wahl Straßenbau GmbH & Co. KG' . "\nTelefon: " . Config::get('PHONE') . "\n";
        return new Message($d['email'], 'Eingangsbestätigung: Ihr Widerruf', $body);
    }

    /** @param bool|null $confirmed Widerruf: Eingangsbestätigung versendet? (null = nicht zutreffend) */
    private function success(bool $silent, ?bool $confirmed = null): void
    {
        $redirect = $this->form === 'widerruf' ? null : '/kontakt/danke/';
        if ($this->json) {
            header('Content-Type: application/json; charset=utf-8');
            echo json_encode(['ok' => true, 'errors' => (object) [], 'error' => '', 'redirect' => $redirect, 'confirmation' => $confirmed],
                JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
            return;
        }
        if ($redirect !== null) {
            header('Location: ' . $redirect, true, 303);
            return;
        }
        // D-05: Widerruf ohne JavaScript → Bestätigungsseite im Stil der Website
        header('Content-Type: text/html; charset=utf-8');
        echo Page::widerrufDone($confirmed !== false);
    }

    /** @param array<string,string> $errors @param array<string,string> $values */
    private function fail(int $status, array $errors, string $general, array $values = []): void
    {
        http_response_code($status);
        if ($this->json) {
            header('Content-Type: application/json; charset=utf-8');
            echo json_encode(['ok' => false, 'errors' => (object) $errors, 'error' => $general], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
            return;
        }
        header('Content-Type: text/html; charset=utf-8');
        echo Page::formError($this->form, $errors, $general, $values ?: $this->rawValues());
    }

    /** Eingaben für die Fehlerseite ohne JavaScript (werden dort escaped). */
    private function rawValues(): array
    {
        $out = [];
        foreach (['name', 'email', 'telefon', 'leistung', 'nachricht', 'bestellnummer', 'artikel'] as $k) {
            $out[$k] = Validator::text($this->post[$k] ?? '');
        }
        return $out;
    }
}
