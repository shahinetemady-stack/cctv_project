const path = require('path');
const qrcode = require('qrcode-terminal');
const pino = require('pino');
const {
  default: makeWASocket,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
  DisconnectReason,
} = require('@whiskeysockets/baileys');

const { callGemini } = require('./gemini');
const db = require('./db');

const logger = pino({ level: process.env.LOG_LEVEL || 'warn' });
const startedAt = Math.floor(Date.now() / 1000);

const sleep = ms => new Promise(r => setTimeout(r, ms));
const humanDelay = () => 3000 + Math.floor(Math.random() * 4000); // 3-7s

function extractText(msg) {
  const m = msg.message || {};
  return (
    m.conversation ||
    m.extendedTextMessage?.text ||
    m.imageMessage?.caption ||
    m.videoMessage?.caption ||
    ''
  ).trim();
}

async function startAccount(account) {
  const { id } = account;
  const authDir = path.join(__dirname, '..', 'sessions', id);
  const { state, saveCreds } = await useMultiFileAuthState(authDir);
  const { version } = await fetchLatestBaileysVersion();

  const sock = makeWASocket({
    version,
    auth: { creds: state.creds, keys: makeCacheableSignalKeyStore(state.keys, logger) },
    logger,
    printQRInTerminal: false,
    markOnlineOnConnect: false,
    syncFullHistory: false,
    browser: ['Ubuntu', 'Chrome', '22.0.0'],
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async (u) => {
    if (u.qr) {
      console.log(`\n===== [${id}] QR — با واتساپ اسکن کن (دستگاه‌های متصل > اتصال دستگاه) =====`);
      qrcode.generate(u.qr, { small: true });
    }
    if (u.connection === 'open') {
      console.log(`[${id}] connected ✅`);
    }
    if (u.connection === 'close') {
      const code = u.lastDisconnect?.error?.output?.statusCode;
      console.log(`[${id}] connection closed (code ${code})`);
      if (code === DisconnectReason.loggedOut) {
        console.log(`[${id}] logged out — سشن را پاک و دوباره پیر کن: rm -rf sessions/${id}`);
        return;
      }
      await sleep(5000);
      startAccount(account).catch(e => console.error(`[${id}] restart failed:`, e.message));
    }
  });

  // serialize replies per conversation so messages never overlap
  const queues = new Map();
  const enqueue = (jid, task) => {
    const prev = queues.get(jid) || Promise.resolve();
    const next = prev.then(task).catch(e => console.error(`[${id}] reply error:`, e.message));
    queues.set(jid, next.finally(() => { if (queues.get(jid) === next) queues.delete(jid); }));
  };

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;
    for (const msg of messages) {
      try {
        const jid = msg.key.remoteJid;
        if (!jid || msg.key.fromMe) continue;
        if (jid === 'status@broadcast') continue;
        if (jid.endsWith('@g.us') && process.env.REPLY_GROUPS !== 'true') continue;
        if (Number(msg.messageTimestamp) < startedAt) continue; // ignore backlog

        const text = extractText(msg);
        if (!text) continue;

        console.log(`[${id}] ${jid}: ${text.slice(0, 80)}`);
        db.logMessage(id, jid, 'user', text);

        enqueue(jid, async () => {
          await sock.presenceSubscribe(jid).catch(() => {});
          await sock.sendPresenceUpdate('composing', jid).catch(() => {});
          await sleep(humanDelay());

          const history = db.getHistory(id, jid).slice(0, -1); // exclude the msg we just logged
          const reply = await callGemini(account.prompt, history, text);

          await sock.sendPresenceUpdate('paused', jid).catch(() => {});
          await sock.sendMessage(jid, { text: reply });
          db.logMessage(id, jid, 'model', reply);
          console.log(`[${id}] -> ${jid}: ${reply.slice(0, 80)}`);
        });
      } catch (e) {
        console.error(`[${id}] handler error:`, e.message);
      }
    }
  });

  return sock;
}

module.exports = { startAccount };
