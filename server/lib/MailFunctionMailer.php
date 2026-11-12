<?php
declare(strict_types=1);

namespace Wahl;

/** Versand über PHP mail() des Hostings. */
final class MailFunctionMailer implements Mailer
{
    public function send(Message $message): bool
    {
        $to = Validator::line($message->to);
        if (filter_var($to, FILTER_VALIDATE_EMAIL) === false) {
            return false;
        }
        $params = '-f' . escapeshellarg(Validator::line(Config::get('FROM_ADDRESS')));
        return @mail($to, $message->encodedSubject(), str_replace("\r\n", "\n", $message->encodedBody()), implode("\r\n", $message->headers()), $params);
    }
}
