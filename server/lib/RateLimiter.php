<?php
declare(strict_types=1);

namespace Wahl;

/**
 * Begrenzung je Absender: Schlüssel = sha256(IP + Tagessalz). Das Salz liegt in der Datenbank und wechselt täglich,
 * die rohe IP wird nie gespeichert; Einträge leben höchstens 24 h (SubmissionStore::purge).
 */
final class RateLimiter
{
    public function __construct(private readonly SubmissionStore $store, private readonly int $limit, private readonly int $window)
    {
    }

    public static function fromConfig(SubmissionStore $store): self
    {
        [$n, $sec] = array_map('intval', explode('/', Config::get('RATE_LIMIT') . '/600'));
        return new self($store, max(1, $n), max(1, $sec));
    }

    private function key(string $ip): string
    {
        $day = gmdate('Y-m-d');
        $salt = $this->store->meta('salt_' . $day);
        if ($salt === null) {
            $salt = bin2hex(random_bytes(32));
            $this->store->setMeta('salt_' . $day, $salt);
            $this->store->pdo()->prepare("DELETE FROM meta WHERE key LIKE 'salt_%' AND key <> :k")->execute([':k' => 'salt_' . $day]);
        }
        return hash('sha256', $ip . '|' . $salt);
    }

    /** Zählt den Versuch und meldet, ob er erlaubt ist. */
    public function hit(string $ip): bool
    {
        $pdo = $this->store->pdo();
        $key = $this->key($ip);
        $now = time();
        $pdo->beginTransaction();
        try {
            $st = $pdo->prepare('SELECT window_start, count FROM rate_limit WHERE key_hash = :k');
            $st->execute([':k' => $key]);
            $row = $st->fetch();
            if (!$row || $now - (int) $row['window_start'] >= $this->window) {
                $pdo->prepare('INSERT INTO rate_limit (key_hash, window_start, count) VALUES (:k, :t, 1)
                    ON CONFLICT(key_hash) DO UPDATE SET window_start = :t, count = 1')->execute([':k' => $key, ':t' => $now]);
                $pdo->commit();
                return true;
            }
            $count = (int) $row['count'] + 1;
            $pdo->prepare('UPDATE rate_limit SET count = :c WHERE key_hash = :k')->execute([':c' => $count, ':k' => $key]);
            $pdo->commit();
            return $count <= $this->limit;
        } catch (\Throwable $e) {
            $pdo->rollBack();
            throw $e;
        }
    }
}
