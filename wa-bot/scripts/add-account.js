const db = require('../src/db');

const [id, ...labelParts] = process.argv.slice(2);
const label = labelParts.join(' ');

if (!id || !label) {
  console.log('usage: npm run add-account -- <id> <label>');
  console.log('example: npm run add-account -- acc1 "فروشگاه دوربینکار"');
  process.exit(1);
}

db.addAccount(id, label);
console.log(`account '${id}' (${label}) added.`);
console.log(`بعد از استارت سرویس، QR مخصوصش در لاگ چاپ می‌شود: journalctl -u wa-bot -f`);
