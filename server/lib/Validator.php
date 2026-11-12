<?php
declare(strict_types=1);

namespace Wahl;

/**
 * Normalisierung und Prüfung der drei Formulare (spec §5–§6, R-05.3/R-05.4).
 * Regeln entsprechen dem Client (main.js), Texte kommen aus server/messages.json (dieselbe Quelle wie build.py).
 */
final class Validator
{
    /** Gleiche Liste wie build.py → SERVICES. */
    public const SERVICES = ['Pflasterarbeiten', 'Garten & Landschaft', 'Asphalt- & Erdarbeiten', 'Havarie', 'Sonstiges'];
    public const FORMS = ['kontakt', 'kurz', 'widerruf'];
    private const PHONE_RE = '/^[0-9+()\/\s.\-]{5,40}$/';

    /** Feld => [Typ, Maximallänge] */
    private const FIELDS = [
        'name'          => ['line', 100],
        'email'         => ['line', 200],
        'telefon'       => ['line', 40],
        'leistung'      => ['line', 60],
        'nachricht'     => ['text', 5000],
        'bestellnummer' => ['line', 100],
        'artikel'       => ['text', 300],
    ];

    /** Pflichtfelder je Formular (Einwilligung separat). */
    private const REQUIRED = [
        'kontakt'  => ['name', 'email', 'nachricht'],
        'kurz'     => ['name', 'telefon', 'nachricht'],
        'widerruf' => ['name', 'bestellnummer', 'email'],
    ];

    /** Einzeiliges Feld: Steuerzeichen inkl. CR/LF entfernen (Header-Injection), Leerraum zusammenfassen. */
    public static function line(mixed $v): string
    {
        $s = is_string($v) ? $v : '';
        $s = preg_replace('/[\x00-\x1F\x7F]+/u', ' ', $s) ?? '';
        return trim(preg_replace('/\s{2,}/u', ' ', $s) ?? '');
    }

    /** Mehrzeiliges Feld: Zeilenumbrüche vereinheitlichen, übrige Steuerzeichen entfernen. */
    public static function text(mixed $v): string
    {
        $s = is_string($v) ? $v : '';
        $s = str_replace(["\r\n", "\r"], "\n", $s);
        $s = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $s) ?? '';
        return trim($s);
    }

    /**
     * @param array<string,mixed> $post
     * @return array{0: array<string,string>, 1: array<string,string>} [bereinigte Werte, Fehler je Feld]
     */
    public static function validate(string $form, array $post): array
    {
        $m = messages();
        $data = [];
        $errors = [];
        foreach (self::FIELDS as $key => [$type, $max]) {
            $value = $type === 'line' ? self::line($post[$key] ?? '') : self::text($post[$key] ?? '');
            if (!mb_check_encoding($value, 'UTF-8')) {
                $value = '';
            }
            $data[$key] = $value;
            if (mb_strlen($value) > $max) {
                $errors[$key] = sprintf($m['toolong'], $max);
            }
        }
        $data['einwilligung'] = (($post['einwilligung'] ?? '') === 'ja') ? 'ja' : '';

        foreach (self::REQUIRED[$form] as $key) {
            if ($data[$key] === '' && !isset($errors[$key])) {
                $errors[$key] = $key === 'nachricht' ? $m['nachricht'] : $m['required'];
            }
        }
        if ($data['email'] !== '' && !isset($errors['email'])
            && (filter_var($data['email'], FILTER_VALIDATE_EMAIL) === false || !preg_match('/\.[^.@\s]{2,}$/', $data['email']))) {
            $errors['email'] = $m['email'];
        }
        if ($data['telefon'] !== '' && !isset($errors['telefon']) && preg_match(self::PHONE_RE, $data['telefon']) !== 1) {
            $errors['telefon'] = $m['telefon'];
        }
        if ($data['nachricht'] !== '' && !isset($errors['nachricht']) && $form !== 'widerruf' && mb_strlen($data['nachricht']) < 5) {
            $errors['nachricht'] = $m['nachricht'];
        }
        if ($data['leistung'] !== '' && !in_array($data['leistung'], self::SERVICES, true)) {
            $errors['leistung'] = $m['leistung'];
        }
        if ($form !== 'widerruf' && $data['einwilligung'] !== 'ja') {
            $errors['einwilligung'] = $m['einwilligung'];
        }

        // Nur die Felder des jeweiligen Formulars behalten (Datensparsamkeit)
        $keep = match ($form) {
            'kontakt'  => ['name', 'email', 'telefon', 'leistung', 'nachricht'],
            'kurz'     => ['name', 'telefon', 'nachricht'],
            'widerruf' => ['name', 'bestellnummer', 'email', 'artikel', 'nachricht'],
        };
        $clean = array_intersect_key($data, array_flip($keep));
        return [$clean, array_intersect_key($errors, array_flip([...$keep, 'einwilligung']))];
    }
}
