<?php
/**
 * Vorlage: als server/config.local.php kopieren (diese Datei ist per .gitignore ausgeschlossen) und anpassen.
 * Umgebungsvariablen gleichen Namens haben Vorrang. Ohne Konfiguration gilt: MAIL_TRANSPORT=log, Speicher storage/.
 */
return [
    'RECIPIENT'        => 'info@wahl-strassenbau.de',      // Empfänger der Anfragen
    'FROM_ADDRESS'     => 'noreply@wahl-strassenbau.de',   // Absender; Domain muss beim Hoster für den Versand erlaubt sein (SPF/DKIM)
    'MAIL_TRANSPORT'   => 'mail',                          // log (nur Datei) | mail (PHP mail()) | smtp
    'SMTP_HOST'        => '',
    'SMTP_PORT'        => '587',
    'SMTP_USER'        => '',
    'SMTP_PASS'        => '',
    'SMTP_SECURE'      => 'tls',                           // tls (STARTTLS, Port 587) | ssl (Port 465) | none
    'STORAGE_PATH'     => __DIR__ . '/../storage',         // besser außerhalb des Webroots, z. B. /home/kunde/wahl-storage
    'RETENTION_DAYS'   => '90',                            // Anfragen werden nach dieser Zahl von Tagen gelöscht
    'RATE_LIMIT'       => '5/600',                         // max. 5 Anfragen je 10 Minuten und Absender
    'MIN_FILL_SECONDS' => '3',
    'CLIENT_IP_HEADER' => '',                            // nur hinter Proxy/CDN, z. B. 'HTTP_CF_CONNECTING_IP' oder 'HTTP_X_FORWARDED_FOR'
    'ALLOWED_ORIGINS'  => 'https://www.wahl-strassenbau.de,https://wahl-strassenbau.de',
];
