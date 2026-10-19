import { useState } from 'react';
import { ArrowRight, Target } from 'lucide-react';
import { Button, Ring } from './components.jsx';

export default function DailyGoal({ state, navigate, mutate, busy }) {
  const goal = state.settings.daily_goal || 3;
  const count = state.share_stats?.today_words || 0;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(goal);
  return <section className="glass-card daily-card"><div className="card-topline"><span className="section-label">今日小目标</span><Target size={17} className="muted" /></div>
    <Ring value={count / goal * 100} label={`今日完成 ${count} 个动词，目标 ${goal} 个`}><strong>{count}<span> / {goal}</span></strong><span>今日完成动词</span></Ring>
    <h3>{count >= goal ? '今天的小目标，已达成' : '不必着急，保持节奏'}</h3><p>每天 {goal} 个动词，同一个词当天只计一次。</p>
    {editing ? <form className="goal-editor" onSubmit={async e => { e.preventDefault(); const result = await mutate('settings', { daily_goal: Number(draft) }, '每日小目标已保存。'); if (result) setEditing(false); }}><label htmlFor="daily-goal">每日目标（个动词）</label><div><input id="daily-goal" type="number" min="1" max="100" required value={draft} onChange={e => setDraft(e.target.value)} /><Button type="submit" disabled={busy}>保存</Button><button type="button" className="text-link" onClick={() => setEditing(false)}>取消</button></div></form> : <div className="goal-actions"><button className="text-link" onClick={() => navigate('learn')}>去练习 <ArrowRight size={14} /></button><button className="text-link" onClick={() => { setDraft(goal); setEditing(true); }}>修改目标</button></div>}
  </section>;
}
