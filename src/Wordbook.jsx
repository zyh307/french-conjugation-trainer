import { useMemo, useState } from 'react';
import { ArrowRight, Bookmark, CheckCheck, ChevronRight, RotateCcw, Search } from 'lucide-react';
import { Button, Empty, SearchBox, Segments } from './components.jsx';
import { groupedMastered, levels, normalize, persons, personLabel, tenseFrench, tenses } from './api.js';
import { verbMeanings } from './verb-meanings.js';

export default function Wordbook({ state, dictionary, selectedVerb, setSelectedVerb, start, mutate, busy }) {
  const [query, setQuery] = useState('');
  const [selectedLevel, setSelectedLevel] = useState('必会');
  const [view, setView] = useState('全部');
  const [limit, setLimit] = useState(100);
  const learned = useMemo(() => groupedMastered(state.mastered).filter(item => {
    const forms = levels.map(level => dictionary?.[item.verbe]?.[level]?.[item.temps]).find(Boolean);
    return forms && persons.filter(p => forms[p]).every(p => item.persons.includes(p));
  }), [state.mastered, dictionary]);
  const known = new Set(learned.map(item => item.verbe));
  const favorites = state.favorites || [];
  const favoriteVerbs = new Set(favorites.map(item => item.verbe));
  const matches = state.verbs.filter(v => normalize(v).includes(normalize(query.trim())) && (view !== '已背' || known.has(v)) && (view !== '收藏' || favoriteVerbs.has(v)));
  const data = dictionary?.[selectedVerb];
  const availableLevels = levels.filter(l => data?.[l]);
  const level = availableLevels.includes(selectedLevel) ? selectedLevel : availableLevels[0];
  const returnWord = async tense => {
    await mutate('mastered/relearn', { keys: [`${selectedVerb}|${tense}`] }, '已放回单词本，将在相应词表优先出现。');
  };
  const changeView = value => {
    setView(value); setLimit(100);
    if (value === '已背' && !known.has(selectedVerb)) setSelectedVerb(state.verbs.find(v => known.has(v) && normalize(v).includes(normalize(query.trim()))) || '');
    if (value === '收藏' && !favoriteVerbs.has(selectedVerb)) setSelectedVerb(favorites[0]?.verbe || '');
  };
  return <div className="page-enter"><div className="page-heading"><div><div className="eyebrow">LES MOTS, À PORTÉE DE MAIN</div><h1>每一个动词，都有迹可查。</h1><p>查变位、直接练习，也在这里回顾已经背过的词。</p></div><span className="soft-badge"><Search size={14} /> {state.verbs.length} 个动词</span></div>
    <div className="dictionary-layout"><section className="glass-card verb-list-panel">
      <Segments options={['全部', '已背', '收藏']} value={view} onChange={changeView} label="单词本分类" />
      <SearchBox value={query} onChange={v => { setQuery(v); setLimit(100); }} placeholder="搜索动词，如 être…" label="搜索法语动词" onKeyDown={e => { if (e.key === 'Enter' && matches[0]) setSelectedVerb(matches[0]); }} />
      <div className="verb-list-heading"><span>{view === '已背' ? `已背 ${matches.length} 个动词` : query ? `${matches.length} 个结果` : '全部动词'}</span><span>A—Z</span></div>
      <div className="verb-list">{matches.slice(0, limit).map(v => <button className={selectedVerb === v ? 'selected' : ''} key={v} onClick={() => setSelectedVerb(v)}><span><span lang="fr">{v}</span>{view === '已背' && <small className="word-days">已背 {Math.max(...learned.filter(i => i.verbe === v).map(i => i.days))} 天</small>}</span>{known.has(v) ? <CheckCheck size={14} aria-label="已背" /> : <ChevronRight size={14} />}</button>)}{!matches.length && <p className="muted no-results">{view === '已背' ? '还没有符合条件的已背动词。' : '没有找到对应动词。'}</p>}{matches.length > limit && <button onClick={() => setLimit(n => n + 100)}>显示更多</button>}</div>
      <div className="verb-list-foot">每个时态单独记录掌握进度</div></section>
      <div className="verb-detail">{view === '收藏' && <section className="glass-card favorite-panel"><div className="section-heading"><div><span className="section-label">MES FAVORIS</span><h2>我的收藏 <small>{favorites.length} 组</small></h2></div><Button variant="primary" disabled={busy || !favorites.length} onClick={() => start({ favorites: true })}>一键练习全部收藏 <ArrowRight size={14} /></Button></div><p className="word-practice-note">按时态分别收藏；完整练完一组变位后记录时间与次数。</p><div className="favorite-list">{favorites.filter(f => normalize(f.verbe).includes(normalize(query.trim()))).map(f => <div className="favorite-row" key={`${f.verbe}|${f.temps}`}><div><button className="text-link" onClick={() => setSelectedVerb(f.verbe)} lang="fr">{f.verbe}</button><span>{f.temps} · {verbMeanings[f.verbe]}</span><small data-testid={`favorite-history-${f.verbe}-${f.temps}`}>{f.last_practiced ? `最近练习 ${new Date(f.last_practiced).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })} · 已完成 ${f.practice_count} 次` : '尚未完成练习'}</small></div><div className="favorite-row-actions"><Button disabled={busy} aria-label={`练习收藏 ${f.verbe} ${f.temps}`} onClick={() => start({ verb: f.verbe, tense: f.temps })}>单个练习</Button><button className="text-link" disabled={busy} aria-label={`移除收藏 ${f.verbe} ${f.temps}`} onClick={() => mutate('favorites/toggle', { verb: f.verbe, tense: f.temps, saved: false })}>移除</button></div></div>)}</div>{!favorites.length && <Empty icon={Bookmark} title="把想多练的词，留在这里。">在任意时态卡片点击“收藏”，就能随时回来练习。</Empty>}</section>}{!dictionary ? <section className="glass-card dictionary-loading"><span className="loading-indicator" /><p>正在整理词典…</p></section> : data ? <>
        <div className="glass-card verb-detail-header"><div><span className="section-label">INFINITIF · 动词原形</span><h2 lang="fr">{selectedVerb}</h2><p className="verb-meaning">{verbMeanings[selectedVerb]}</p><div className="verb-meta"><span className="status-dot" />{availableLevels.join(' / ')}词表已收录</div></div><Segments options={availableLevels} value={level} onChange={setSelectedLevel} label="选择词典等级" /></div>
        {tenses.filter(t => data[level]?.[t]).map((tense, i) => {
          const item = learned.find(item => item.verbe === selectedVerb && item.temps === tense);
          const favorite = favorites.some(f => f.verbe === selectedVerb && f.temps === tense);
          return <section className="glass-card tense-table-card" key={tense}><div className="section-heading"><div><span className="section-label">0{i + 1}</span><h3>{tense}<span lang="fr">{tenseFrench[tense]}</span></h3></div><span className="tiny-badge">{item ? `已背 ${item.days} 天` : '待学习'}</span></div>
            <div className="conjugation-grid">{persons.map(p => <div key={p}><span lang="fr">{personLabel(p)}</span><strong lang="fr">{data[level][tense][p] || '—'}</strong></div>)}</div>
            <div className="favorite-toggle"><Button variant="ghost" icon={Bookmark} aria-label={`收藏 ${selectedVerb} ${tense}`} aria-pressed={favorite} disabled={busy} onClick={() => mutate('favorites/toggle', { verb: selectedVerb, tense, saved: !favorite })}>{favorite ? '已收藏' : '收藏'}</Button></div>
            <div className="word-practice-actions"><Button variant="primary" disabled={busy} aria-label={`立即练习 ${selectedVerb} ${tense}`} onClick={() => start({ verb: selectedVerb, level, tense })}>立即练习 <ArrowRight size={14} /></Button>{item && <Button variant="ghost" disabled={busy} icon={RotateCcw} aria-label={`返回单词本 ${selectedVerb} ${tense}`} onClick={() => returnWord(tense)}>返回单词本</Button>}</div>
            <p className="word-practice-note">{item ? '重新练习保留已背天数与复习日期。' : '只练这个词、这个时态；完成后计入已背。'}</p>
          </section>;
        })}</> : <section className="glass-card"><Empty title="选一个动词，展开看看。">左侧的每个动词，都有属于它的变位方式。</Empty></section>}</div>
    </div></div>;
}
