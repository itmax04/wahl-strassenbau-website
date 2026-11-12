<?php
declare(strict_types=1);

/**
 * Formular-Endpunkt für wahl-strassenbau.de: POST /kontakt.php (Formulare kontakt, kurz, widerruf).
 * Dünner Einstieg; die Logik liegt in server/ (ADR-0001). Konfiguration: server/config.local.php oder Umgebungsvariablen,
 * siehe server/config.example.php. Standard-Versand «log» schreibt nach storage/mail.log (keine echten E-Mails).
 */

require __DIR__ . '/server/bootstrap.php';

(new Wahl\FormHandler($_SERVER, $_POST))->handle();
