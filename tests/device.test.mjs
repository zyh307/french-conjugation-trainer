import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DeviceStudio, checkAnswer, practiceHint } from '../src/device-core.js';
import { verbMeanings } from '../src/verb-meanings.js';
import { shareQuotes, nextQuote } from '../src/share-quotes.js';
const wordlists = JSON.parse(readFileSync(new URL('../src/generated/wordlists.json', import.meta.url), 'utf8'));
function setup(clock) {
  const values = new Map();
  const storage = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) };
  return { studio: new DeviceStudio(wordlists, storage, clock), storage };
}
const solve = (studio, q) => studio.request('session/answer', { id: q.id, answer: q.round === 'reverse' ? q.personne : studio.forms(q.verbe, q.temps, q.level)[q.personne] });

test('progress counts only confirmed tasks and updates after every judgment, answer and restart', () => {
  const { studio, storage } = setup();
  let q = studio.request('session/start', { count: 3 });
  assert.deepEqual([q.done, q.total], [0, 3]);
  q = studio.request('session/answer', { id: q.id, choice: 2 }).next;
  assert.deepEqual([q.done, q.total], [1, 21]);
  const old = studio.read(); old.active.question.total = 999; studio.write(old);
  q = new DeviceStudio(wordlists, storage).request('session/resume');
  assert.deepEqual([q.done, q.total], [1, 21]);
  q = studio.request('session/answer', { id: q.id, choice: 1 }).next;
  assert.deepEqual([q.done, q.total], [2, 21]);
  q = studio.request('session/answer', { id: q.id, choice: 3 }).next;
  assert.deepEqual([q.done, q.total], [3, 39]);
  q = studio.request('session/answer', { id: q.id, answer: 'incorrect' }).next;
  assert.deepEqual([q.done, q.total], [3, 39]);
  q = solve(studio, q).next;
  assert.deepEqual([q.done, q.total], [4, 39]);
  let answered = 1;
  while (!q.completed) { q = solve(studio, q).next; answered++; }
  assert.equal(answered, 36);
});

test('future batches and disabled rounds do not inflate the progress total', () => {
  const { studio } = setup();
  studio.request('settings', { enable_reverse: false, enable_fill: false });
  let q = studio.request('session/start', { count: 6 });
  assert.deepEqual([q.done, q.total], [0, 6]);
  q = studio.request('session/answer', { id: q.id, choice: 2 }).next;
  assert.deepEqual([q.done, q.total], [1, 12]);
});

test('hints show length for short or irregular forms without exposing the answer or zero suffixes', () => {
  for (const [verb, form] of [['être', 'suis'], ['avoir', 'ai'], ['aller', 'va'], ['être', 'sommes'], ['parler', 'parle'], ['avoir', 'ai eu']]) {
    const hint = practiceHint(verb, form);
    assert.match(hint, /^答案长度：[1-9]\d* 个字母$/);
    assert.ok(!hint.includes(form));
  }
  assert.equal(practiceHint('parler', 'parlons'), '词干：parl + 后缀（3 个字母）');
  for (const lists of Object.values(wordlists)) for (const verbs of Object.values(lists)) for (const [verb, forms] of Object.entries(verbs)) for (const form of Object.values(forms)) {
    const hint = practiceHint(verb, form);
    assert.doesNotMatch(hint, /[（(]0\s*个/);
    assert.ok(!hint.startsWith(`词干：${form}`));
  }
});

test('familiar judgment enters known book, never review; other tense stays in practice', () => {
  let now = new Date(2026, 9, 1); const { studio } = setup(() => now);
  const q = studio.request('session/start', { count: 1 });
  studio.request('session/answer', { id: q.id, choice: 1 });
  assert.ok(studio.read().mastered.every(m => m.known));
  now = new Date(2026, 9, 2);
  assert.equal(studio.request('state').review.length, 0);
  assert.ok(studio.read().mastered.every(m => m.temps === q.temps));
});

test('notebook moves are exclusive, idempotent, per tense and preserve unrelated progress', () => {
  let now = new Date(2026, 9, 1); const { studio, storage } = setup(() => now);
  const q = studio.request('session/start', { count: 6 });
  const other = q.batch_verbs.find(v => v !== q.verbe);
  const before = studio.read().active.schedule.groups.flatMap(g => g.entries).filter(e => e.verbe !== other);
  studio.request('notebooks/move', { keys: [`${other}|现在时`], target: 'review' });
  assert.equal(studio.read().active.question.id, q.id);
  const after = studio.read().active.schedule.groups.flatMap(g => g.entries);
  assert.deepEqual(after, before);
  assert.equal(studio.read().mastered.length, 6);
  now = new Date(2026, 9, 2);
  studio.request('notebooks/move', { keys: [`${other}|现在时`], target: 'review' });
  assert.ok(studio.read().mastered.every(m => m.date_learned === '2026-10-01'));
  assert.equal(studio.request('state').review.length, 6);
  studio.request('notebooks/move', { keys: [`${other}|现在时`], target: 'known' });
  assert.equal(studio.request('state').review.length, 0);
  assert.equal(studio.read().mastered.length, 6);
  studio.request('favorites/toggle', { verb: other, tense: '现在时', saved: true });
  studio.request('favorites/toggle', { verb: other, tense: '现在时', saved: true });
  assert.equal(studio.request('state').favorites.length, 1);
  studio.request('notebooks/move', { keys: [`${other}|现在时`], target: 'practice' });
  assert.equal(studio.read().mastered.length, 0);
  assert.equal(studio.request('session/resume').id, q.id);
  assert.ok(studio.read().settings.priority_learn.includes(`${other}|现在时|je`));
  assert.equal(new DeviceStudio(wordlists, storage).request('state').favorites.length, 1);
});

test('review book promotes after 30 days including skipped days; partial words stay in practice', () => {
  let now = new Date(2026, 9, 1); const { studio } = setup(() => now);
  studio.request('notebooks/move', { keys: ['être|现在时'], target: 'review' });
  now = new Date(2026, 9, 29);
  assert.ok(studio.request('state').mastered.every(m => !m.known));
  now = new Date(2026, 10, 5);
  assert.ok(studio.request('state').mastered.every(m => m.known));
  assert.equal(studio.request('state').review.length, 0);
  const data = studio.read();
  data.mastered.push({ verbe: 'avoir', temps: '现在时', personne: 'je', date_learned: '2026-10-01' });
  studio.write(data);
  assert.equal(studio.request('state').mastered.find(m => m.verbe === 'avoir').known, undefined);
});

test('moving during direct practice skips only that pair and known repractice preserves dates', () => {
  const { studio } = setup();
  studio.request('favorites/toggle', { verb: 'être', tense: '现在时', saved: true });
  studio.request('favorites/toggle', { verb: 'être', tense: '复合过去时', saved: true });
  studio.request('session/start', { favorites: true });
  let q = studio.request('notebooks/move', { keys: ['être|现在时'], target: 'known' }).next;
  assert.equal(q.temps, '复合过去时');
  while (!q.completed) q = solve(studio, q).next;
  const before = studio.read().mastered.filter(m => m.temps === '现在时');
  q = studio.request('session/start', { verb: 'être', tense: '现在时' });
  while (!q.completed) q = solve(studio, q).next;
  assert.deepEqual(studio.read().mastered.filter(m => m.temps === '现在时'), before);
  assert.equal(studio.request('state').favorites.length, 2);
});
test('direct practice skips judging, isolates the tense, resumes and keeps the regular session', () => {
  const { studio, storage } = setup();
  const regular = studio.request('session/start', { count: 3 });
  const progress = structuredClone(studio.read().progress);
  let q = studio.request('session/start', { verb: 'résoudre', tense: '复合过去时' });
  assert.equal(q.round, 'choice'); assert.equal(q.direct, true); assert.equal(q.verbe, 'résoudre');
  const restarted = new DeviceStudio(wordlists, storage);
  assert.deepEqual(restarted.request('session/resume'), q);
  let count = 0;
  while (!q.completed) {
    assert.equal(q.verbe, 'résoudre'); assert.equal(q.temps, '复合过去时');
    assert.equal(restarted.request('share').today_words, 0);
    q = solve(restarted, q).next; assert.ok(++count <= 18);
  }
  assert.equal(count, 18);
  const state = restarted.request('state'); assert.equal(state.share_stats.today_words, 1);
  assert.equal(state.mastered.length, 6); assert.deepEqual(restarted.read().progress, progress);
  assert.equal(restarted.request('session/start', {}).id, regular.id);
});
test('direct practice preserves learned dates and deduplicates words across tenses', () => {
  let now = new Date(2026, 9, 10, 10); const { studio } = setup(() => now);
  let q = studio.request('session/start', { count: 1 }); const verb = q.verbe;
  studio.request('session/answer', { id: q.id, choice: 1 });
  const original = studio.read().mastered.map(m => m.date_learned);
  now = new Date(2026, 9, 19, 10);
  for (const tense of ['现在时', '复合过去时', '现在时']) {
    q = studio.request('session/start', { verb, tense });
    while (!q.completed) q = solve(studio, q).next;
    assert.equal(studio.request('share').today_words, 1);
  }
  assert.deepEqual(studio.read().mastered.filter(m => m.temps === '现在时').map(m => m.date_learned), original);
  assert.ok(studio.request('state').mastered.filter(m => m.temps === '现在时').every(m => m.days === 10));
});
test('returned words remain priority through other wordlists and saved sessions', () => {
  const { studio } = setup();
  let q = studio.request('session/start', { verb: 'résoudre', tense: '未完成过去时' });
  while (!q.completed) q = solve(studio, q).next;
  const regular = studio.request('session/start', { level: '生僻', tense: '未完成过去时' });
  studio.request('mastered/relearn', { keys: ['résoudre|未完成过去时'] });
  assert.equal(studio.request('state').mastered.length, 0);
  studio.request('session/start', { tense: '现在时' });
  assert.ok(studio.read().settings.priority_learn.includes('résoudre|未完成过去时|je'));
  q = studio.request('session/start', { level: '生僻', tense: '未完成过去时', count: 1 });
  assert.equal(q.id, regular.id); assert.equal(q.round, 'judge');
  for (let i = 0; i < 3; i++) q = studio.request('session/answer', { id: q.id, choice: 1 }).next;
  assert.equal(q.verbe, 'résoudre'); assert.equal(q.round, 'judge');
});
test('returning a word preserves another current question, stages, retries and unrelated tense progress', () => {
  const { studio, storage } = setup();
  let q = studio.request('session/start', { count: 6 });
  const returned = q.verbe;
  q = studio.request('session/answer', { id: q.id, choice: 1 }).next;
  for (let i = 0; i < 2; i++) q = studio.request('session/answer', { id: q.id, choice: 3 }).next;
  for (let i = 0; i < 7; i++) q = solve(studio, q).next;
  q = studio.request('session/answer', { id: q.id, answer: '__wrong__' }).next;
  const before = studio.read(), originalQuestion = q;
  studio.request('session/start', { tense: '复合过去时', count: 3 });
  const other = structuredClone(studio.read().progress['必会|复合过去时']);
  studio.request('session/start', {});
  studio.request('mastered/relearn', { keys: [`${returned}|现在时`] });
  const after = studio.read();
  assert.deepEqual(after.progress['必会|复合过去时'], other);
  for (const field of ['plans', 'queue', 'judges']) assert.deepEqual(after.active.schedule[field], before.active.schedule[field]);
  assert.equal(after.active.done, before.active.done); assert.equal(after.active.question.id, originalQuestion.id);
  const restarted = new DeviceStudio(wordlists, storage);
  q = restarted.request('session/resume'); assert.equal(q.id, originalQuestion.id);
  for (let i = 0; i < 70 && q.round !== 'judge'; i++) q = solve(restarted, q).next;
  assert.equal(q.verbe, returned); assert.equal(q.round, 'judge');
  assert.ok(after.settings.priority_learn.includes(`${returned}|现在时|je`));
});
test('favorites survive reload, practice across levels and tenses, record completions once and retain regular progress', () => {
  const { studio, storage } = setup();
  assert.throws(() => studio.request('session/start', { favorites: true }));
  const regular = studio.request('session/start', { count: 3 });
  const saved = structuredClone(studio.read().progress);
  const selected = [{ verb: 'être', tense: '现在时' }, { verb: 'résoudre', tense: '复合过去时' }];
  for (const body of selected) studio.request('favorites/toggle', { ...body, saved: true });
  assert.equal(new DeviceStudio(wordlists, storage).request('state').favorites.length, 2);
  let q = studio.request('session/start', { favorites: true }), count = 0;
  while (!q.completed) {
    assert.notEqual(q.round, 'judge');
    if (count === 1) assert.deepEqual(new DeviceStudio(wordlists, storage).request('session/resume'), q);
    q = solve(studio, q).next; assert.ok(++count <= 36);
  }
  assert.equal(count, 36);
  let favorites = studio.request('state').favorites;
  assert.ok(favorites.every(f => f.practice_count === 1 && f.last_practiced));
  assert.deepEqual(studio.read().progress, saved);
  assert.notEqual(studio.request('session/start', {}).verbe, 'être');
  q = studio.request('session/start', { verb: 'être', tense: '现在时' });
  const stale = q;
  while (!q.completed) q = solve(studio, q).next;
  assert.throws(() => solve(studio, stale));
  favorites = studio.request('state').favorites;
  assert.equal(favorites.find(f => f.verbe === 'être').practice_count, 2);
  assert.equal(favorites.find(f => f.verbe === 'résoudre').practice_count, 1);
  studio.request('favorites/toggle', { ...selected[0], saved: false });
  assert.equal(studio.request('state').favorites.length, 1);
});
test('editable word goal validates input; every verb has Chinese and every quote is bilingual', () => {
  const { studio } = setup(); studio.request('settings', { daily_goal: 7 });
  assert.equal(studio.request('state').settings.daily_goal, 7);
  for (const value of [0, 101, 1.5, true, '3']) assert.throws(() => studio.request('settings', { daily_goal: value }));
  for (const verb of studio.request('state').verbs) assert.match(verbMeanings[verb], /[\u3400-\u9fff]/);
  assert.equal(shareQuotes.length, 15); assert.equal(new Set(shareQuotes.map(q => q.text)).size, 15);
  for (let i = 0; i < shareQuotes.length; i++) { assert.match(shareQuotes[i].translation, /[\u3400-\u9fff]/); assert.notEqual(nextQuote(i), i); }
});
test('all original CSV entries are packaged without a server', () => {
  const { studio } = setup(); const state = studio.request('state');
  assert.equal(state.wordlists.length, 9); assert.ok(state.verbs.includes('être'));
  assert.equal(studio.request('dictionary')['être']['必会']['现在时']['je'], 'suis');
});
test('three cards precede practice; every batch stays inside its three verbs', () => {
  const { studio } = setup(); let q = studio.request('session/start', { count: 7 });
  for (let batch = 1; batch <= 3; batch++) {
    const verbs = []; const size = batch === 3 ? 1 : 3;
    for (let i = 0; i < size; i++) {
      assert.equal(q.round, 'judge'); assert.equal(q.batch_index, batch); verbs.push(q.verbe);
      q = studio.request('session/answer', { id: q.id, choice: 3 }).next;
    }
    let steps = 0;
    while (!q.completed && q.batch_index === batch) { assert.notEqual(q.round, 'judge'); assert.ok(verbs.includes(q.verbe)); q = solve(studio, q).next; assert.ok(++steps < 100); }
  }
  assert.ok(q.completed); assert.equal(studio.request('state').mastered.length, 42);
});
test('device restart keeps current question and pending groups', () => {
  const { studio, storage } = setup(); let q = studio.request('session/start', { count: 6 });
  for (let i = 0; i < 3; i++) q = studio.request('session/answer', { id: q.id, choice: 3 }).next;
  const restarted = new DeviceStudio(wordlists, storage);
  assert.deepEqual(restarted.request('session/resume'), q);
  assert.equal(restarted.read().active.pending_groups.length, 1);
});
test('mistakes, mastery, priority relearning and settings persist', () => {
  const { studio, storage } = setup(); let q = studio.request('session/start', { count: 1 });
  q = studio.request('session/answer', { id: q.id, choice: 3 }).next;
  assert.equal(studio.request('session/answer', { id: q.id, answer: 'wrong' }).correct, false);
  assert.equal(studio.request('state').errors.length, 1);
  studio.request('errors/delete', { all: true }); assert.equal(studio.request('state').errors.length, 0);
  studio.request('settings', { fuzzy: false }); assert.equal(new DeviceStudio(wordlists, storage).request('state').settings.fuzzy, false);
  assert.ok(checkAnswer('etes', 'êtes', true)); assert.equal(checkAnswer('etes', 'êtes', false), false);
});
test('disabled rounds, all known verbs and stale answer protection', () => {
  const { studio } = setup(); studio.request('settings', { enable_reverse: false, enable_choice: false });
  let q = studio.request('session/start', { count: 1 }); q = studio.request('session/answer', { id: q.id, choice: 3 }).next;
  assert.equal(q.round, 'fill'); const old = q; q = solve(studio, q).next;
  assert.throws(() => solve(studio, old));
  while (!q.completed) q = solve(studio, q).next;
  assert.equal(studio.request('state').mastered.length, 6);
  const first = studio.request('state').mastered[0];
  studio.request('mastered/relearn', { keys: [`${first.verbe}|${first.temps}`] });
  assert.equal(studio.request('state').mastered.length, 0);
  assert.equal(studio.request('session/start', { count: 1 }).verbe, first.verbe);
});
test('scheduled reviews advance and return on subsequent intervals', () => {
  let now = new Date(2026, 9, 19, 10); const { studio } = setup(() => now);
  let q = studio.request('session/start', { verb: 'être', tense: '现在时' }); while (!q.completed) q = solve(studio, q).next;
  now = new Date(2026, 9, 20, 10); assert.equal(studio.request('state').review.length, 6);
  q = studio.request('session/start', { mode: 'review' });
  for (let i = 0; i < 6; i++) q = solve(studio, q).next;
  assert.ok(q.completed); assert.equal(studio.request('state').review.length, 0);
  now = new Date(2026, 9, 22, 10); assert.equal(studio.request('state').review.length, 6);
});

test('all judgments precede queue creation, including the partly familiar choice', () => {
  const { studio } = setup(); let q = studio.request('session/start', { count: 3 });
  for (const choice of [2, 3, 3]) {
    const s = studio.read().active.schedule;
    assert.deepEqual(s.queue, []); assert.deepEqual(s.plans, []); assert.equal(q.round, 'judge');
    q = studio.request('session/answer', { id: q.id, choice }).next;
  }
  assert.equal(q.round, 'choice');
});
test('every word follows choice then reverse then fill, including randomized retries', () => {
  const { studio } = setup(); let q = studio.request('session/start', { count: 3 });
  const verbs = q.batch_verbs;
  for (let i = 0; i < 3; i++) q = studio.request('session/answer', { id: q.id, choice: 3 }).next;
  const rounds = ['choice', 'reverse', 'fill'], successes = new Map(), failed = new Set(), waiting = new Map();
  for (const v of verbs) for (const r of rounds) successes.set(v + '|' + r, new Set());
  let steps = 0;
  while (!q.completed) {
    const v = q.verbe, r = q.round, p = q.personne, id = v + '|' + r;
    if (waiting.has(v)) { assert.equal(r, waiting.get(v)); waiting.delete(v); }
    for (const earlier of rounds.slice(0, rounds.indexOf(r))) assert.equal(successes.get(v + '|' + earlier).size, 6, `${v} skipped a pending ${earlier} task`);
    let result;
    if (!failed.has(id)) { failed.add(id); waiting.set(v, r); result = studio.request('session/answer', { id: q.id, answer: '__wrong__' }); assert.equal(result.correct, false); }
    else { result = solve(studio, q); assert.ok(result.correct); successes.get(id).add(p); }
    q = result.next; assert.ok(++steps < 150);
  }
  assert.ok([...successes.values()].every(s => s.size === 6));
  assert.deepEqual(studio.request('state').stats, { total: 63, correct: 54 });
});
test('failed choice stays choice after restarting the device app', () => {
  const { studio, storage } = setup(); let q = studio.request('session/start', { count: 3 });
  for (let i = 0; i < 3; i++) q = studio.request('session/answer', { id: q.id, choice: 3 }).next;
  const verb = q.verbe;
  q = studio.request('session/answer', { id: q.id, answer: '__wrong__' }).next;
  assert.notEqual(q.verbe, verb);
  const restarted = new DeviceStudio(wordlists, storage);
  assert.deepEqual(restarted.request('session/resume'), q);
  let steps = 0;
  while (q.verbe !== verb) { q = solve(restarted, q).next; assert.ok(++steps < 40); }
  assert.equal(q.round, 'choice');
});
test('upgrading an installed 3.0.1 snapshot fixes stage order and keeps statistics', () => {
  const { studio } = setup(), data = studio.read();
  const tasks = ['je', 'tu', 'il', 'nous', 'vous', 'ils'].flatMap(p => ['reverse', 'choice', 'fill'].map(round => ({ verbe: 'être', temps: '现在时', personnes: [p], personne_index: 0, round })));
  data.stats = { total: 7, correct: 4 };
  data.active = { mode: 'learn', level: '必会', temps: '现在时', count: 1, done: 1, settings: data.settings, queue: tasks.slice(0, 1), post_entries: tasks.slice(1), pending_groups: [], batch_index: 1, batch_count: 1, batch_verbs: ['être'], question: { id: 'old', round: 'reverse' } };
  studio.write(data);
  const q = studio.request('session/resume');
  assert.equal(q.round, 'choice'); assert.equal(q.done, 1);
  assert.deepEqual(studio.request('state').stats, { total: 7, correct: 4 });
});

test('share counts distinct completed verbs and retains cumulative learning after relearning', () => {
  const { studio } = setup(); const data = studio.read();
  const yesterday = new Date(); yesterday.setDate(yesterday.getDate() - 1);
  const day = `${yesterday.getFullYear()}-${String(yesterday.getMonth() + 1).padStart(2, '0')}-${String(yesterday.getDate()).padStart(2, '0')}`;
  for (const p of ['je', 'tu', 'il', 'nous', 'vous', 'ils']) data.mastered.push({ verbe: 'être', temps: '现在时', personne: p, date_learned: day });
  studio.write(data);
  assert.equal(studio.request('share').total_words, 1); assert.equal(studio.request('share').today_words, 0);
  const next = studio.read();
  for (const p of ['je', 'tu', 'il', 'nous', 'vous', 'ils']) studio.addMastery(next, { verbe: 'être', temps: '复合过去时' }, p);
  studio.addMastery(next, { verbe: 'avoir', temps: '现在时' }, 'je'); studio.write(next);
  assert.equal(studio.request('share').total_words, 1); assert.equal(studio.request('share').today_words, 1);
  studio.request('mastered/relearn', { keys: ['être|现在时', 'être|复合过去时'] });
  assert.equal(studio.request('share').total_words, 1);
});
test('today share count includes a completed review and never inflates for repeated practice', () => {
  let now = new Date(2026, 9, 19, 10); const { studio } = setup(() => now);
  let q = studio.request('session/start', { verb: 'être', tense: '现在时' }); while (!q.completed) q = solve(studio, q).next;
  assert.equal(studio.request('share').today_words, 1);
  now = new Date(2026, 9, 20, 10); assert.equal(studio.request('share').today_words, 0);
  q = studio.request('session/start', { mode: 'review' });
  for (let i = 0; i < 6; i++) { q = solve(studio, q).next; assert.equal(studio.request('share').today_words, Number(i === 5)); }
  assert.equal(studio.request('share').total_words, 1);
  assert.equal(studio.request('share').today_words, 1);
});
