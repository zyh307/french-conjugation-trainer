import { useEffect, useRef } from 'react';
import { ArrowRight, X, Search, Check, BookOpen } from 'lucide-react';
import { normalize } from './api.js';

export function Button({ children, icon: Icon, variant = 'secondary', className = '', ...props }) {
  return <button className={`button ${variant} ${className}`} {...props}>{Icon && <Icon size={16} strokeWidth={1.7} />}{children}</button>;
}

export function Empty({ icon: Icon = BookOpen, title, children, action }) {
  return <div className="empty-state"><div className="empty-icon"><Icon size={26} strokeWidth={1.3} /></div><h3>{title}</h3><p>{children}</p>{action}</div>;
}

export function Modal({ title, children, onClose, className = '' }) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current; el.showModal();
    return () => { if (el.open) el.close(); };
  }, []);
  return <dialog ref={ref} className={`glass-dialog ${className}`} onCancel={e => { e.preventDefault(); onClose(); }} onClick={e => { if (e.target === e.currentTarget) onClose(); }} aria-label={title}>
    <div className="dialog-header"><h2>{title}</h2><button className="icon-button" aria-label="关闭对话框" onClick={onClose}><X size={18} /></button></div>{children}
  </dialog>;
}

export function SearchBox({ value, onChange, placeholder, label = '搜索', ...props }) {
  return <div className="search-box"><Search size={17} strokeWidth={1.7} /><input aria-label={label} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} {...props} />{value && <button className="icon-button compact" aria-label="清除搜索" onClick={() => onChange('')}><X size={14} /></button>}</div>;
}

export function Segments({ options, value, onChange, label }) {
  return <div className="segments" role="group" aria-label={label}>{options.map(option => <button key={option} aria-pressed={value === option} className={value === option ? 'selected' : ''} onClick={() => onChange(option)}>{option}</button>)}</div>;
}

export function Progress({ value, label }) {
  return <div className="progress-track" role="progressbar" aria-label={label} aria-valuenow={Math.round(value)} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }} /></div>;
}

export function Ring({ value, children, label }) {
  return <div className="ring" role="img" aria-label={label}><svg viewBox="0 0 160 160" aria-hidden="true"><circle className="ring-track" cx="80" cy="80" r="67" /><circle className="ring-value" cx="80" cy="80" r="67" style={{ strokeDasharray: '421', strokeDashoffset: 421 * (1 - Math.min(value, 100) / 100) }} /></svg><div className="ring-content">{children}</div></div>;
}

export function CommandPalette({ verbs, onClose, navigate, openVerb }) {
  const input = useRef(null);
  useEffect(() => { input.current?.focus(); }, []);
  // Search terms are kept inside the modal so opening it always starts fresh.
  return <CommandContent input={input} verbs={verbs} onClose={onClose} navigate={navigate} openVerb={openVerb} />;
}

import { useState } from 'react';
function CommandContent({ input, verbs, onClose, navigate, openVerb }) {
  const [query, setQuery] = useState('');
  const matches = verbs.filter(v => normalize(v).includes(normalize(query.trim()))).slice(0, 7);
  const pages = [['learn', '开始一组练习'], ['review', '查看待复习'], ['errors', '打开错题本'], ['settings', '偏好设置']];
  return <Modal title="快速前往" onClose={onClose} className="command-dialog"><SearchBox value={query} onChange={setQuery} ref={input} autoFocus placeholder="搜索法语动词，或跳转到功能…" label="快速搜索" onKeyDown={e => { if (e.key === 'Enter' && query && matches[0]) { openVerb(matches[0]); onClose(); } }} />
    <div className="command-results">{!query && <><p className="section-label">快捷操作</p>{pages.map(([id, title]) => <button className="command-item" key={id} onClick={() => { navigate(id); onClose(); }}><BookOpen size={17} /><span>{title}</span><ArrowRight size={15} /></button>)}<p className="section-label">查找动词</p></>}
      {matches.map(v => <button className="command-item" key={v} onClick={() => { openVerb(v); onClose(); }}><span className="verb-initial">{v[0]}</span><span lang="fr">{v}</span><ArrowRight size={15} /></button>)}
      {query && !matches.length && <p className="muted command-empty">没有找到这个动词，试试 parler 或 être。</p>}
    </div><div className="command-footer"><span>输入时支持忽略重音符号</span><kbd>esc</kbd><span>关闭</span></div></Modal>;
}

export function Toggle({ checked, onChange, label, disabled }) {
  return <button role="switch" aria-checked={checked} aria-label={label} disabled={disabled} className={`toggle ${checked ? 'on' : ''}`} onClick={() => onChange(!checked)}><span>{checked && <Check size={10} strokeWidth={3} />}</span></button>;
}
