import { Check, ChevronRight, Database, Keyboard, Monitor, Palette, ShieldCheck, SlidersHorizontal } from 'lucide-react';
import { Toggle } from './components.jsx';
import { isDevice } from './api.js';

export default function Settings({ state, mutate, busy, theme, setTheme, showHelp }) {
  const settings = state.settings;
  const sections = [
    { title: '让练习更适合你', description: '小小的调整，找到舒服的学习方式。', rows: [
      ['fuzzy', '模糊匹配', '忽略重音符号、大小写及标点的差异。关闭后严格核对。'],
      ['show_stem', '词干提示', '拼写练习中显示词干与后缀长度，给记忆一点线索。'],
    ] },
    { title: '练习题型', description: '自由组合练习方式，掌握程度判断始终保留。', rows: [
      ['enable_reverse', '反向选择', '看变位形式，选择对应的人称。'],
      ['enable_choice', '选择变位', '在多个选项中，辨认正确的变位。'],
      ['enable_fill', '拼写练习', '亲手写下答案，加深对词形的记忆。'],
    ] },
  ];
  return <div className="page-enter settings-page"><div className="page-heading"><div><div className="eyebrow">À VOTRE FAÇON</div><h1>你的空间，你的节奏。</h1><p>把细节调到刚好，让学习自然一点。</p></div><span className="soft-badge"><SlidersHorizontal size={14} /> 偏好设置</span></div><section className="glass-card settings-section"><div className="section-heading"><div><h2>外观</h2><p>选择适合此刻的玻璃质感。</p></div><Palette size={19} className="muted" /></div><div className="theme-options">{[['light', '浅色', '柔和、明净'], ['dark', '深色', '沉静、专注'], ['system', '跟随系统', '与你的设备同步']].map(([value, title, description]) => <button key={value} className={`theme-option ${theme === value ? 'selected' : ''}`} aria-pressed={theme === value} onClick={() => setTheme(value)}><div className={`theme-preview preview-${value}`} aria-hidden="true"><span className="preview-sidebar" /><span className="preview-card one" /><span className="preview-card two" /></div><div><span><strong>{title}</strong><small>{description}</small></span><span className="selection-dot">{theme === value && <Check size={11} />}</span></div></button>)}</div></section>{sections.map(section => <section className="glass-card settings-section" key={section.title}><div className="section-heading"><div><h2>{section.title}</h2><p>{section.description}</p></div><span className="saved-label"><Check size={13} /> 自动保存</span></div>{section.rows.map(([key, title, description]) => <div className="setting-row" key={key}><div><h3>{title}</h3><p>{description}</p></div><Toggle label={title} checked={settings[key]} disabled={busy} onChange={value => mutate('settings', { [key]: value }, '偏好已保存，将在下一组练习生效。')} /></div>)}</section>)}<section className="glass-card settings-section data-section"><div className="section-heading"><div><h2>安心留在本机</h2><p>学习进度与偏好只保存在当前设备。</p></div><ShieldCheck size={20} className="muted" /></div><div className="data-info"><Database size={18} /><div><strong>本地数据与自动备份</strong><p>{isDevice ? '所有题库和练习都在手机内运行，保存时保留上一份记录。' : '进度实时写入 data 文件夹，更新时保留上一份备份。'}</p></div><span className="tiny-badge">本地存储</span></div><button className="setting-help" onClick={showHelp}><Keyboard size={18} /><span>查看键盘快捷键</span><ChevronRight size={16} /></button></section><div className="about-footer"><span className="brand-mark small">ç</span><div><strong>Conjugaison <span>3.0</span></strong><p>法语变位器 · 专注每一个小小的进步</p></div><span className="about-version">{isDevice ? '安卓离线版 · 3.0.5' : 'React + 原版学习核心'}</span></div></div>;
}
