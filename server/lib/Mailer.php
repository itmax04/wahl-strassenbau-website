<?php
declare(strict_types=1);

namespace Wahl;

/** Austauschbarer Versandweg (ADR-0001): log | mail | smtp. */
interface Mailer
{
    /** true = übergeben/gesendet. Wirft keine Ausnahmen nach außen. */
    public function send(Message $message): bool;
}
