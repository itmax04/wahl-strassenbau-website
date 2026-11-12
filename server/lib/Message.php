<?php
declare(strict_types=1);

namespace Wahl;

/** Eine Text-E-Mail. Alle Kopfzeilenwerte sind einzeilig (Validator::line), der Betreff wird MIME-kodiert. */
final class Message
{
    public function __construct(
        public readonly string $to,
        public readonly string $subject,
        public readonly string $body,
        public readonly string $replyTo = '',
    ) {
    }

    public function fromHeader(): string
    {
        return mb_encode_mimeheader(Config::get('SITE_NAME'), 'UTF-8', 'B') . ' <' . Validator::line(Config::get('FROM_ADDRESS')) . '>';
    }

    public function encodedSubject(): string
    {
        return mb_encode_mimeheader(Validator::line($this->subject), 'UTF-8', 'B', "\r\n");
    }

    /** @return list<string> Kopfzeilen ohne To/Subject (für mail()) */
    public function headers(): array
    {
        $h = [
            'From: ' . $this->fromHeader(),
            'MIME-Version: 1.0',
            'Content-Type: text/plain; charset=UTF-8',
            'Content-Transfer-Encoding: quoted-printable',
        ];
        $reply = Validator::line($this->replyTo);
        if ($reply !== '' && filter_var($reply, FILTER_VALIDATE_EMAIL) !== false) {
            $h[] = 'Reply-To: ' . $reply;
        }
        return $h;
    }

    /** Text quoted-printable kodiert (Zeilen ≤ 76 Zeichen, RFC 2045) mit CRLF — lange Nachrichtenzeilen verletzen sonst das 998-Zeichen-Limit. */
    public function encodedBody(): string
    {
        return quoted_printable_encode(str_replace(["\r\n", "\r", "\n"], ["\n", "\n", "\r\n"], $this->body));
    }

    /** Für SMTP: wie encodedBody, Zeilen mit «.» am Anfang verdoppelt (Dot-Stuffing). */
    public function smtpBody(): string
    {
        $lines = array_map(static fn (string $l): string => str_starts_with($l, '.') ? '.' . $l : $l, explode("\r\n", $this->encodedBody()));
        return implode("\r\n", $lines);
    }
}
