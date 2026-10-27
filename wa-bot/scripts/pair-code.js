// pairing با کد به‌جای QR — برای وقتی که به صفحه مانیتور دسترسی نداری
// usage: npm run pair-code -- <account-id> <phone>
// مثال: npm run pair-code -- acc1 989121234567
const path = require('path');
const pino = require('pino');
const {
  default: makeWASocket,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
} = require('@whiskeysockets/baileys');

const [id, phone] = process.argv.slice(2);
if (!id || !phone) {
  console.log('usage: npm run pair-code -- <account-id> <phone>');
  console.log('example: npm run pair-code -- acc1 989121234567');
  process.exit(1);
}
const cleanPhone = phone.replace(/[^0-9]/g, '');

async function main() {
  const authDir = path.join(__dirname, '..', 'sessions', id);
  const { state, saveCreds } = await useMultiFileAuthState(authDir);
  const { version } = await fetchLatestBaileysVersion();

  const sock = makeWASocket({
    version,
    auth: { creds: state.creds, keys: makeCacheableSignalKeyStore(state.keys, pino({ level: 'warn' })) },
    logger: pino({ level: 'warn' }),
    printQRInTerminal: false,
    markOnlineOnConnect: false,
    browser: ['Ubuntu', 'Chrome', '22.0.0'],
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', (u) => {
    if (u.connection === 'open') {
      console.log(`\n✅ [${id}] paired successfully! حالا سرویس را استارت کن: sudo systemctl start wa-bot`);
      setTimeout(() => process.exit(0), 1500);
    }
    if (u.connection === 'close') {
      console.log('connection closed before pairing — دوباره تلاش کن');
      process.exit(1);
    }
  });

  await new Promise(r => setTimeout(r, 3000));
  const code = await sock.requestPairingCode(cleanPhone);
  console.log(`\n===== کد پیرینگ [${id}]: ${code} =====`);
  console.log('توی واتساپ: تنظیمات ← دستگاه‌های متصل ← اتصال دستگاه ← «اتصال با شماره تلفن» ← این کد را وارد کن');
  console.log('(چند دقیقه اعتبار دارد)\n');
}

main().catch(e => { console.error('error:', e.message); process.exit(1); });
