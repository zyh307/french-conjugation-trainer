import { readFileSync, readdirSync, mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
const root = fileURLToPath(new URL('../', import.meta.url));
function csv(text) {
  const rows = []; let row = [], field = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') { if (quoted && text[i + 1] === '"') { field += '"'; i++; } else quoted = !quoted; }
    else if (c === ',' && !quoted) { row.push(field.trim()); field = ''; }
    else if ((c === '\n' || c === '\r') && !quoted) { if (c === '\r' && text[i + 1] === '\n') i++; row.push(field.trim()); if (row.some(Boolean)) rows.push(row); row = []; field = ''; }
    else field += c;
  }
  if (field || row.length) { row.push(field.trim()); rows.push(row); }
  return rows;
}
const data = {};
let count = 0;
for (const level of ['必会', '常用', '生僻']) {
  data[level] = {};
  for (const tense of ['现在时', '复合过去时', '未完成过去时']) {
    const rows = csv(readFileSync(join(root, 'wordlists', level, `${tense}.csv`), 'utf8').replace(/^\uFEFF/, ''));
    const verbs = data[level][tense] = {};
    for (const [verb, , originalPerson, conjugation] of rows.slice(1)) {
      if (!verb || !originalPerson || !conjugation) continue;
      const person = ({ elle: 'il', elles: 'ils' })[originalPerson] || originalPerson;
      (verbs[verb] ||= {})[person] = conjugation; count++;
    }
  }
}
mkdirSync(join(root, 'src/generated'), { recursive: true });
writeFileSync(join(root, 'src/generated/wordlists.json'), JSON.stringify(data));
console.log(`Bundled 9 wordlists, ${count} conjugations for offline use.`);
