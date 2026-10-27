const Database = require('better-sqlite3');
const path = require('path');

const db = new Database(path.join(__dirname, '..', 'data', 'bot.db'));
db.pragma('journal_mode = WAL');

db.exec(`
CREATE TABLE IF NOT EXISTS accounts (
  id         TEXT PRIMARY KEY,
  label      TEXT NOT NULL,
  prompt     TEXT NOT NULL DEFAULT '',
  enabled    INTEGER NOT NULL DEFAULT 1,
  created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE TABLE IF NOT EXISTS messages (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id TEXT NOT NULL,
  jid        TEXT NOT NULL,
  role       TEXT NOT NULL CHECK (role IN ('user','model')),
  text       TEXT NOT NULL,
  ts         INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages (account_id, jid, id);
`);

const HISTORY_LIMIT = 20;

function getEnabledAccounts() {
  return db.prepare('SELECT * FROM accounts WHERE enabled = 1').all();
}

function addAccount(id, label, prompt = '') {
  db.prepare('INSERT OR IGNORE INTO accounts (id, label, prompt) VALUES (?, ?, ?)').run(id, label, prompt);
}

function setPrompt(id, prompt) {
  db.prepare('UPDATE accounts SET prompt = ? WHERE id = ?').run(prompt, id);
}

function setEnabled(id, enabled) {
  db.prepare('UPDATE accounts SET enabled = ? WHERE id = ?').run(enabled ? 1 : 0, id);
}

function logMessage(accountId, jid, role, text) {
  db.prepare('INSERT INTO messages (account_id, jid, role, text) VALUES (?, ?, ?, ?)')
    .run(accountId, jid, role, text);
  // keep only the last HISTORY_LIMIT messages per conversation
  db.prepare(`
    DELETE FROM messages WHERE account_id = ? AND jid = ? AND id NOT IN (
      SELECT id FROM messages WHERE account_id = ? AND jid = ? ORDER BY id DESC LIMIT ?
    )`).run(accountId, jid, accountId, jid, HISTORY_LIMIT);
}

function getHistory(accountId, jid) {
  return db.prepare(
    'SELECT role, text FROM messages WHERE account_id = ? AND jid = ? ORDER BY id ASC'
  ).all(accountId, jid);
}

module.exports = { getEnabledAccounts, addAccount, setPrompt, setEnabled, logMessage, getHistory, HISTORY_LIMIT };
