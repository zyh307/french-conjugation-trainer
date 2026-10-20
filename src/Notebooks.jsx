import { useState } from 'react';
import { ArrowRight, CheckCheck, Repeat2 } from 'lucide-react';
import { Button, Empty, SearchBox } from './components.jsx';
import { groupedMastered, notebookFor, notebookNames, normalize, tenses } from './api.js';
import { verbMeanings } from './verb-meanings.js';

export default function Notebooks({ kind, state, start, moveWord, busy }) {
  const [query, setQuery] = useState('');
  const [tense, setTense] = useState('全部时态');
  const [limit, setLimit] = useState(30);
  const items = groupedMastered(state.mastered).filter(m => notebookFor(state, m.verbe, m.temps) === kind);
  const filtered = items.filter(m => normalize(m.verbe).includes(normalize(query)) && (tense === '全部时态' || tense === m.temps));
  const due = new Set(state.review.map(m => `${m.verbe}|${m.temps}`));
  return <div className="page-enter"><div className="page-heading"><div><div className="eyebrow">{kind === 'known' ? 'MES ACQUIS' : 'RÉVISER POUR RETENIR'}</div><h1>{notebookNames[kind]}</h1><p>{kind === 'known' ? '已熟悉的动词与时态，不再安排复习。' : '完整练完的词条在这里巩固，已背满 30 天自动转入已会本。'}</p></div><span className="soft-badge">{kind === 'known' ? <CheckCheck size={14} /> : <Repeat2 size={14} />}{items.length} 组词条</span></div>
    {kind === 'review' && <section className="glass-card notebook-summary"><div><h2>今日复习</h2><p>第 2、4、7、15 天安排温习 · 今日到期 {due.size} 组</p></div><Button variant="primary" disabled={busy || !due.size} onClick={() => start({ mode: 'review' })}>开始今日复习 <ArrowRight size={14} /></Button></section>}
    <section className="glass-card collection-card"><div className="collection-tools"><SearchBox value={query} onChange={v => { setQuery(v); setLimit(30); }} placeholder="搜索动词…" label={`搜索${notebookNames[kind]}`} /><label className="filter-select"><span className="sr-only">按时态筛选</span><select value={tense} onChange={e => { setTense(e.target.value); setLimit(30); }}>{['全部时态', ...tenses].map(t => <option key={t}>{t}</option>)}</select></label></div>
      <div className="notebook-list">{filtered.slice(0, limit).map(m => <article className="notebook-row" key={m.key}><div><strong lang="fr">{m.verbe}</strong><span>{m.temps} · {verbMeanings[m.verbe]}</span><small>已背 {m.days} 天{kind === 'review' && due.has(m.key) ? ' · 今日待复习' : ''}</small></div><div className="notebook-actions"><Button disabled={busy} onClick={() => start({ verb: m.verbe, tense: m.temps })}>立即练习</Button><Button variant="ghost" disabled={busy} onClick={() => moveWord(m.verbe, m.temps, 'practice')}>放回练习本</Button>{kind === 'review' && <Button variant="ghost" disabled={busy} onClick={() => moveWord(m.verbe, m.temps, 'known')}>加入已会本</Button>}</div></article>)}</div>
      {!filtered.length && <Empty title="暂无词条">每个动词的每个时态单独记录，练习中也可以调整归属。</Empty>}{filtered.length > limit && <Button onClick={() => setLimit(n => n + 30)}>显示更多</Button>}
    </section></div>;
}
