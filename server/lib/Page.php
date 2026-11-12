<?php
declare(strict_types=1);

namespace Wahl;

use DOMDocument;
use DOMElement;
use DOMXPath;

/**
 * HTML-Antworten ohne JavaScript (ADR-0001 Punkt 4, spec D-05). Kopf/Fuß und Formular-Markup erzeugt build.py
 * in server/templates/, damit es nur eine Quelle gibt. Alle Werte werden über DOM gesetzt bzw. mit htmlspecialchars escaped.
 */
final class Page
{
    private const PHONE_HREF = 'tel:+4938125223941';

    private static function e(string $s): string
    {
        return htmlspecialchars($s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    }

    private static function layout(string $title, string $body): string
    {
        $tpl = (string) @file_get_contents(__DIR__ . '/../templates/layout.html');
        if ($tpl === '') {
            return '<!doctype html><html lang="de"><meta charset="utf-8"><title>' . self::e($title) . '</title>' . $body;
        }
        return str_replace(['{{page_title}}', '{{page_body}}'], [self::e($title . ' – Wahl Straßenbau'), $body], $tpl);
    }

    private static function hero(string $eyebrow, string $title, string $lead): string
    {
        return '<section class="phero phero--plain phero--sm" aria-labelledby="page-title"><div class="wrap phero__inner">'
            . '<div class="phero__body"><p class="eyebrow">' . self::e($eyebrow) . '</p>'
            . '<h1 id="page-title">' . self::e($title) . '</h1><p class="lead">' . $lead . '</p></div></div></section>';
    }

    /**
     * Formular mit Fehlern und den bisherigen Eingaben.
     * @param array<string,string> $errors @param array<string,string> $values
     */
    public static function formError(string $form, array $errors, string $general, array $values): string
    {
        $m = messages();
        $phone = Config::get('PHONE');
        $lead = $general !== ''
            ? self::e($general)
            : self::e($m['summary']) . ' Ihre Angaben sind noch da. Oder rufen Sie uns an: <a class="inline" href="' . self::PHONE_HREF . '">' . self::e($phone) . '</a>';
        $formHtml = self::fillForm($form, $errors, $values);
        $body = self::hero('Kontakt', 'Bitte prüfen Sie Ihre Angaben', $lead)
            . '<section class="sec"><div class="wrap"><div class="panel" style="max-width:760px">' . $formHtml . '</div></div></section>';
        return self::layout('Bitte prüfen Sie Ihre Angaben', $body);
    }

    /** D-05: Bestätigung des Widerrufs; Text aus der gebauten Seite /j/withdrawal/ (#widerruf-done). */
    public static function widerrufDone(): string
    {
        $built = (string) @file_get_contents(ROOT . '/j/withdrawal/index.html');
        $done = '';
        if (preg_match('#<div class="done" id="widerruf-done"[^>]*>(.*?)</div>\s*</div>\s*</div>\s*</section>#s', $built, $mm)) {
            $done = $mm[1];
        }
        $body = '<section class="sec"><div class="wrap"><div class="panel" style="max-width:760px"><div class="done">' . $done
            . '<a class="btn btn--secondary" href="/">Zur Startseite</a></div></div></div></section>';
        return self::layout('Widerruf eingegangen', $body);
    }

    /** Setzt Werte, Fehlermeldungen, aria-invalid und die Fehlerübersicht im Formular-Markup aus build.py. */
    private static function fillForm(string $form, array $errors, array $values): string
    {
        $html = (string) @file_get_contents(__DIR__ . '/../templates/form-' . $form . '.html');
        if ($html === '') {
            return '';
        }
        $doc = new DOMDocument();
        libxml_use_internal_errors(true);
        $doc->loadHTML('<?xml encoding="UTF-8"><div id="root">' . $html . '</div>', LIBXML_HTML_NOIMPLIED | LIBXML_HTML_NODEFDTD);
        libxml_clear_errors();
        $xp = new DOMXPath($doc);
        $labels = [];
        foreach ($xp->query('//*[@data-field]') as $field) {
            /** @var DOMElement $field */
            $key = $field->getAttribute('data-field');
            $control = $xp->query('.//input[@name] | .//textarea[@name] | .//select[@name]', $field)->item(0);
            $label = $xp->query('.//label[contains(@class,"field__label")]', $field)->item(0);
            $labels[$key] = $label ? rtrim(trim($label->textContent), ' *') : 'Einwilligung';
            $value = $values[$key] ?? '';
            if ($control instanceof DOMElement) {
                if ($control->tagName === 'textarea') {
                    $control->textContent = $value;
                } elseif ($control->tagName === 'select') {
                    foreach ($xp->query('.//option', $control) as $opt) {
                        /** @var DOMElement $opt */
                        if ($opt->getAttribute('value') === $value && $value !== '') {
                            $opt->setAttribute('selected', 'selected');
                        }
                    }
                } elseif ($control->getAttribute('type') !== 'checkbox') {
                    $control->setAttribute('value', $value);
                }
                if (isset($errors[$key])) {
                    $control->setAttribute('aria-invalid', 'true');
                }
            }
            if (isset($errors[$key])) {
                $field->setAttribute('class', trim($field->getAttribute('class') . ' is-error'));
                $err = $xp->query('.//*[contains(@class,"field__error")]', $field)->item(0);
                if ($err instanceof DOMElement) {
                    $err->textContent = $errors[$key];
                    $err->removeAttribute('hidden');
                }
            }
        }
        $sum = $xp->query('//*[contains(@class,"errsum")]')->item(0);
        if ($sum instanceof DOMElement && $errors) {
            $sum->removeAttribute('hidden');
            $text = $xp->query('.//*[contains(@class,"errsum__text")]', $sum)->item(0);
            if ($text instanceof DOMElement) {
                $others = array_values(array_filter(array_keys($errors), static fn ($k) => $k !== 'einwilligung'));
                if ($others) {
                    $text->appendChild($doc->createTextNode(count($others) === 1 ? '1 Pflichtfeld fehlt oder ist ungültig: ' : count($others) . ' Pflichtfelder fehlen oder sind ungültig: '));
                    foreach ($others as $i => $k) {
                        if ($i) {
                            $text->appendChild($doc->createTextNode(', '));
                        }
                        $a = $doc->createElement('a');
                        $a->setAttribute('href', '#' . $form . '-' . $k);
                        $a->textContent = $labels[$k] ?? $k;
                        $text->appendChild($a);
                    }
                    $text->appendChild($doc->createTextNode('.'));
                }
                if (isset($errors['einwilligung'])) {
                    $text->appendChild($doc->createTextNode($others ? ' Außerdem ist die ' : 'Die '));
                    $a = $doc->createElement('a');
                    $a->setAttribute('href', '#' . $form . '-einwilligung');
                    $a->textContent = 'Einwilligung';
                    $text->appendChild($a);
                    $text->appendChild($doc->createTextNode(' erforderlich.'));
                }
            }
        }
        $root = $doc->getElementById('root');
        $out = '';
        foreach ($root->childNodes as $child) {
            $out .= $doc->saveHTML($child);
        }
        return $out;
    }
}
