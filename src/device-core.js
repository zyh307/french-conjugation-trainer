// Standalone learning controller for the Android build. No network or Python runtime.
import { GroupedPractice } from './learning-schedule.js';
const PERSONS = ['je', 'tu', 'il', 'nous', 'vous', 'ils'];
const LEVELS = ['必会', '常用', '生僻'];
const TENSES = ['现在时', '复合过去时', '未完成过去时'];
const STORE = 'conjugaison.device.v1';
const clone = value => JSON.parse(JSON.stringify(value));
const key = (v, t, p) => `${v}|${t}${p ? `|${p}` : ''}`;
const require = (condition, message) => { if (!condition) throw new Error(message); };
const uid = () => globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
const shuffle = array => { for (let i = array.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [array[i], array[j]] = [array[j], array[i]]; } return array; };
export const normalizeAnswer = value => String(value).normalize('NFKD').replace(/\p{M}/gu, '').replace(/[^\p{L}]/gu, '').toLowerCase();
export const checkAnswer = (answer, expected, fuzzy) => Boolean(answer) && (fuzzy ? normalizeAnswer(answer) === normalizeAnswer(expected) : answer === expected);
export function practiceHint(verb, expected) {
  const letters = text => [...text].filter(c => /\p{L}/u.test(c)).length;
  const length = letters(expected);
  if (!length) return '';
  const ending = ['er', 'ir', 're', 'oir'].find(s => verb.endsWith(s));
  const stem = ending ? verb.slice(0, -ending.length) : '';
  const suffix = stem && expected.startsWith(stem) ? expected.slice(stem.length) : '';
  if (length <= 4 || !suffix || letters(suffix) < 2) return `答案长度：${length} 个字母`;
  return `词干：${stem} + 后缀（${letters(suffix)} 个字母）`;
}
function localDay(date) { return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`; }
const initial = () => ({ schema: 1, stats: { total: 0, correct: 0 }, settings: { fuzzy: true, show_stem: true, enable_reverse: true, enable_choice: true, enable_fill: true, priority_learn: [] }, mastered: [], errors: [], review: [], progress: {}, history: {}, word_history: {}, active: null });

export class DeviceStudio {
  constructor(wordlists, storage, clock = () => new Date()) {
    this.wordlists = wordlists; this.storage = storage; this.clock = clock;
    this.dictionary = {};
    for (const level of LEVELS) for (const tense of TENSES) for (const [verb, forms] of Object.entries(wordlists[level][tense])) {
      this.dictionary[verb] ||= {}; this.dictionary[verb][level] ||= {}; this.dictionary[verb][level][tense] = forms;
    }
  }
  read() {
    const raw = this.storage.getItem(STORE);
    if (!raw) return initial();
    for (const value of [raw, this.storage.getItem(STORE + '.bak')]) {
      try { const data = JSON.parse(value); if (data?.schema === 1 && Array.isArray(data.mastered) && data.stats && data.settings && data.progress) return data; } catch { /* Try the previous committed snapshot. */ }
    }
    throw new Error('学习记录暂时无法读取，请保留应用数据并联系维护者。');
  }
  write(data) {
    try {
      const old = this.storage.getItem(STORE);
      if (old) this.storage.setItem(STORE + '.bak', old);
      this.storage.setItem(STORE, JSON.stringify(data));
    } catch { throw new Error('学习记录保存失败，请检查设备的可用存储空间。'); }
  }
  today() { return localDay(this.clock()); }
  completeDirectWord(data, session, entry) {
    const id = key(entry.verbe, entry.temps);
    session.completed_words ||= [];
    if (session.completed_words.includes(id)) return;
    for (const p of PERSONS.filter(p => this.forms(entry.verbe, entry.temps)[p])) this.addMastery(data, entry, p);
    const favorite = data.favorites?.[id];
    if (favorite) { favorite.practice_count = (favorite.practice_count || 0) + 1; favorite.last_practiced = this.clock().toISOString(); }
    session.completed_words.push(id);
  }
  forms(verb, tense, level) {
    if (level) return this.wordlists[level]?.[tense]?.[verb];
    for (const candidate of [...LEVELS].reverse()) if (this.wordlists[candidate][tense][verb]) return this.wordlists[candidate][tense][verb];
    return {};
  }
  addMastery(data, entry, person) {
    if (!data.mastered.some(m => key(m.verbe, m.temps, m.personne) === key(entry.verbe, entry.temps, person))) data.mastered.push({ verbe: entry.verbe, temps: entry.temps, personne: person, date_learned: this.today(), days: 1, needs_review: false, review_completed: false });
    this.recordCompletedWord(data, entry.verbe, entry.temps);
  }
  rememberWord(data, verb, day) {
    const journal = data.word_history ||= {};
    const item = journal[verb] ||= { first_learned: day, days: [] };
    if (day < item.first_learned) item.first_learned = day;
    if (!item.days.includes(day)) item.days.push(day);
  }
  recordCompletedWord(data, verb, tense) {
    const expected = PERSONS.filter(p => this.forms(verb, tense)[p]);
    const known = new Set(data.mastered.filter(m => m.verbe === verb && m.temps === tense).map(m => m.personne));
    if (expected.length && expected.every(p => known.has(p))) this.rememberWord(data, verb, this.today());
  }
  shareStats(data) {
    const groups = new Map();
    for (const item of data.mastered) { const id = key(item.verbe, item.temps); if (!groups.has(id)) groups.set(id, {}); groups.get(id)[item.personne] = item.date_learned; }
    for (const [id, people] of groups) {
      const [verb, tense] = id.split('|'), expected = PERSONS.filter(p => this.forms(verb, tense)[p]);
      if (expected.length && expected.every(p => people[p])) this.rememberWord(data, verb, expected.map(p => people[p]).sort()[expected.length - 1]);
    }
    const journal = data.word_history ||= {}, date = this.today();
    const verbs = Object.keys(journal).filter(v => journal[v].days.includes(date)).sort((a, b) => a.localeCompare(b, 'fr'));
    return { total_words: Object.keys(journal).length, today_words: verbs.length, today_verbs: verbs, date };
  }
  updateReview(data) {
    const today = this.today();
    const now = Date.parse(today + 'T00:00:00Z');
    data.review = [];
    const groups = new Map();
    for (const m of data.mastered) { const id = key(m.verbe, m.temps); if (!groups.has(id)) groups.set(id, []); groups.get(id).push(m); }
    for (const items of groups.values()) {
      const complete = PERSONS.filter(p => this.forms(items[0].verbe, items[0].temps)[p]).every(p => items.some(m => m.personne === p));
      if (complete && (items.some(m => m.known) || items.every(m => Math.floor((now - Date.parse(m.date_learned + 'T00:00:00Z')) / 86400000) + 1 >= 30))) for (const m of items) m.known = true;
    }
    for (const item of data.mastered) {
      item.days = Math.floor((now - Date.parse(item.date_learned + 'T00:00:00Z')) / 86400000) + 1;
      const complete = PERSONS.filter(p => this.forms(item.verbe, item.temps)[p]).every(p => groups.get(key(item.verbe, item.temps)).some(m => m.personne === p));
      item.needs_review = complete && !item.known && [2, 4, 7, 15].includes(item.days) && item.last_review_day !== today;
      if (item.needs_review) data.review.push({ verbe: item.verbe, temps: item.temps, personne: item.personne, due_date: today });
    }
  }
  record(data, correct, entry) {
    data.stats.total++; if (correct) data.stats.correct++;
    const day = data.history[this.today()] ||= { total: 0, correct: 0 };
    day.total++; if (correct) day.correct++;
    if (!correct) {
      const item = { verbe: entry.verbe, temps: entry.temps, personne: entry.personne, conjugaison: this.forms(entry.verbe, entry.temps)[entry.personne] };
      data.errors = data.errors.filter(e => key(e.verbe, e.temps, e.personne) !== key(item.verbe, item.temps, item.personne));
      data.errors.push(item);
    }
  }
  snapshot(data) {
    this.updateReview(data);
    const known = new Set(data.mastered.map(m => key(m.verbe, m.temps, m.personne)));
    const wordlists = LEVELS.flatMap(level => TENSES.map(tense => {
      const verbs = this.wordlists[level][tense];
      return { level, tense, total: Object.keys(verbs).length, mastered: Object.entries(verbs).filter(([v, forms]) => PERSONS.filter(p => forms[p]).every(p => known.has(key(v, tense, p)))).length, resume: Boolean(data.progress[key(level, tense)]) };
    }));
    return { stats: data.stats, settings: data.settings, mastered: data.mastered, review: data.review, errors: data.errors, history: data.history, verbs: Object.keys(this.dictionary).sort((a, b) => a.localeCompare(b, 'fr')), wordlists, favorites: Object.values(data.favorites || {}), active: Boolean(data.active), storage: 'device', share_stats: this.shareStats(data) };
  }
  buildBatch(data, session, verbs) {
    const known = new Set(data.mastered.map(m => key(m.verbe, m.temps, m.personne)));
    return verbs.map(verbe => {
      const personnes = PERSONS.filter(p => this.forms(verbe, session.temps, session.level)[p] && !known.has(key(verbe, session.temps, p)));
      return { verbe, temps: session.temps, personnes, personne_index: 0, round: 'judge' };
    }).filter(e => e.personnes.length);
  }
  ensureSchedule(session) {
    if (session.mode === 'learn' && session.schedule?.version !== 2) {
      session.schedule = GroupedPractice.fromProgress(session, session.settings).state;
      delete session.question;
    }
    if (session.mode === 'learn' && session.question) {
      session.question.done = session.done;
      session.question.total = session.done + new GroupedPractice([], session.settings, session.schedule).remaining();
    }
  }
  start(data, body) {
    const mode = body.mode || 'learn';
    require(['learn', 'review'].includes(mode), '未知的练习类型。');
    if (mode === 'review') {
      this.updateReview(data);
      data.active = { mode, items: clone(data.review).sort((a, b) => a.verbe.localeCompare(b.verbe, 'fr') || TENSES.indexOf(a.temps) - TENSES.indexOf(b.temps) || PERSONS.indexOf(a.personne) - PERSONS.indexOf(b.personne)), done: 0, total: data.review.length };
      return this.next(data);
    }
    const tense = body.tense || '现在时', level = body.level || (body.verb && LEVELS.find(l => this.wordlists[l][tense]?.[body.verb])) || '必会', count = body.count ?? 3;
    require(LEVELS.includes(level) && TENSES.includes(tense), '请选择有效的等级和时态。');
    if (body.verb || body.favorites) {
      const selected = body.favorites ? Object.values(data.favorites || {}) : [{ verbe: body.verb, temps: tense }];
      require(selected.length > 0, '先收藏一个动词，再开始练习。');
      const entries = selected.map(e => {
        const candidate = body.favorites ? LEVELS.find(l => this.wordlists[l][e.temps]?.[e.verbe]) : level;
        const forms = this.wordlists[candidate]?.[e.temps]?.[e.verbe];
        require(Boolean(forms), '此词不在所选时态和词表中。');
        return { verbe: e.verbe, temps: e.temps, personnes: PERSONS.filter(p => forms[p]), personne_index: 0, round: 'judge' };
      });
      const settings = { ...clone(data.settings), enable_choice: true, enable_reverse: true, enable_fill: true };
      const groups = TENSES.flatMap(t => { const words = entries.filter(e => e.temps === t), groups = []; for (let i = 0; i < words.length; i += 3) groups.push(words.slice(i, i + 3)); return groups; });
      const scheduler = new GroupedPractice(groups, settings);
      for (const group of scheduler.state.groups) group.judge_keys = [];
      data.active = { mode: 'learn', direct: true, favorites_mode: Boolean(body.favorites), direct_entries: entries, completed_words: [], verb: entries[0].verbe, level, temps: tense, settings, done: 0, schedule: scheduler.state };
      return this.next(data);
    }
    require(Number.isInteger(count) && count >= 1 && count <= 100, '动词数量需在 1–100 之间。');
    const saved = data.progress[key(level, tense)];
    if (saved && body.resume !== false) { data.active = clone(saved); this.ensureSchedule(data.active); return data.active.question || this.next(data); }
    const session = { mode, level, temps: tense, count, settings: clone(data.settings), done: 0, queue: [], post_entries: [], pending_groups: [], batch_index: 0, batch_count: 0, batch_verbs: [] };
    let verbs = Object.keys(this.wordlists[level][tense]).filter(v => PERSONS.some(p => this.forms(v, tense, level)[p] && !data.mastered.some(m => key(m.verbe, m.temps, m.personne) === key(v, tense, p))));
    const priorities = new Set(session.settings.priority_learn);
    verbs = [...verbs.filter(v => priorities.has(key(v, tense, 'je'))), ...verbs.filter(v => !priorities.has(key(v, tense, 'je')))].slice(0, count);
    data.settings.priority_learn = (data.settings.priority_learn || []).filter(id => !verbs.some(v => id === key(v, tense, 'je')));
    const groups = [];
    for (let i = 0; i < verbs.length; i += 3) groups.push(this.buildBatch(data, session, verbs.slice(i, i + 3)));
    session.schedule = new GroupedPractice(groups, session.settings).state;
    data.active = session;
    return this.next(data);
  }
  saveSession(data) {
    const s = data.active;
    if (s?.mode === 'learn' && !s.direct) data.progress[key(s.level, s.temps)] = clone(s);
  }
  pruneCompleted(data, session) {
    if (!session || session.direct) return;
    const selected = new Set();
    for (const m of data.mastered) {
      const items = data.mastered.filter(e => e.verbe === m.verbe && e.temps === m.temps);
      if (PERSONS.filter(p => this.forms(m.verbe, m.temps)[p]).every(p => items.some(e => e.personne === p)) && (session.mode !== 'review' || m.known)) selected.add(key(m.verbe, m.temps));
    }
    if (session.mode === 'review') session.items = session.items.filter(e => !selected.has(key(e.verbe, e.temps)));
    else new GroupedPractice([], session.settings, session.schedule).removeWords(selected);
    if (session.question && selected.has(key(session.question.verbe, session.question.temps))) delete session.question;
  }
  returnWords(data, selected, removeOnly = false) {
    function affected(e) { return selected.has(key(e.verbe, e.temps)); }
    const patch = session => {
      if (!session) return session;
      if (session.mode === 'review') {
        session.items = session.items.filter(e => !affected(e));
        session.total = session.done + session.items.length;
        if (session.question && affected(session.question)) delete session.question;
        return session;
      }
      if (session.direct) {
        const entries = session.direct_entries || [{ verbe: session.verb, temps: session.temps }];
        if (!entries.some(affected)) return session;
        session.direct_entries = entries.filter(e => !affected(e));
        if (!session.direct_entries.length) return null;
        const scheduler = new GroupedPractice([], session.settings, session.schedule);
        scheduler.removeWords(selected); const current = scheduler.current();
        session.queue = current ? [current] : [];
        Object.assign(session, scheduler.batchInfo());
        if (session.question && affected(session.question)) delete session.question;
        else if (session.question) Object.assign(session.question, scheduler.batchInfo(), { total: session.done + scheduler.remaining() });
        return session;
      }
      const entries = [...selected].map(id => { const [verbe, temps] = id.split('|'); return { verbe, temps, personnes: PERSONS.filter(p => this.wordlists[session.level]?.[temps]?.[verbe]?.[p]), personne_index: 0, round: 'judge' }; }).filter(e => e.temps === session.temps && e.personnes.length);
      if (!entries.length) return session;
      this.ensureSchedule(session);
      const scheduler = new GroupedPractice([], session.settings, session.schedule);
      if (removeOnly) scheduler.removeWords(selected); else scheduler.returnWords(entries);
      const current = scheduler.current();
      session.queue = current ? [current] : []; session.post_entries = [];
      session.pending_groups = session.schedule.groups.slice(session.schedule.cursor + 1);
      Object.assign(session, scheduler.batchInfo());
      if (session.question && affected(session.question)) delete session.question;
      else if (session.question) Object.assign(session.question, scheduler.batchInfo(), { total: session.done + scheduler.remaining() });
      return session;
    };
    for (const id of Object.keys(data.progress)) data.progress[id] = patch(data.progress[id]);
    if (data.active?.mode === 'learn' && !data.active.direct) data.active = clone(data.progress[key(data.active.level, data.active.temps)] || patch(data.active));
    else data.active = patch(data.active);
  }
  finish(data) {
    const mode = data.active?.mode;
    if (mode === 'learn' && data.active.direct) {
      for (const entry of data.active.direct_entries || [{ verbe: data.active.verb, temps: data.active.temps }]) this.completeDirectWord(data, data.active, entry);
    } else if (mode === 'learn') delete data.progress[key(data.active.level, data.active.temps)];
    data.active = null;
    return { completed: true, mode };
  }
  options(session, entry, expected) {
    const forms = this.forms(entry.verbe, entry.temps, session.direct ? undefined : session.level);
    let pool = PERSONS.filter(p => p !== entry.personne).map(p => forms[p]).filter(Boolean);
    if (pool.length < 3) for (const tense of TENSES.filter(t => t !== entry.temps)) for (const p of PERSONS.filter(p => p !== entry.personne)) pool.push(this.forms(entry.verbe, tense, session.level)?.[p]);
    if (pool.length < 3) for (const [verb, forms] of Object.entries(this.wordlists[session.level][entry.temps])) if (verb !== entry.verbe) pool.push(forms[entry.personne]);
    const options = [expected, ...shuffle([...new Set(pool.filter(c => c && c !== expected))]).slice(0, 3)];
    while (options.length < 4) options.push('???');
    return shuffle(options);
  }
  next(data) {
    const s = data.active;
    if (!s) return { completed: true };
    let q;
    if (s.mode === 'review') {
      this.updateReview(data);
      s.items = s.items.filter(e => !data.mastered.some(m => m.verbe === e.verbe && m.temps === e.temps && m.known));
      if (!s.items.length) return this.finish(data);
      q = { ...s.items[0], round: 'fill', mode: 'review', done: s.done, total: s.total };
    } else {
      this.ensureSchedule(s);
      const scheduler = new GroupedPractice([], s.settings, s.schedule), e = scheduler.current();
      if (!e) return this.finish(data);
      s.queue = [e]; s.post_entries = []; Object.assign(s, scheduler.batchInfo());
      s.pending_groups = s.schedule.groups.slice(s.schedule.cursor + 1);
      const questionLevel = s.direct ? LEVELS.find(l => this.wordlists[l][e.temps]?.[e.verbe]) : s.level;
      q = { verbe: e.verbe, temps: e.temps, personne: e.personnes[e.personne_index || 0], round: e.round, level: questionLevel, mode: 'learn', direct: Boolean(s.direct), done: s.done, total: s.done + scheduler.remaining(), ...scheduler.batchInfo() };
      const forms = this.forms(q.verbe, q.temps, questionLevel);
      if (q.round === 'judge') q.conjugations = forms;
      else if (q.round === 'reverse') { q.display = forms[q.personne]; q.options = PERSONS; }
      else if (q.round === 'choice') q.options = this.options(s, q, forms[q.personne]);
      else if (s.settings.show_stem) {
        q.hint = practiceHint(q.verbe, forms[q.personne]);
      }
    }
    q.id = uid(); s.question = q; this.saveSession(data); return q;
  }
  answer(data, body) {
    const s = data.active, q = s?.question;
    require(q && body.id === q.id, '题目已更新，请重新打开练习继续。');
    if (s.mode === 'review') {
      const answer = String(body.answer || '').trim(); require(answer, '请先输入答案。');
      const expected = this.forms(q.verbe, q.temps)[q.personne];
      const correct = checkAnswer(answer, expected, data.settings.fuzzy); this.record(data, correct, q);
      if (correct) {
        const item = data.mastered.find(m => key(m.verbe, m.temps, m.personne) === key(q.verbe, q.temps, q.personne));
        if (item) { item.last_review_day = this.today(); item.review_completed = true; item.needs_review = false; }
        s.items.shift(); s.done++;
        if (!s.items.some(e => e.verbe === q.verbe && e.temps === q.temps)) this.recordCompletedWord(data, q.verbe, q.temps);
      }
      return { correct, expected, next: this.next(data) };
    }
    const entry = s.queue[0];
    const scheduler = new GroupedPractice([], s.settings, s.schedule);
    if (q.round === 'judge') {
      require([1, 2, 3].includes(body.choice), '请选择掌握程度。');
      if (body.choice === 1) {
        for (const p of entry.personnes) this.addMastery(data, entry, p);
        for (const m of data.mastered.filter(m => m.verbe === q.verbe && m.temps === q.temps)) m.known = true;
      }
      if (body.choice !== 1 && !['reverse', 'choice', 'fill'].some(r => s.settings['enable_' + r])) for (const p of entry.personnes) this.addMastery(data, entry, p);
      scheduler.judge(body.choice); s.done++;
      return { correct: true, judged: true, next: this.next(data) };
    }
    const answer = String(body.answer || '').trim(); require(answer, '请先选择或输入答案。');
    const forms = this.forms(q.verbe, q.temps, q.level), expected = q.round === 'reverse' ? q.personne : forms[q.personne];
    const correct = q.round === 'reverse' ? PERSONS.includes(answer) && forms[answer] === forms[q.personne] : checkAnswer(answer, expected, s.settings.fuzzy);
    this.record(data, correct, q);
    const { final } = scheduler.answer(correct);
    if (correct) { s.done++; if (final && !s.direct) this.addMastery(data, entry, q.personne); }
    if (correct && final && s.direct && s.schedule.plans.some(p => key(p.verbe, p.temps) === key(q.verbe, q.temps) && p.stage === p.rounds.length)) this.completeDirectWord(data, s, entry);
    return { correct, expected, next: this.next(data) };
  }
  request(path, body = {}) {
    const data = this.read(); let result;
    this.updateReview(data);
    if (data.active?.mode === 'learn') this.ensureSchedule(data.active);
    if (path === 'state') result = this.snapshot(data);
    else if (path === 'share') result = this.shareStats(data);
    else if (path === 'dictionary') return clone(this.dictionary);
    else if (path === 'favorites/toggle') {
      require(TENSES.includes(body.tense) && Boolean(this.dictionary[body.verb]), '请选择有效的动词和时态。');
      const favorites = data.favorites ||= {}, id = key(body.verb, body.tense);
      require(typeof body.saved === 'boolean', '收藏状态无效。');
      if (body.saved) favorites[id] ||= { verbe: body.verb, temps: body.tense, added: this.today(), practice_count: 0, last_practiced: null };
      else delete favorites[id];
      result = { ok: true };
    }
    else if (path === 'notebooks/move') {
      let selected = new Set(body.keys || []);
      require(selected.size > 0 && ['practice', 'review', 'known'].includes(body.target), '请选择有效的词条和目标本。');
      for (const id of selected) { const [v, t, extra] = id.split('|'); require(!extra && TENSES.includes(t) && Boolean(this.forms(v, t).je), '请选择有效的动词和时态。'); }
      selected = new Set([...selected].filter(id => {
        const [v, t] = id.split('|'), items = data.mastered.filter(m => key(m.verbe, m.temps) === id);
        const complete = PERSONS.filter(p => this.forms(v, t)[p]).every(p => items.some(m => m.personne === p));
        return (complete ? (items.some(m => m.known) ? 'known' : 'review') : 'practice') !== body.target;
      }));
      if (body.target === 'practice') {
        data.mastered = data.mastered.filter(m => !selected.has(key(m.verbe, m.temps)));
        for (const id of selected) { const priority = id + '|je'; if (!data.settings.priority_learn.includes(priority)) data.settings.priority_learn.push(priority); }
        this.returnWords(data, selected);
      } else {
        for (const id of selected) {
          const [verbe, temps] = id.split('|'), items = data.mastered.filter(m => key(m.verbe, m.temps) === id);
          const complete = PERSONS.filter(p => this.forms(verbe, temps)[p]).every(p => items.some(m => m.personne === p));
          const current = complete ? (items.some(m => m.known) ? 'known' : 'review') : 'practice';
          if (current === body.target) continue;
          if (complete && body.target === 'known') { for (const m of items) m.known = true; continue; }
          data.mastered = data.mastered.filter(m => key(m.verbe, m.temps) !== id);
          for (const p of PERSONS.filter(p => this.forms(verbe, temps)[p])) this.addMastery(data, { verbe, temps }, p);
          for (const m of data.mastered.filter(m => key(m.verbe, m.temps) === id)) m.known = body.target === 'known';
        }
        this.returnWords(data, selected, true);
      }
      this.updateReview(data);
      result = { ok: true, next: data.active?.question || this.next(data) };
    }
    else if (path === 'session/start') {
      for (const saved of Object.values(data.progress)) this.pruneCompleted(data, saved);
      result = this.start(data, body);
    }
    else if (path === 'session/resume') { this.pruneCompleted(data, data.active); result = data.active?.question || this.next(data); }
    else if (path === 'session/answer') result = this.answer(data, body);
    else if (path === 'settings') {
      if ('daily_goal' in body) { require(Number.isInteger(body.daily_goal) && body.daily_goal >= 1 && body.daily_goal <= 100, '每日目标需为 1–100 个动词。'); data.settings.daily_goal = body.daily_goal; }
      for (const option of ['fuzzy', 'show_stem', 'enable_reverse', 'enable_choice', 'enable_fill']) if (option in body) { require(typeof body[option] === 'boolean', '设置值必须是开关状态。'); data.settings[option] = body[option]; }
      result = data.settings;
    } else if (path === 'errors/delete') { data.errors = body.all ? [] : data.errors.filter(e => !(body.keys || []).includes(key(e.verbe, e.temps, e.personne))); result = { ok: true }; }
    else if (path === 'mastered/relearn') {
      const requested = new Set(body.keys || []);
      const selected = new Set(data.mastered.filter(e => requested.has(key(e.verbe, e.temps))).map(e => key(e.verbe, e.temps)));
      for (const item of data.mastered.filter(e => selected.has(key(e.verbe, e.temps)))) { const priority = key(item.verbe, item.temps, 'je'); if (!data.settings.priority_learn.includes(priority)) data.settings.priority_learn.push(priority); }
      data.mastered = data.mastered.filter(e => !selected.has(key(e.verbe, e.temps)));
      this.returnWords(data, selected);
      this.updateReview(data); result = { ok: true };
    } else if (path === 'progress/reset') {
      require(LEVELS.includes(body.level) && TENSES.includes(body.tense), '等级或时态无效。');
      delete data.progress[key(body.level, body.tense)];
      if (data.active?.level === body.level && data.active?.temps === body.tense) data.active = null;
      result = { ok: true };
    } else throw new Error('不存在的操作。');
    this.write(data); return clone(result);
  }
}
