/**
 * Cloudflare Worker für wahl-strassenbau.de: statische Seiten aus dist/ (Workers Static Assets, Header in dist/_headers),
 * der Worker selbst bearbeitet nur POST /kontakt.php (siehe app.js) und löscht täglich alte Anfragen (Cron).
 */
import { connect } from 'cloudflare:sockets';
import { handleForm, purge } from './app.js';

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (pathname === '/kontakt.php') return handleForm(request, env, { connect });
    return env.ASSETS.fetch(request);
  },

  async scheduled(controller, env, ctx) {
    ctx.waitUntil(purge(env).then((n) => console.log(`purge: ${n} Anfrage(n) älter als RETENTION_DAYS gelöscht`)));
  },
};
