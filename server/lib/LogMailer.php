<?php
declare(strict_types=1);

namespace Wahl;

/** Lokal und in Tests: schreibt die Nachricht in storage/mail.log statt sie zu senden. */
final class LogMailer implements Mailer
{
    public function __construct(private readonly string $file)
    {
    }

    public function send(Message $message): bool
    {
        $entry = '[' . date('c') . '] An: ' . Validator::line($message->to) . "\n"
            . 'Subject: ' . $message->encodedSubject() . "\n"
            . 'Betreff (lesbar): ' . Validator::line($message->subject) . "\n"
            . implode("\n", $message->headers()) . "\n\n"
            . $message->body . "\n" . str_repeat('-', 60) . "\n";
        return @file_put_contents($this->file, $entry, FILE_APPEND | LOCK_EX) !== false;
    }
}
