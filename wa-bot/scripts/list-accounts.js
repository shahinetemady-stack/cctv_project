const db = require('../src/db');

const accounts = db.getEnabledAccounts();
if (accounts.length === 0) {
  console.log('(no accounts)');
} else {
  for (const a of accounts) {
    console.log(`${a.id}  |  ${a.label}  |  prompt: ${a.prompt ? a.prompt.length + ' chars' : '(none)'}`);
  }
}
