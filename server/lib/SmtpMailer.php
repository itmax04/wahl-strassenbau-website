<?php
declare(strict_types=1);

namespace Wahl;

/**
 * Minimaler SMTP-Client ohne Fremdbibliotheken (ADR-0001): EHLO, optional STARTTLS (tls) oder implizites TLS (ssl),
 * AUTH LOGIN, MAIL FROM, RCPT TO, DATA, QUIT. Zertifikate werden geprüft (Standard von PHP/OpenSSL).
 * Getestet gegen tests/php/fake_smtp.php; Verhalten beim echten Provider: NOT RUN bis zur Hosting-Entscheidung.
 */
final class SmtpMailer implements Mailer
{
    /** @var resource|null */
    private $socket = null;

    public function __construct(
        private readonly string $host,
        private readonly int $port,
        private readonly string $user,
        private readonly string $pass,
        private readonly string $secure,
        private readonly int $timeout,
    ) {
    }

    public function send(Message $message): bool
    {
        try {
            $this->deliver($message);
            return true;
        } catch (\Throwable $e) {
            // Nur Status ins Fehlerlog, keine personenbezogenen Daten, keine Zugangsdaten
            error_log('SmtpMailer: ' . preg_replace('/\s+/', ' ', $e->getMessage()));
            return false;
        } finally {
            if (is_resource($this->socket)) {
                @fwrite($this->socket, "QUIT\r\n");
                @fclose($this->socket);
            }
            $this->socket = null;
        }
    }

    private function deliver(Message $message): void
    {
        $to = Validator::line($message->to);
        $from = Validator::line(Config::get('FROM_ADDRESS'));
        if ($this->host === '' || filter_var($to, FILTER_VALIDATE_EMAIL) === false || filter_var($from, FILTER_VALIDATE_EMAIL) === false) {
            throw new \RuntimeException('Konfiguration oder Adresse ungültig');
        }
        $scheme = $this->secure === 'ssl' ? 'ssl://' : 'tcp://';
        $errno = 0;
        $errstr = '';
        $ctx = stream_context_create(['ssl' => ['verify_peer' => true, 'verify_peer_name' => true, 'SNI_enabled' => true]]);
        $sock = @stream_socket_client($scheme . $this->host . ':' . $this->port, $errno, $errstr, $this->timeout, STREAM_CLIENT_CONNECT, $ctx);
        if ($sock === false) {
            throw new \RuntimeException("Verbindung fehlgeschlagen ($errno)");
        }
        $this->socket = $sock;
        stream_set_timeout($sock, $this->timeout);
        $this->expect(220);
        $helo = preg_replace('/[^A-Za-z0-9.\-]/', '', (string) parse_url('http://' . ($_SERVER['HTTP_HOST'] ?? 'localhost'), PHP_URL_HOST)) ?: 'localhost';
        $this->command("EHLO $helo", 250);
        if ($this->secure === 'tls') {
            $this->command('STARTTLS', 220);
            if (!stream_socket_enable_crypto($sock, true, STREAM_CRYPTO_METHOD_TLSv1_2_CLIENT | STREAM_CRYPTO_METHOD_TLSv1_3_CLIENT)) {
                throw new \RuntimeException('STARTTLS fehlgeschlagen');
            }
            $this->command("EHLO $helo", 250);
        }
        if ($this->user !== '') {
            $this->command('AUTH LOGIN', 334);
            $this->command(base64_encode($this->user), 334, true);
            $this->command(base64_encode($this->pass), 235, true);
        }
        $this->command("MAIL FROM:<$from>", 250);
        $this->command("RCPT TO:<$to>", [250, 251]);
        $this->command('DATA', 354);
        $head = ['Date: ' . date('r'), 'To: <' . $to . '>', 'Subject: ' . $message->encodedSubject(), ...$message->headers(),
                 'Message-ID: <' . bin2hex(random_bytes(12)) . '@' . (explode('@', $from)[1] ?? 'localhost') . '>'];
        $this->write(implode("\r\n", $head) . "\r\n\r\n" . $message->smtpBody() . "\r\n.\r\n");
        $this->expect(250);
    }

    private function write(string $data): void
    {
        if (@fwrite($this->socket, $data) === false) {
            throw new \RuntimeException('Schreiben fehlgeschlagen');
        }
    }

    /** @param int|list<int> $expect */
    private function command(string $line, int|array $expect, bool $secret = false): void
    {
        $this->write($line . "\r\n");
        try {
            $this->expect($expect);
        } catch (\RuntimeException $e) {
            throw new \RuntimeException(($secret ? '[AUTH]' : strtok($line, ' ')) . ': ' . $e->getMessage());
        }
    }

    /** @param int|list<int> $expect */
    private function expect(int|array $expect): void
    {
        $reply = '';
        while (($line = fgets($this->socket, 1024)) !== false) {
            $reply .= $line;
            if (strlen($line) < 4 || $line[3] !== '-') {
                break;
            }
        }
        $code = (int) substr($reply, 0, 3);
        if (!in_array($code, (array) $expect, true)) {
            throw new \RuntimeException('Antwort ' . ($code ?: 'leer'));
        }
    }
}
