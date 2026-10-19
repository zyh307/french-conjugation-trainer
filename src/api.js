export const isDevice = import.meta.env.VITE_APP_STORAGE === 'device';
export async function request(path, body) {
  if (isDevice) { const { deviceRequest } = await import('./device-api.js'); return deviceRequest(path, body); }
  const response = await fetch(`/api/${path}`, {
    ...(body !== undefined ? { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Conjugaison-Client': '3.0' }, body: JSON.stringify(body) } : {}),
  });
  let data;
  try { data = await response.json(); } catch { throw new Error('本地服务没有返回有效数据，请确认服务正在运行。'); }
  if (!response.ok) throw new Error(data.error || '操作未完成，请重试。');
  return data;
}

export const persons = ['je', 'tu', 'il', 'nous', 'vous', 'ils'];
export const personLabel = p => ({ il: 'il / elle', ils: 'ils / elles' }[p] || p);
export const tenses = ['现在时', '复合过去时', '未完成过去时'];
export const tenseFrench = { '现在时': 'Présent', '复合过去时': 'Passé composé', '未完成过去时': 'Imparfait' };
export const levels = ['必会', '常用', '生僻'];
export const roundNames = { judge: '掌握度判断', reverse: '反向选择', choice: '选择变位', fill: '拼写练习' };
export const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase();
export function todayKey(offset = 0) {
  const date = new Date(); date.setDate(date.getDate() + offset);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
export function groupedMastered(items) {
  const groups = new Map();
  for (const item of items) {
    const key = `${item.verbe}|${item.temps}`;
    if (!groups.has(key)) groups.set(key, { key, verbe: item.verbe, temps: item.temps, persons: [], date: item.date_learned, days: item.days });
    const group = groups.get(key);
    group.persons.push(item.personne);
    group.date = group.date > item.date_learned ? group.date : item.date_learned;
    group.days = Math.min(group.days, item.days);
  }
  return [...groups.values()];
}
