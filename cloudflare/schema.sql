-- D1-Schema für die Formular-Anfragen (wie server/lib/SubmissionStore.php). Der Worker legt es beim ersten Zugriff
-- auch selbst an; diese Datei ist für «wrangler d1 execute wahl-forms --remote --file schema.sql».
CREATE TABLE IF NOT EXISTS submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  form TEXT NOT NULL,
  name TEXT NOT NULL DEFAULT '',
  email TEXT NOT NULL DEFAULT '',
  phone TEXT NOT NULL DEFAULT '',
  service TEXT NOT NULL DEFAULT '',
  message TEXT NOT NULL DEFAULT '',
  order_no TEXT NOT NULL DEFAULT '',
  items TEXT NOT NULL DEFAULT '',
  consent_at TEXT,
  mail_status TEXT NOT NULL DEFAULT 'pending'
);
CREATE INDEX IF NOT EXISTS submissions_created ON submissions(created_at);
CREATE TABLE IF NOT EXISTS rate_limit (key_hash TEXT PRIMARY KEY, window_start INTEGER NOT NULL, count INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
