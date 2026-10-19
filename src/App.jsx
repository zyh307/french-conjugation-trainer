import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowRight, Bell, BookOpen, Check, CheckCheck, ChevronRight, CircleHelp, Command, Database, LayoutDashboard, Maximize2, Menu, NotebookPen, Palette, PanelLeftClose, PanelLeftOpen, Repeat2, Search, Share2, Settings as SettingsIcon, ShieldCheck, X } from 'lucide-react';
import Dashboard from './Dashboard.jsx';
import { LearnSetup, Practice, ReviewSetup } from './Learning.jsx';
import { Collection } from './Library.jsx';
import Settings from './Settings.jsx';
import Wordbook from './Wordbook.jsx';
import ShareDialog from './ShareDialog.jsx';
import { Button, CommandPalette, Empty, Modal } from './components.jsx';
import { request, isDevice } from './api.js';

const navigation = [
  { id: 'home', title: '学习总览', french: 'Mon espace', icon: LayoutDashboard },
  { id: 'learn', title: '开始学习', french: 'Apprendre', icon: BookOpen },
  { id: 'review', title: '智能复习', french: 'Réviser', icon: Repeat2 },
  { id: 'errors', title: '错题本', french: 'Mes erreurs', icon: NotebookPen },
  { id: 'mastered', title: '已掌握', french: 'Mes acquis', icon: CheckCheck },
  { id: 'dictionary', title: '动词词典', french: 'Dictionnaire', icon: Search },
];
const getRoute = () => [...navigation.map(n => n.id), 'settings'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'home';

export default function App() {
  const [page, setPage] = useState(getRoute);
  const [state, setState] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [busy, setBusy] = useState(false);
  const operationRef = useRef(false);
  const [toast, setToast] = useState(null);
  const [modal, setModal] = useState(null);
  const [commandOpen, setCommandOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [theme, updateTheme] = useState(() => { try { return localStorage.getItem('conjugaison-theme') || 'light'; } catch { return 'light'; } });
  const [selection, setSelection] = useState({ level: '必会', tense: '现在时' });
  const [practice, setPractice] = useState(false);
  const [question, setQuestion] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [dictionary, setDictionary] = useState(null);
  const [dictionaryError, setDictionaryError] = useState('');
  const [selectedVerb, setSelectedVerb] = useState('être');
  const mainRef = useRef(null);
  const showToast = useCallback((message, error = false) => setToast({ message, error, id: Date.now() }), []);
  const refresh = useCallback(async () => {
    try { const next = await request('state'); setState(next); setLoadError(''); return next; }
    catch (e) { setLoadError(isDevice ? e.message : '本地服务暂时无法连接，请确认启动窗口仍然打开。'); throw e; }
  }, []);
  useEffect(() => { refresh().catch(() => {}); }, [refresh]);
  useEffect(() => {
    const onRoute = () => { setPage(getRoute()); setPractice(false); };
    window.addEventListener('hashchange', onRoute); window.addEventListener('popstate', onRoute);
    return () => { window.removeEventListener('hashchange', onRoute); window.removeEventListener('popstate', onRoute); };
  }, []);
  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const apply = () => { document.documentElement.dataset.theme = theme === 'system' ? media.matches ? 'dark' : 'light' : theme; };
    apply(); media.addEventListener('change', apply); return () => media.removeEventListener('change', apply);
  }, [theme]);
  useEffect(() => { if (!toast) return; const timer = setTimeout(() => setToast(null), toast.error ? 6500 : 3200); return () => clearTimeout(timer); }, [toast]);
  useEffect(() => { mainRef.current?.scrollTo({ top: 0, behavior: 'instant' }); }, [page, practice]);
  const loadDictionary = useCallback(() => {
    setDictionaryError('');
    request('dictionary').then(setDictionary).catch(() => setDictionaryError('词典加载失败，请确认本地服务仍在运行。'));
  }, []);
  useEffect(() => { if (page === 'dictionary' && !dictionary && !dictionaryError) loadDictionary(); }, [page, dictionary, dictionaryError, loadDictionary]);

  const setTheme = value => { updateTheme(value); try { localStorage.setItem('conjugaison-theme', value); } catch { /* Theme still works for this session. */ } };
  const navigate = useCallback((id, nextSelection) => {
    if (nextSelection) setSelection(s => ({ ...s, ...nextSelection }));
    setPage(id); setPractice(false); setSidebarOpen(false);
    if (location.hash !== `#${id}`) history.pushState(null, '', `#${id}`);
  }, []);
  const leavePractice = useCallback(() => { setPractice(false); setFeedback(null); refresh().catch(() => {}); }, [refresh]);
  useEffect(() => {
    function onKey(e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); if (state) setCommandOpen(v => !v); }
      if (e.key === 'Escape' && !document.querySelector('dialog[open]')) { if (sidebarOpen) setSidebarOpen(false); else if (practice) leavePractice(); else if (page !== 'home') navigate('home'); }
    }
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey);
  }, [state, sidebarOpen, practice, page, navigate, leavePractice]);

  const perform = async callback => {
    if (operationRef.current) return null;
    operationRef.current = true; setBusy(true);
    try { return await callback(); }
    catch (e) { showToast(e.message === 'Failed to fetch' ? '无法连接本地服务，请检查启动窗口。' : e.message, true); return null; }
    finally { operationRef.current = false; setBusy(false); }
  };
  const mutate = (path, data, message) => perform(async () => { const result = await request(path, data); await refresh(); if (message) showToast(message); return result; });
  const start = options => perform(async () => {
    const q = options.resumeActive ? await request('session/resume', {}) : await request('session/start', { mode: 'learn', ...options });
    navigate(q.direct ? 'dictionary' : q.mode === 'review' || options.mode === 'review' ? 'review' : 'learn');
    setQuestion(q); setFeedback(null); setPractice(true); await refresh();
  });
  const answer = data => perform(async () => {
    const result = await request('session/answer', data);
    if (result.judged) { setQuestion(result.next); setFeedback(null); }
    else setFeedback(result);
    await refresh();
  });
  const nextQuestion = () => { if (feedback) { setQuestion(feedback.next); setFeedback(null); } };
  const openVerb = verb => { setSelectedVerb(verb); navigate('dictionary'); };
  const reset = s => setModal({ type: 'confirm', title: '重新开始这组练习？', description: `将重置「${s.level} · ${s.tense}」的答题位置。已掌握词条、错题与统计会保留。`, action: '重置练习进度', onConfirm: () => mutate('progress/reset', s, '这组练习已重置，可以重新开始。') });
  const confirm = options => setModal({ type: 'confirm', ...options });
  const help = () => setModal({ type: 'help' });
  const fullscreen = async () => {
    try { if (document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen(); }
    catch { showToast('此窗口不支持全屏，可使用浏览器全屏快捷键。'); }
  };
  const activeTitle = page === 'settings' ? '偏好设置' : navigation.find(n => n.id === page)?.title;

  return <><a className="skip-link" href="#main-content">跳到主要内容</a><div className="ambient-background" aria-hidden="true"><div className="ambient-shape shape-sage" /><div className="ambient-shape shape-lilac" /><div className="ambient-shape shape-peach" /></div><div className={`app-window ${isDevice ? "device-app" : ""} ${practice ? "is-practicing" : ""} ${collapsed ? 'sidebar-collapsed' : ''} ${sidebarOpen ? 'mobile-menu-open' : ''}`}>
    <aside className="sidebar" aria-label="主导航"><div className="window-controls" aria-hidden="true"><span /><span /><span /></div><button className="brand" onClick={() => navigate('home')} aria-label="法语变位器，回到学习总览"><span className="brand-mark">ç</span><span className="brand-text"><strong>Conjugaison<span className="version">3.0</span></strong><span>你的法语学习空间</span></span></button><div className="nav-section-label">我的空间</div><nav>{navigation.map(({ id, title, french, icon: Icon }) => <button className={`nav-item ${page === id ? 'active' : ''}`} key={id} aria-current={page === id ? 'page' : undefined} aria-label={title} title={collapsed ? title : undefined} onClick={() => navigate(id)}><Icon size={19} strokeWidth={1.6} /><span>{title}</span>{id === 'review' && state?.review.length > 0 && <span className="nav-count">{state.review.length}</span>}{id === 'home' && page === id && <span className="nav-active-dot" />}</button>)}</nav><div className="sidebar-bottom"><div className="sidebar-quote"><span className="quote-hairline" /><p lang="fr">Un peu, chaque jour.</p><span>每天一点，走得更远。</span></div><button className={`nav-item ${page === 'settings' ? 'active' : ''}`} aria-label="偏好设置" aria-current={page === 'settings' ? 'page' : undefined} onClick={() => navigate('settings')}><SettingsIcon size={19} strokeWidth={1.6} /><span>偏好设置</span></button><button className="profile-card" onClick={() => navigate('mastered')} aria-label="查看我的学习成果"><span className="avatar">我</span><span><strong>法语学习者</strong><small><span className="status-dot" /> 在自己的节奏里</small></span><ChevronRight size={15} /></button></div></aside>
    {sidebarOpen && <button className="sidebar-scrim" aria-label="关闭导航" onClick={() => setSidebarOpen(false)} />}
    <div className="workspace"><header className="topbar"><div className="topbar-leading"><button className="icon-button desktop-sidebar-toggle" aria-label={collapsed ? '展开侧栏' : '收起侧栏'} onClick={() => setCollapsed(v => !v)}>{collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}</button><button className="icon-button mobile-menu-toggle" aria-label="打开导航" onClick={() => setSidebarOpen(true)}><Menu size={20} /></button><div className="breadcrumbs"><span>个人学习空间</span><ChevronRight size={12} /><strong>{activeTitle}</strong></div></div><div className="topbar-actions"><button className="global-search" onClick={() => setCommandOpen(true)} disabled={!state}><Search size={15} /><span>搜索动词或前往…</span><kbd><Command size={10} /> K</kbd></button><div className="toolbar-divider" /><button className="icon-button" aria-label="分享学习记录" title="分享学习记录" disabled={!state} onClick={() => setModal({ type: "share" })}><Share2 size={18} /></button><button className="icon-button" aria-label="切换浅色或深色外观" title="切换外观" onClick={() => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark')}><Palette size={18} /></button><button className="icon-button notification-button" aria-label="查看复习提醒" title="复习提醒" onClick={() => setModal({ type: 'notifications' })}><Bell size={18} />{state?.review.length > 0 && <span />}</button><button className="icon-button fullscreen-toggle" aria-label="切换全屏" title="全屏" onClick={fullscreen}><Maximize2 size={16} /></button></div></header>
    <main id="main-content" tabIndex={-1} ref={mainRef} className="main-content">{!state ? <div className="loading-screen"><span className="brand-mark">ç</span>{loadError ? <><h2>先和本地服务重新连上。</h2><p>{loadError}</p><Button variant="primary" onClick={() => refresh().catch(() => {})}>重新连接</Button></> : <><span className="loading-indicator" /><p>正在打开你的法语空间…</p></>}</div> : <>{loadError && <div className="connection-banner" role="alert">{loadError}<button onClick={() => refresh().catch(() => {})}>重新连接</button></div>}{practice ? <Practice question={question} feedback={feedback} answer={answer} next={nextQuestion} busy={busy} leave={leavePractice} share={() => setModal({ type: "share" })} /> : page === 'home' ? <Dashboard state={state} navigate={navigate} openVerb={openVerb} start={start} mutate={mutate} busy={busy} /> : page === 'learn' ? <LearnSetup state={state} selection={selection} setSelection={setSelection} start={start} busy={busy} reset={reset} /> : page === 'review' ? <ReviewSetup state={state} start={start} busy={busy} navigate={navigate} /> : page === 'errors' || page === 'mastered' ? <Collection key={page} kind={page} state={state} navigate={navigate} mutate={mutate} confirm={confirm} start={start} busy={busy} /> : page === 'dictionary' ? dictionaryError ? <section className="glass-card"><Empty icon={Database} title="词典暂时没有打开" action={<Button onClick={loadDictionary}>重新加载</Button>}>{dictionaryError}</Empty></section> : <Wordbook start={start} mutate={mutate} busy={busy} state={state} dictionary={dictionary} selectedVerb={selectedVerb} setSelectedVerb={setSelectedVerb} navigate={navigate} /> : <Settings state={state} mutate={mutate} busy={busy} theme={theme} setTheme={setTheme} showHelp={help} />}</>}</main>
    {isDevice && !practice && <nav className="bottom-navigation" aria-label="手机底部导航">{[{id:'home',title:'总览',icon:LayoutDashboard},{id:'learn',title:'学习',icon:BookOpen},{id:'review',title:'复习',icon:Repeat2},{id:'dictionary',title:'词典',icon:Search},{id:'settings',title:'设置',icon:SettingsIcon}].map(({id,title,icon:Icon}) => <button key={id} className={page === id ? 'active' : ''} aria-label={`底部导航：${title}`} aria-current={page === id ? 'page' : undefined} onClick={() => navigate(id)}><Icon size={19} strokeWidth={1.7} /><span>{title}</span></button>)}</nav>}<footer className="statusbar"><span><span className="status-dot" />{state ? isDevice ? '离线可用 · 进度保存在此设备' : '学习数据保存在本机' : isDevice ? '正在读取学习记录' : '正在连接本地服务'}</span><span lang="fr">Fait pour votre rythme.</span><button onClick={help}><CircleHelp size={13} /><span>快捷键与帮助</span></button></footer></div>
  </div>
  {toast && <div key={toast.id} className={`toast ${toast.error ? 'error' : ''}`} role={toast.error ? 'alert' : 'status'}><span>{toast.error ? <CircleHelp size={17} /> : <Check size={17} />}</span><p>{toast.message}</p><button className="icon-button" aria-label="关闭通知" onClick={() => setToast(null)}><X size={15} /></button></div>}
  {commandOpen && state && <CommandPalette verbs={state.verbs} navigate={navigate} openVerb={openVerb} onClose={() => setCommandOpen(false)} />}
  {modal?.type === 'share' && <ShareDialog initialStats={state?.share_stats} onClose={() => setModal(null)} />}{modal?.type === 'help' && <Modal title="给专注，少一点打断。" onClose={() => setModal(null)}><p className="dialog-description">用熟悉的快捷键，在学习空间里自在切换。</p><div className="shortcut-list">{[['搜索动词 / 快速前往', '⌘ / Ctrl', 'K'], ['保存并返回 / 关闭面板', 'Esc'], ['选择答题选项', '1 – 6'], ['确认答案 / 继续下一题', 'Enter']].map(([label, ...keys]) => <div key={label}><span>{label}</span><span>{keys.map(key => <kbd key={key}>{key}</kbd>)}</span></div>)}</div><div className="help-note"><ShieldCheck size={18} /><p>每次答题后自动保存。下次回到学习总览，选择「继续上次练习」即可接着学。</p></div></Modal>}
  {modal?.type === 'notifications' && <Modal title="你的复习提醒" onClose={() => setModal(null)}>{state?.review.length ? <div className="notification-content"><span className="metric-icon sage"><Repeat2 size={23} /></span><h3>{state.review.length} 个人称变位到了复习时间。</h3><p>花一点时间回顾，让记忆留得更久。</p><Button variant="primary" onClick={() => { navigate('review'); setModal(null); }}>前往智能复习 <ArrowRight size={16} /></Button></div> : <Empty icon={CheckCheck} title="一切就绪，按你的节奏来。">暂时没有到期的复习，新提醒会在这里出现。</Empty>}</Modal>}
  {modal?.type === 'confirm' && <Modal title={modal.title} onClose={() => { if (!busy) setModal(null); }}><p className="dialog-description">{modal.description}</p><div className="dialog-actions"><Button disabled={busy} onClick={() => setModal(null)}>再想想</Button><Button variant={modal.destructive ? 'danger' : 'primary'} disabled={busy} onClick={async () => { const result = await modal.onConfirm(); if (result !== null) setModal(null); }}>{busy ? '正在保存…' : modal.action}</Button></div></Modal>}
  </>;
}
