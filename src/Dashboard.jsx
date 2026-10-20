import { ArrowUpRight, ArrowRight, BookOpen, Check, CheckCheck, Clock3, Layers3, Play, Repeat2, Target, TrendingUp, ChevronRight } from 'lucide-react';
import { Button, Ring, Progress } from './components.jsx';
import DailyGoal from './DailyGoal.jsx';
import { todayKey, groupedMastered, tenseFrench, notebookFor } from './api.js';

export default function Dashboard({ state, navigate, openVerb, start, mutate, busy }) {
  const { stats, history, mastered, review, wordlists, active } = state;
  const today = history[todayKey()] || { total: 0, correct: 0 };
  const rate = stats.total ? Math.round(stats.correct / stats.total * 100) : 0;
  const groups = groupedMastered(mastered).filter(m => notebookFor(state, m.verbe, m.temps) === 'known');
  const dueGroups = new Set(review.map(m => `${m.verbe}|${m.temps}`)).size;
  const recent = wordlists.filter(w => w.level === '必会');
  const date = new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' });
  const metrics = [
    { label: '累计练习', value: stats.total, unit: '题', icon: Layers3, color: 'sage', detail: '每一道，都算数', page: 'learn' },
    { label: '答题正确率', value: stats.total ? rate : '—', unit: stats.total ? '%' : '', icon: Target, color: 'lavender', detail: stats.total ? `${stats.correct} 道正确 · ${stats.total} 道练习` : '从第一组练习开始', page: 'learn' },
    { label: '已会词条', value: groups.length, unit: '组', icon: CheckCheck, color: 'sand', detail: '不再安排复习', page: 'mastered' },
    { label: '等待复习', value: dueGroups, unit: '组', icon: Repeat2, color: 'rose', detail: review.length ? '给记忆一点温柔的提醒' : '记忆在慢慢沉淀', page: 'review' },
  ];

  return <div className="page-enter dashboard">
    <div className="page-heading"><div><div className="eyebrow">VOTRE ESPACE FRANÇAIS</div><h1>Bonjour<span className="heading-comma">，</span>继续向前。</h1><p>把一点时间留给法语，让每次进步都有迹可循。</p></div><div className="date-pill"><Clock3 size={14} /><span>{date}</span></div></div>

    <div className="hero-grid">
      <section className="glass-card study-hero">
        <div className="hero-copy"><span className="soft-badge"><span className="status-dot" /> 一点专注，日有所进</span><h2>让变位，<br />成为你的直觉。</h2><p>从认识到熟练，以自己的节奏，<br className="desktop-break" />把每一个法语动词变成日常。</p><div className="hero-actions"><Button variant="primary" icon={Play} disabled={busy} onClick={() => active ? start({ resumeActive: true }) : navigate('learn')}>{active ? '继续上次练习' : '开始今日练习'}<ArrowRight size={16} /></Button><span className="hero-note">三种时态 · 循序渐进</span></div></div>
        <div className="type-sculpture" aria-hidden="true"><div className="sculpture-orbit" /><div className="floating-tile tile-back"><span>apprendre</span><small>一点一点，慢慢掌握</small></div><div className="floating-tile tile-main"><span className="tile-overline">L’ART DE CONJUGUER</span><span className="sculpture-letter">é<span>.</span></span><div className="tile-rule" /><span className="tile-caption">un peu, chaque jour.</span></div><div className="floating-tile tile-front"><span className="mini-check"><Check size={15} /></span><div><strong>je progresse</strong><small>每一天，都在进步</small></div></div></div>
      </section>
      <DailyGoal state={state} navigate={navigate} mutate={mutate} busy={busy} />
    </div>

    <div className="metric-grid">{metrics.map(({ label, value, unit, icon: Icon, color, detail, page }) => <button key={label} className="glass-card metric-card" onClick={() => navigate(page)}><div className="metric-top"><span className={`metric-icon ${color}`}><Icon size={18} strokeWidth={1.6} /></span><ArrowUpRight size={15} className="metric-arrow" /></div><span className="metric-label">{label}</span><div className="metric-value">{value}<span>{unit}</span></div><span className="metric-detail">{detail}</span></button>)}</div>

    <div className="dashboard-bottom"><section className="glass-card progress-card"><div className="section-heading"><div><span className="section-label">一步一步，积累起来</span><h2>你的学习路径</h2></div><button className="text-link" onClick={() => navigate('learn')}>全部词表 <ChevronRight size={14} /></button></div><div className="path-list">{recent.map((item, i) => <button className="path-row" key={item.tense} onClick={() => navigate('learn', { level: item.level, tense: item.tense })}><span className={`path-icon ${['sage', 'lavender', 'sand'][i]}`}><BookOpen size={19} strokeWidth={1.6} /></span><div className="path-content"><div className="path-title"><h3>{item.tense}<span lang="fr">{tenseFrench[item.tense]}</span></h3><span>{item.mastered}<span className="muted"> / {item.total}</span></span></div><Progress value={item.mastered / Math.max(item.total, 1) * 100} label={`${item.tense}掌握进度`} /><span className="path-caption">必会词表 · {item.mastered ? '继续巩固，让记忆更牢固' : '从最常见的法语动词开始'}</span></div><ChevronRight size={16} className="muted" /></button>)}</div></section>

      <section className="glass-card week-card"><div className="section-heading"><div><span className="section-label">让坚持，看得见</span><h2>最近七天</h2></div><span className="tiny-badge"><TrendingUp size={13} /> 学习足迹</span></div><div className="week-chart" role="img" aria-label={`最近七天共练习 ${Array.from({ length: 7 }, (_, i) => history[todayKey(i - 6)]?.total || 0).reduce((a, b) => a + b, 0)} 题`}>{Array.from({ length: 7 }, (_, i) => { const key = todayKey(i - 6); const total = history[key]?.total || 0; const max = Math.max(20, ...Object.values(history).map(h => h.total)); return <div className={`chart-column ${i === 6 ? 'is-today' : ''}`} key={key} title={`${key}：${total} 题`}><span className="chart-number">{total || '·'}</span><div className="bar-space"><span className="chart-bar" style={{ height: total ? `${Math.max(6, total / max * 100)}%` : '4px' }} /></div><span className="chart-label">{i === 6 ? '今天' : `${Number(key.slice(5, 7))}/${Number(key.slice(8))}`}</span></div>; })}</div><div className="week-footer"><span className="status-dot" /><span>{Object.keys(history).length ? `已记录 ${Object.keys(history).length} 天的练习，继续保持。` : '第一笔学习足迹，等你写下。'}</span></div></section>
    </div>
    <div className="dashboard-footnote"><span className="footnote-line" /><span lang="fr">Petit à petit, on va loin.</span><span>积少成多，步履不停。</span><span className="footnote-line" /></div>
  </div>;
}
