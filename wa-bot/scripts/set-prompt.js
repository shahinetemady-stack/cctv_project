const fs = require('fs');
const db = require('../src/db');

const [id, file] = process.argv.slice(2);
if (!id || !file) {
  console.log('usage: npm run set-prompt -- <account-id> <prompt-file>');
  console.log('example: npm run set-prompt -- acc1 prompts/doorbinkar.txt');
  process.exit(1);
}

const prompt = fs.readFileSync(file, 'utf8');
db.setPrompt(id, prompt);
console.log(`prompt for '${id}' updated (${prompt.length} chars).`);
