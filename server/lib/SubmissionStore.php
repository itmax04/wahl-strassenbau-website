<?php
declare(strict_types=1);

namespace Wahl;

use PDO;

/**
 * Kopie jeder gültigen Anfrage in SQLite (ADR-0001 Punkt 2). Nur Formularfelder und Einwilligungszeitpunkt, keine IP.
 * Ausschließlich vorbereitete Anweisungen. Schema wird beim ersten Zugriff angelegt.
 */
final class SubmissionStore
{
    private PDO $db;

    public function __construct(string $path)
    {
        $this->db = new PDO('sqlite:' . $path, null, null, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);
        @chmod($path, 0600);
        $this->db->exec('PRAGMA busy_timeout = 3000');
        $this->db->exec('CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            form TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT \'\',
            email TEXT NOT NULL DEFAULT \'\',
            phone TEXT NOT NULL DEFAULT \'\',
            service TEXT NOT NULL DEFAULT \'\',
            message TEXT NOT NULL DEFAULT \'\',
            order_no TEXT NOT NULL DEFAULT \'\',
            items TEXT NOT NULL DEFAULT \'\',
            consent_at TEXT,
            mail_status TEXT NOT NULL DEFAULT \'pending\'
        )');
        $this->db->exec('CREATE INDEX IF NOT EXISTS submissions_created ON submissions(created_at)');
        $this->db->exec('CREATE TABLE IF NOT EXISTS rate_limit (key_hash TEXT PRIMARY KEY, window_start INTEGER NOT NULL, count INTEGER NOT NULL)');
        $this->db->exec('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)');
    }

    public function pdo(): PDO
    {
        return $this->db;
    }

    /** @param array<string,string> $d bereinigte Werte aus Validator */
    public function insert(string $form, array $d, ?string $consentAt): int
    {
        $st = $this->db->prepare('INSERT INTO submissions (created_at, form, name, email, phone, service, message, order_no, items, consent_at)
            VALUES (:created, :form, :name, :email, :phone, :service, :message, :order_no, :items, :consent)');
        $st->execute([
            ':created' => gmdate('Y-m-d\TH:i:s\Z'), ':form' => $form,
            ':name' => $d['name'] ?? '', ':email' => $d['email'] ?? '', ':phone' => $d['telefon'] ?? '',
            ':service' => $d['leistung'] ?? '', ':message' => $d['nachricht'] ?? '', ':order_no' => $d['bestellnummer'] ?? '',
            ':items' => $d['artikel'] ?? '', ':consent' => $consentAt,
        ]);
        return (int) $this->db->lastInsertId();
    }

    public function setMailStatus(int $id, string $status): void
    {
        $this->db->prepare('UPDATE submissions SET mail_status = :s WHERE id = :id')->execute([':s' => $status, ':id' => $id]);
    }

    /** Löscht Anfragen älter als $days Tage und Rate-Limit-Einträge älter als 24 h. Rückgabe: gelöschte Anfragen. */
    public function purge(int $days): int
    {
        $cutoff = gmdate('Y-m-d\TH:i:s\Z', time() - max(1, $days) * 86400);
        $st = $this->db->prepare('DELETE FROM submissions WHERE created_at < :c');
        $st->execute([':c' => $cutoff]);
        $this->db->prepare('DELETE FROM rate_limit WHERE window_start < :t')->execute([':t' => time() - 86400]);
        return $st->rowCount();
    }

    /** @return list<array<string,mixed>> */
    public function list(?int $days = null): array
    {
        if ($days === null) {
            return $this->db->query('SELECT * FROM submissions ORDER BY id')->fetchAll();
        }
        $st = $this->db->prepare('SELECT * FROM submissions WHERE created_at >= :c ORDER BY id');
        $st->execute([':c' => gmdate('Y-m-d\TH:i:s\Z', time() - $days * 86400)]);
        return $st->fetchAll();
    }

    public function meta(string $key): ?string
    {
        $st = $this->db->prepare('SELECT value FROM meta WHERE key = :k');
        $st->execute([':k' => $key]);
        $v = $st->fetchColumn();
        return $v === false ? null : (string) $v;
    }

    public function setMeta(string $key, string $value): void
    {
        $this->db->prepare('INSERT INTO meta (key, value) VALUES (:k, :v) ON CONFLICT(key) DO UPDATE SET value = excluded.value')
            ->execute([':k' => $key, ':v' => $value]);
    }
}
