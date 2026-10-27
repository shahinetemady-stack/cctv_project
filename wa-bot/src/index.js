const db = require('./db');

async function main() {
  const accounts = db.getEnabledAccounts();
  if (accounts.length === 0) {
    console.log('هیچ اکانتی تعریف نشده. اول اضافه کن:');
    console.log('  npm run add-account -- acc1 "فروشگاه دوربینکار"');
    process.exit(1);
  }

  console.log(`starting ${accounts.length} account(s): ${accounts.map(a => a.id).join(', ')}`);
  const { startAccount } = require('./sessionManager');

  for (const [i, account] of accounts.entries()) {
    await new Promise(r => setTimeout(r, i * 5000)); // staggered start
    startAccount(account).catch(e => console.error(`[${account.id}] failed to start:`, e.message));
  }
}

process.on('SIGTERM', () => process.exit(0));
process.on('SIGINT', () => process.exit(0));

main();
