<?php
declare(strict_types=1);

/**
 * Fake-SMTP-Server für Tests (ADR-0001): php tests/php/fake_smtp.php <port> <logdatei>
 * Antwortet 220/250/334/235/354/221 ohne TLS, protokolliert den Dialog (C: Client, S: Server) in <logdatei>.
 */

$port = (int) ($argv[1] ?? 2525);
$log = $argv[2] ?? sys_get_temp_dir() . '/fake_smtp.log';
$server = stream_socket_server("tcp://127.0.0.1:$port", $errno, $errstr);
if ($server === false) {
    fwrite(STDERR, "fake_smtp: $errstr\n");
    exit(1);
}
file_put_contents($log, '');
$say = static function ($c, string $line) use ($log): void {
    fwrite($c, $line . "\r\n");
    file_put_contents($log, "S: $line\n", FILE_APPEND);
};
while ($conn = @stream_socket_accept($server, 120)) {
    stream_set_timeout($conn, 10);
    $say($conn, '220 fake.smtp.test ESMTP');
    $inData = false;
    $authStep = 0;
    while (($line = fgets($conn)) !== false) {
        file_put_contents($log, 'C: ' . rtrim($line, "\r\n") . "\n", FILE_APPEND);
        $cmd = strtoupper(rtrim($line, "\r\n"));
        if ($inData) {
            if (rtrim($line, "\r\n") === '.') {
                $inData = false;
                $say($conn, '250 2.0.0 queued');
            }
            continue;
        }
        if ($authStep === 1) { $authStep = 2; $say($conn, '334 UGFzc3dvcmQ6'); continue; }
        if ($authStep === 2) { $authStep = 0; $say($conn, '235 2.7.0 Authentication successful'); continue; }
        if (str_starts_with($cmd, 'EHLO')) {
            fwrite($conn, "250-fake.smtp.test\r\n250 AUTH LOGIN\r\n");
            file_put_contents($log, "S: 250 AUTH LOGIN\n", FILE_APPEND);
        } elseif ($cmd === 'AUTH LOGIN') {
            $authStep = 1;
            $say($conn, '334 VXNlcm5hbWU6');
        } elseif (str_starts_with($cmd, 'MAIL FROM') || str_starts_with($cmd, 'RCPT TO')) {
            $say($conn, '250 OK');
        } elseif ($cmd === 'DATA') {
            $inData = true;
            $say($conn, '354 End data with <CR><LF>.<CR><LF>');
        } elseif ($cmd === 'QUIT') {
            $say($conn, '221 Bye');
            break;
        } else {
            $say($conn, '502 Command not implemented');
        }
    }
    fclose($conn);
}
