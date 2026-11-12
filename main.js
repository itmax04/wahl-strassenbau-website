(() => {
  window.__siteReady = true; // Sicherheitsnetz im <head>: ohne dieses Flag werden animierte Inhalte nach 4 s eingeblendet
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  /* ---- Kopfzeile: Variante „Sticky“ nach 8 px Scrollen (Figma 6:146 / 6:203 / 6:247) ---- */
  const hdr = $('.hdr');
  const totop = $('[data-totop]');
  const onScroll = () => {
    const y = window.scrollY;
    if (hdr) hdr.classList.toggle('is-sticky', y > 8);
    if (totop) totop.classList.toggle('is-visible', y > 600);
  };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  /* ---- Mobiles Menü (Figma 6:437): Fokusfalle, Esc, Scroll-Sperre, Fokus zurück auf den Auslöser ---- */
  const menu = $('#menu');
  const toggle = $('.hdr__menu');
  if (menu && toggle) {
    const close = $('.menu__close', menu);
    let opener = null;
    const setMenu = (open) => {
      toggle.setAttribute('aria-expanded', String(open));
      menu.hidden = !open;
      document.body.classList.toggle('is-locked', open);
      if (open) {
        opener = document.activeElement;
        (close || $(FOCUSABLE, menu)).focus();
      } else if (opener) {
        opener.focus();
        opener = null;
      }
    };
    toggle.addEventListener('click', () => setMenu(true));
    if (close) close.addEventListener('click', () => setMenu(false));
    menu.addEventListener('click', (e) => { if (e.target.closest('a')) setMenu(false); });
    menu.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { e.preventDefault(); setMenu(false); return; }
      if (e.key !== 'Tab') return;
      const items = $$(FOCUSABLE, menu).filter((el) => el.offsetParent !== null);
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
    // Desktop hat kein Menü: beim Vergrößern schließen
    window.matchMedia('(min-width: 1280px)').addEventListener('change', (m) => { if (m.matches && !menu.hidden) setMenu(false); });
  }

  /* ---- Zähler: Kinetics „Odometer Count-up“ (1,4 s, ease-out cubic 1 − (1 − p)³, Auslöser bei 50 % Sichtbarkeit), danach „Number Counter“-Bump ---- */
  const countUp = (el) => {
    const end = Number(el.dataset.count);
    if (!Number.isFinite(end)) return;
    const bump = () => { el.classList.remove('bump'); void el.offsetWidth; el.classList.add('bump'); };
    const t0 = performance.now();
    const step = (t) => {
      const p = Math.min((t - t0) / 1400, 1);
      el.textContent = String(Math.round(end * (1 - Math.pow(1 - p, 3))));
      if (p < 1) requestAnimationFrame(step); else bump();
    };
    requestAnimationFrame(step);
  };
  if ('IntersectionObserver' in window && !reduce) {
    const co = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) { countUp(e.target); co.unobserve(e.target); }
    }), { threshold: 0.5 });
    $$('[data-count]').forEach((el) => co.observe(el));
  }

  /* ---- Stagger Entrance (Kinetics): Auslöser per IntersectionObserver.
         Bereits passierte Elemente (schnelles Scrollen) werden sofort gezeigt, damit nie ein leerer Block stehen bleibt. ---- */
  const groups = $$('[data-stagger]');
  groups.forEach((g) => [...g.children].forEach((c, i) => c.style.setProperty('--i', i)));
  if (reduce || !('IntersectionObserver' in window)) {
    groups.forEach((g) => g.classList.add('is-in'));
  } else {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting && entry.boundingClientRect.top > 0) return;
        entry.target.classList.add('is-in');
        io.unobserve(entry.target);
      });
    }, { threshold: 0.01, rootMargin: '0px 0px -60px 0px' });
    groups.forEach((g) => io.observe(g));
  }

  /* ---- Vorher/Nachher (Kinetics „Before / After“): range-Regler setzt --pct, per Tastatur bedienbar ---- */
  $$('[data-compare]').forEach((box) => {
    const range = $('input[type="range"]', box);
    const update = () => {
      box.style.setProperty('--pct', range.value + '%');
      range.setAttribute('aria-valuetext', `${range.value} % fertig sichtbar`);
    };
    range.addEventListener('input', update);
    update();
  });

  /* ---- Inhaltsverzeichnis (Rechtstexte): Scroll-Spy für die Desktop-Spalte, mobile Liste schließt nach Auswahl ---- */
  const tocLinks = $$('.toc a');
  if (tocLinks.length && 'IntersectionObserver' in window) {
    const map = new Map(tocLinks.map((a) => [decodeURIComponent(a.getAttribute('href').slice(1)), a]));
    const visible = new Set();
    const mark = () => {
      const ids = [...map.keys()];
      const current = ids.find((id) => visible.has(id));
      if (!current) return;
      tocLinks.forEach((l) => l.removeAttribute('aria-current'));
      map.get(current).setAttribute('aria-current', 'location');
    };
    const so = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) visible.add(e.target.id); else visible.delete(e.target.id); });
      mark();
    }, { rootMargin: '-20% 0px -65% 0px' });
    map.forEach((_, id) => { const h = document.getElementById(id); if (h) so.observe(h); });
    tocLinks[0].setAttribute('aria-current', 'location');
  }
  $$('.tocm a').forEach((a) => a.addEventListener('click', () => { const d = a.closest('details'); if (d) d.open = false; }));

  /* ---- Bildansicht (natives <dialog>): Pfeile, Esc, Wischen, Fokus zurück auf die Kachel ---- */
  const shots = $$('a[data-lightbox]');
  if (shots.length && typeof HTMLDialogElement === 'function') {
    const svg = (d) => `<svg class="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
    const dlg = document.createElement('dialog');
    dlg.className = 'lightbox';
    dlg.setAttribute('aria-label', 'Bildansicht');
    dlg.innerHTML =
      `<button class="iconbtn iconbtn--outline lightbox__close" type="button" aria-label="Schließen">${svg('<path d="M18 6L6 18"/><path d="M6 6l12 12"/>')}</button>` +
      `<button class="iconbtn iconbtn--outline lightbox__prev" type="button" aria-label="Vorheriges Bild">${svg('<path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/>')}</button>` +
      '<figure><img alt="" draggable="false"></figure>' +
      `<button class="iconbtn iconbtn--outline lightbox__next" type="button" aria-label="Nächstes Bild">${svg('<path d="M5 12h14"/><path d="M12 5l7 7-7 7"/>')}</button>` +
      '<div class="lightbox__bar"><span class="lightbox__count" aria-live="polite"></span><p class="lightbox__caption"></p></div>';
    document.body.appendChild(dlg);
    const img = $('img', dlg);
    const count = $('.lightbox__count', dlg);
    const caption = $('.lightbox__caption', dlg);
    const fig = $('figure', dlg);
    let idx = 0;
    let opener = null;
    // Nur die Bilder derselben Galerie durchblättern
    let set = shots;
    const preload = (n) => { const a = set[(n + set.length) % set.length]; new Image().src = a.href; };
    const show = (n) => {
      idx = (n + set.length) % set.length;
      const a = set[idx];
      img.src = a.href;
      img.alt = a.dataset.alt || '';
      count.textContent = `${idx + 1} / ${set.length}`;
      caption.textContent = a.dataset.alt || '';
      if (set.length > 1) { preload(idx + 1); preload(idx - 1); }
    };
    shots.forEach((a) => a.addEventListener('click', (e) => {
      e.preventDefault();
      opener = a;
      const scope = a.closest('[data-gallery]');
      set = scope ? $$('a[data-lightbox]', scope) : [a];
      $('.lightbox__prev', dlg).hidden = $('.lightbox__next', dlg).hidden = set.length < 2;
      show(set.indexOf(a));
      dlg.showModal();
      document.body.classList.add('is-locked');
    }));
    $('.lightbox__close', dlg).addEventListener('click', () => dlg.close());
    $('.lightbox__prev', dlg).addEventListener('click', () => show(idx - 1));
    $('.lightbox__next', dlg).addEventListener('click', () => show(idx + 1));
    dlg.addEventListener('click', (e) => { if (e.target === dlg || e.target === fig) dlg.close(); });
    dlg.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') show(idx - 1);
      if (e.key === 'ArrowRight') show(idx + 1);
    });
    dlg.addEventListener('close', () => {
      document.body.classList.remove('is-locked');
      if (opener) opener.focus();
    });
    let sx = 0, sy = 0, tracking = false;
    fig.addEventListener('pointerdown', (e) => { sx = e.clientX; sy = e.clientY; tracking = true; });
    fig.addEventListener('pointerup', (e) => {
      if (!tracking) return;
      tracking = false;
      const dx = e.clientX - sx, dy = e.clientY - sy;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.3) show(idx + (dx < 0 ? 1 : -1));
    });
    fig.addEventListener('pointercancel', () => { tracking = false; });
  }

  /* ---- Formulare: Prüfung im Browser (Texte aus data-msg, erzeugt von build.py), Fehlerübersicht mit Fokus,
         Versand per fetch an /kontakt.php. Ohne JavaScript sendet das Formular normal (POST + 303). ---- */
  const PHONE_RE = /^[0-9+()\/\s.\-]{5,40}$/;
  const EMAIL_RE = /^[^\s@<>()[\]\\,;:"]+@[^\s@<>()[\]\\,;:"]+\.[^\s@<>()[\]\\,;:"]{2,}$/;

  $$('form[data-form]').forEach((form) => {
    const msgs = JSON.parse(form.dataset.msgs || '{}');
    // Ausfüllzeit relativ messen (Sekunden seit dem Laden) — unabhängig von der Uhr des Geräts
    const stamp = $('input[name="t"]', form);
    const loadedAt = performance.now();
    const status = $('.form__status', form);
    const submit = $('[type="submit"]', form);
    const summary = $('.errsum', form);
    const fields = $$('.field', form);
    const control = (f) => $('input:not([type="hidden"]), select, textarea', f);
    const labelOf = (f) => {
      const l = $('.field__label', f);
      return l ? l.textContent.replace(/\s*\*\s*$/, '').trim() : 'Einwilligung';
    };

    const setState = (field, message, ok) => {
      const input = control(field);
      const out = $('.field__error', field);
      field.classList.toggle('is-error', Boolean(message));
      field.classList.toggle('is-ok', !message && Boolean(ok));
      out.textContent = message || '';
      out.hidden = !message;
      if (message) input.setAttribute('aria-invalid', 'true'); else input.removeAttribute('aria-invalid');
    };
    const check = (field) => {
      const input = control(field);
      const value = input.type === 'checkbox' ? (input.checked ? 'ja' : '') : input.value.trim();
      if (input.required && !value) return input.name === 'nachricht' || input.type === 'checkbox' ? input.dataset.msg : (msgs.required || input.dataset.msg);
      if (input.type === 'email' && value && !EMAIL_RE.test(value)) return input.dataset.msg;
      if (input.type === 'tel' && value && !PHONE_RE.test(value)) return input.dataset.msg;
      if (input.name === 'nachricht' && input.required && value.length < 5) return input.dataset.msg;
      return '';
    };
    // Fehlerübersicht wie Frame 07F: „2 Pflichtfelder fehlen oder sind ungültig: E-Mail, Nachricht. Außerdem ist die Einwilligung erforderlich.“
    const fieldLink = (f) => {
      const a = document.createElement('a');
      a.href = '#' + control(f).id;
      a.textContent = labelOf(f);
      a.addEventListener('click', (e) => { e.preventDefault(); control(f).focus(); });
      return a;
    };
    const showSummary = (bad) => {
      if (!summary) return;
      const out = $('.errsum__text', summary);
      out.textContent = '';
      const consent = bad.find((f) => f.dataset.field === 'einwilligung');
      const others = bad.filter((f) => f !== consent);
      if (others.length) {
        out.append(others.length === 1 ? '1 Pflichtfeld fehlt oder ist ungültig: ' : `${others.length} Pflichtfelder fehlen oder sind ungültig: `);
        others.forEach((f, i) => { if (i) out.append(', '); out.append(fieldLink(f)); });
        out.append('.');
      }
      if (consent) {
        const a = fieldLink(consent);
        a.textContent = 'Einwilligung';
        out.append(others.length ? ' Außerdem ist die ' : 'Die ', a, ' erforderlich.');
      }
      summary.hidden = bad.length === 0;
      if (bad.length) summary.focus();
    };
    const validate = () => {
      const bad = [];
      fields.forEach((f) => {
        const msg = check(f);
        const input = control(f);
        const filled = input.type === 'checkbox' ? input.checked : input.value.trim() !== '';
        setState(f, msg, filled);
        if (msg) bad.push(f);
      });
      return bad;
    };
    fields.forEach((f) => {
      const input = control(f);
      const evt = input.type === 'checkbox' || input.tagName === 'SELECT' ? 'change' : 'input';
      input.addEventListener(evt, () => { if (f.classList.contains('is-error')) setState(f, check(f), true); });
      // Erst nach dem ersten Absenden beim Verlassen prüfen: sonst verschiebt die Meldung den Button unter dem Mauszeiger
      input.addEventListener('blur', () => {
        if (!form.classList.contains('was-validated')) return;
        const filled = input.type === 'checkbox' ? input.checked : input.value.trim() !== '';
        if (filled) setState(f, check(f), true);
      });
      if (input.tagName === 'SELECT') {
        const sync = () => input.classList.toggle('is-empty', !input.value);
        input.addEventListener('change', sync);
        sync();
      }
    });
    const setStatus = (text, isError) => {
      status.className = 'form__status' + (isError ? ' is-error' : '');
      status.textContent = text || '';
    };
    let busy = false;
    const setBusy = (on) => {
      busy = on;
      submit.disabled = on;
      submit.classList.toggle('is-busy', on);
      submit.setAttribute('aria-busy', String(on));
      const label = $('.btn__label', submit);
      if (on) { submit.dataset.label = label.textContent; label.textContent = 'Wird gesendet …'; }
      else if (submit.dataset.label) label.textContent = submit.dataset.label;
    };

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (busy) return;
      setStatus('');
      form.classList.add('was-validated');
      const bad = validate();
      if (bad.length) { showSummary(bad); return; }
      if (summary) summary.hidden = true;
      if (stamp) stamp.value = String(Math.floor((performance.now() - loadedAt) / 1000));
      setBusy(true);
      try {
        const res = await fetch(form.action, {
          method: 'POST',
          headers: { Accept: 'application/json', 'X-Requested-With': 'fetch' },
          body: new FormData(form),
          credentials: 'same-origin',
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.ok) {
          if (form.dataset.form === 'widerruf') {
            // D-05: Bestätigung im selben Bereich
            const done = document.getElementById('widerruf-done');
            if (done) {
              if (data.confirmation === false) {
                $('[data-mailed]', done).hidden = true;
                $('[data-nomail]', done).hidden = false;
              }
              form.hidden = true;
              done.hidden = false;
              done.focus();
              return;
            }
          }
          window.location.assign(data.redirect || '/kontakt/danke/');
          return;
        }
        if (res.status === 422 && data.errors) {
          const bad422 = [];
          fields.forEach((f) => {
            const msg = data.errors[control(f).name];
            const c = control(f);
            setState(f, msg || '', !msg && (c.type === 'checkbox' ? c.checked : c.value.trim() !== ''));
            if (msg) bad422.push(f);
          });
          showSummary(bad422);
        } else if (res.status === 429) {
          setStatus(data.error || msgs.rate, true);
        } else {
          setStatus(data.error || msgs.network, true);
        }
      } catch (err) {
        setStatus(msgs.network, true);
      }
      setBusy(false);
    });
  });
})();
