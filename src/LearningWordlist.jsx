import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ChevronRight } from 'lucide-react';
import { Button, Empty, SearchBox } from './components.jsx';
import { normalize } from './api.js';
import Wordbook from './Wordbook.jsx';

export default function LearningWordlist({ state, dictionary, error, retry, scope, selectedVerb, setSelectedVerb, back, ...actions }) {
  const [query, setQuery] = useState('');
  const scroll = useRef(0);
  const root = useRef(null);
  const verbs = state.verbs.filter(v => dictionary?.[v]?.[scope.level]?.[scope.tense]);
  const matches = verbs.filter(v => normalize(v).includes(normalize(query.trim())));
  useEffect(() => {
    root.current?.closest('main')?.scrollTo({ top: selectedVerb ? 0 : scroll.current, behavior: 'instant' });
  }, [selectedVerb]);
  const open = verb => { scroll.current = root.current?.closest('main')?.scrollTop || 0; setSelectedVerb(verb); };
  return <div ref={root} className="page-enter learning-wordlist-page"><button className="text-link wordlist-back" onClick={() => selectedVerb ? setSelectedVerb(null) : back()}><ArrowLeft size={16} />{selectedVerb ? '返回词表' : '返回学习设置'}</button>
    {selectedVerb ? <Wordbook {...actions} state={state} dictionary={dictionary} scope={scope} selectedVerb={selectedVerb} setSelectedVerb={setSelectedVerb} /> : <><div className="page-heading"><div><div className="eyebrow">LES VERBES À APPRENDRE</div><h1>{scope.level} · {scope.tense}</h1><p>点击动词原形，查看变位或立即练习。</p></div><span className="soft-badge">{verbs.length} 个动词</span></div>
      {error ? <section className="glass-card"><Empty title="词表暂时无法打开" action={<Button onClick={retry}>重新加载</Button>}>{error}</Empty></section> : !dictionary ? <section className="glass-card dictionary-loading"><span className="loading-indicator" /><p>正在整理词表…</p></section> : <section className="glass-card learning-wordlist"><SearchBox value={query} onChange={setQuery} placeholder="搜索动词原形…" label="搜索当前词表" onKeyDown={e => { if (e.key === 'Enter' && matches[0]) open(matches[0]); }} /><div className="learning-wordlist-rows">{matches.map(v => <button key={v} onClick={() => open(v)} aria-label={`查看 ${v}`}><span lang="fr">{v}</span><ChevronRight size={16} /></button>)}</div>{!matches.length && <Empty title="没有匹配的动词">试试其他拼写，或清空搜索词。</Empty>}</section>}</>}
  </div>;
}
