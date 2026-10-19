// Each verb completes an entire stage before the next one becomes eligible.
const ORDER = ['choice', 'reverse', 'fill'];
const copy = value => JSON.parse(JSON.stringify(value));
const key = e => `${e.verbe}|${e.temps}`;
const shuffle = array => { for (let i = array.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [array[i], array[j]] = [array[j], array[i]]; } };

export class GroupedPractice {
  constructor(groups = [], settings = {}, state = null) {
    this.state = state || { version: 2, rounds: ORDER.filter(r => settings['enable_' + r] !== false), groups: groups.map(entries => ({ entries: copy(entries) })), cursor: -1, offset: 0, judges: [], plans: [], queue: [], entries: [], decisions: {}, last_verb: null };
  }
  static fromProgress(saved, settings) {
    if (saved.schedule?.version === 2) return new GroupedPractice([], settings, copy(saved.schedule));
    function convert(queue, pool) {
      const entries = new Map(), judges = new Set(), starts = {};
      for (const item of [...queue, ...pool]) {
        const id = key(item);
        if (!entries.has(id)) entries.set(id, { verbe: item.verbe, temps: item.temps, personnes: [], personne_index: 0, round: 'judge' });
        const entry = entries.get(id);
        for (const p of item.personnes || []) if (!entry.personnes.includes(p)) entry.personnes.push(p);
        if (item.round === 'judge') judges.add(id);
        else if (ORDER.includes(item.round)) starts[id] = Math.min(starts[id] ?? 99, ORDER.indexOf(item.round));
      }
      return { entries: [...entries.values()], judge_keys: [...judges], starts };
    }
    const scheduler = new GroupedPractice([], settings);
    scheduler.state.groups = [convert(saved.queue || [], saved.post_entries || []), ...(saved.pending_groups || []).map(g => convert(g.queue, g.post_entries || []))].filter(g => g.entries.length);
    scheduler.state.offset = Math.max((saved.batch_index || 1) - 1, 0);
    return scheduler;
  }
  removeWords(selected) {
    const s = this.state;
    // Keep every other verb's stage, remaining persons and queue order intact.
    for (const group of s.groups) {
      group.entries = group.entries.filter(e => !selected.has(key(e)));
      if (group.judge_keys) group.judge_keys = group.judge_keys.filter(id => !selected.has(id));
      for (const id of selected) if (group.starts) delete group.starts[id];
    }
    for (const field of ['entries', 'judges', 'plans', 'queue']) s[field] = s[field].filter(e => !selected.has(key(e)));
    for (const id of selected) delete s.decisions[id];
    if (selected.has(s.last_verb)) s.last_verb = null;
  }
  returnWords(entries) {
    const s = this.state;
    this.removeWords(new Set(entries.map(key)));
    const groups = [];
    for (let i = 0; i < entries.length; i += 3) groups.push({ entries: copy(entries.slice(i, i + 3)) });
    s.groups.splice(Math.max(s.cursor + 1, 0), 0, ...groups);
  }
  activate() {
    const s = this.state;
    if (++s.cursor >= s.groups.length) return false;
    const group = s.groups[s.cursor];
    s.entries = copy(group.entries);
    const judges = new Set(group.judge_keys || s.entries.map(key));
    s.judges = s.entries.filter(e => judges.has(key(e))).map(copy);
    s.decisions = Object.fromEntries(s.entries.filter(e => !judges.has(key(e))).map(e => [key(e), 3]));
    s.plans = []; s.queue = []; s.prepared = false;
    return true;
  }
  tasks(plan) { return plan.remaining.map(p => ({ verbe: plan.verbe, temps: plan.temps, personnes: [p], personne_index: 0, round: plan.rounds[plan.stage] })); }
  mix() {
    const s = this.state; shuffle(s.queue);
    const alternatives = s.queue.map((e, i) => key(e) !== s.last_verb ? i : -1).filter(i => i >= 0);
    if (alternatives.length) { const i = alternatives[Math.floor(Math.random() * alternatives.length)]; [s.queue[0], s.queue[i]] = [s.queue[i], s.queue[0]]; }
  }
  prepare() {
    const s = this.state, group = s.groups[s.cursor];
    for (const entry of s.entries) {
      if (s.decisions[key(entry)] === 1 || !s.rounds.length) continue;
      const start = group.starts?.[key(entry)] ?? 0;
      const rounds = s.rounds.filter(r => ORDER.indexOf(r) >= start);
      if (!rounds.length) continue;
      const plan = { ...copy(entry), rounds, stage: 0, remaining: [...entry.personnes] };
      s.plans.push(plan); s.queue.push(...this.tasks(plan));
    }
    s.prepared = true; this.mix();
  }
  current() {
    const s = this.state;
    while (true) {
      if (s.cursor < 0 && !this.activate()) return null;
      if (s.cursor >= s.groups.length) return null;
      if (s.judges.length) return s.judges[0];
      if (!s.prepared) this.prepare();
      if (s.queue.length) return s.queue[0];
      if (!this.activate()) return null;
    }
  }
  judge(choice) {
    const s = this.state, entry = s.judges.shift(); s.decisions[key(entry)] = choice;
    return entry;
  }
  answer(correct) {
    const s = this.state, entry = s.queue.shift(), plan = s.plans.find(p => key(p) === key(entry));
    const person = entry.personnes[0], final = correct && plan.stage === plan.rounds.length - 1;
    if (correct) {
      plan.remaining.splice(plan.remaining.indexOf(person), 1);
      if (!plan.remaining.length && ++plan.stage < plan.rounds.length) { plan.remaining = [...plan.personnes]; s.queue.push(...this.tasks(plan)); }
    } else s.queue.push(entry);
    s.last_verb = key(entry); this.mix();
    return { entry, final };
  }
  remaining() {
    const s = this.state;
    const future = s.groups.slice(s.cursor + 1).reduce((n, g) => n + (g.judge_keys || g.entries).length + g.entries.reduce((total, e) => total + e.personnes.length * s.rounds.length, 0), 0);
    if (s.judges.length) return future + s.judges.length + s.entries.filter(e => s.decisions[key(e)] !== 1).reduce((n, e) => n + e.personnes.length * s.rounds.length, 0);
    return future + s.plans.reduce((n, p) => n + p.remaining.length + Math.max(0, p.rounds.length - p.stage - 1) * p.personnes.length, 0);
  }
  batchInfo() { const s = this.state; return { batch_index: s.offset + s.cursor + 1, batch_count: s.offset + s.groups.length, batch_verbs: s.entries.map(e => e.verbe) }; }
}
