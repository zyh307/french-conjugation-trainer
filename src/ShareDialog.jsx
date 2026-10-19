import { useEffect, useRef, useState } from 'react';
import { Check, Download, RefreshCw, Share2, Upload } from 'lucide-react';
import { Button, Modal } from './components.jsx';
import { request } from './api.js';
import { coverThemes, drawSharePoster, prepareCustomCover, canvasBlob } from './share-poster.js';
import { shareQuotes, nextQuote } from './share-quotes.js';
import './share.css';

let customCoverCache = null;
function preferences() { try { return JSON.parse(localStorage.getItem('conjugaison-share-style')) || {}; } catch { return {}; } }

export default function ShareDialog({ initialStats, onClose }) {
  const [stats, setStats] = useState(initialStats || null);
  const [quoteIndex, setQuoteIndex] = useState(() => nextQuote());
  const [customImage, setCustomImage] = useState(customCoverCache);
  const [themeId, setThemeId] = useState(() => { const id = preferences().cover; return coverThemes.some(t => t.id === id) || (id === 'custom' && customCoverCache) ? id : 'sage'; });
  const [showWords, setShowWords] = useState(() => preferences().showWords !== false);
  const [position, setPosition] = useState(50);
  const [drawing, setDrawing] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loadError, setLoadError] = useState(false);
  const canvas = useRef(null), fileInput = useRef(null);
  const quoteBag = useRef([]);
  function changeQuote() {
    if (!quoteBag.current.length) {
      const remaining = shareQuotes.map((_, i) => i).filter(i => i !== quoteIndex);
      for (let i = remaining.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [remaining[i], remaining[j]] = [remaining[j], remaining[i]]; }
      quoteBag.current = remaining;
    }
    setQuoteIndex(quoteBag.current.pop());
  }
  const quote = shareQuotes[quoteIndex];
  const loadStats = () => { setLoadError(false); request('share').then(setStats).catch(e => { setError(e.message); setLoadError(true); }); };
  useEffect(() => { let mounted = true; request('share').then(value => { if (mounted) setStats(value); }).catch(e => { if (mounted) { setError(e.message); setLoadError(true); } }); return () => { mounted = false; }; }, []);
  useEffect(() => {
    try { localStorage.setItem('conjugaison-share-style', JSON.stringify({ cover: themeId, showWords })); } catch { /* Preview and export remain available. */ }
  }, [themeId, showWords]);
  useEffect(() => {
    if (!stats || !canvas.current) return;
    const controller = new AbortController(); setDrawing(true); setError('');
    drawSharePoster(canvas.current, { stats, themeId, customImage, position, quote, showWords }, controller.signal)
      .then(() => { if (!controller.signal.aborted) setDrawing(false); })
      .catch(e => { if (!controller.signal.aborted) { setError(e.message); setDrawing(false); } });
    return () => controller.abort();
  }, [stats, themeId, customImage, position, quoteIndex, showWords]);
  useEffect(() => {
    const onResult = event => { setExporting(false); if (event.detail?.success) setMessage(event.detail.message); else setError(event.detail?.message || '操作未完成，请重试。'); };
    window.addEventListener('conjugaison-export', onResult); return () => window.removeEventListener('conjugaison-export', onResult);
  }, []);
  async function chooseImage(event) {
    const file = event.target.files?.[0]; if (!file) return;
    setError(''); setDrawing(true);
    try { const value = await prepareCustomCover(file); customCoverCache = value; setCustomImage(value); setPosition(50); setThemeId('custom'); }
    catch (e) { setError(e.message); setDrawing(false); }
    event.target.value = '';
  }
  async function download(blob) {
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = `法语学习-${stats.date}.png`; document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 10000);
    setMessage('图片已生成，可在下载记录中找到。');
  }
  async function exportImage(share) {
    if (drawing || exporting || !stats) return;
    setExporting(true); setError(''); setMessage('');
    try {
      const native = window.ConjugaisonNative;
      if (share && native?.shareImage) { native.shareImage(canvas.current.toDataURL('image/png')); return; }
      if (!share && native?.saveImage) { native.saveImage(canvas.current.toDataURL('image/png')); return; }
      const blob = await canvasBlob(canvas.current);
      const file = new File([blob], `法语学习-${stats.date}.png`, { type: 'image/png' });
      if (share && navigator.canShare?.({ files: [file] })) {
        await navigator.share({ title: '我的法语学习记录', text: `累计背词 ${stats.total_words} 个，今天 ${stats.today_words} 个。`, files: [file] });
        setMessage('分享操作已完成。');
      } else await download(blob);
      setExporting(false);
    } catch (e) { setExporting(false); if (e.name !== 'AbortError') setError(e.message || '图片导出失败，请重试。'); }
  }
  return <Modal title="把今天的进步，分享出去。" onClose={onClose} className="share-dialog"><div className="share-editor"><div className="share-preview"><div className="poster-frame"><canvas ref={canvas} role="img" aria-label={stats ? `学习分享卡片：累计背词 ${stats.total_words} 个，今日背词 ${stats.today_words} 个` : '正在生成学习分享卡片'} data-cover={themeId} />{drawing && <span className="poster-rendering">正在生成…</span>}</div><p className="share-stat-caption">累计 <strong>{stats?.total_words ?? '—'}</strong> 个动词<span>·</span>今日 <strong>{stats?.today_words ?? '—'}</strong> 个动词</p></div><div className="share-controls"><div className="share-control-heading"><span className="section-label">给记录选一个封面</span><span>1080 × 1440</span></div><div className="cover-options">{coverThemes.map(theme => <button key={theme.id} aria-label={`封面：${theme.name}`} aria-pressed={themeId === theme.id} className={`cover-option ${themeId === theme.id ? 'selected' : ''}`} onClick={() => setThemeId(theme.id)}><span className="cover-swatch" style={{ background: `linear-gradient(145deg,${theme.colors.join(',')})` }}>{themeId === theme.id ? <Check size={15} /> : <i>é</i>}</span><span>{theme.name}</span></button>)}{customImage && <button aria-label="封面：我的图片" aria-pressed={themeId === 'custom'} className={`cover-option ${themeId === 'custom' ? 'selected' : ''}`} onClick={() => setThemeId('custom')}><span className="cover-swatch custom-swatch" style={{ backgroundImage: `url(${customImage})` }}>{themeId === 'custom' && <Check size={15} />}</span><span>我的图片</span></button>}</div><input ref={fileInput} type="file" accept="image/png,image/jpeg,image/webp,image/avif" className="sr-only" aria-label="上传自选封面" onChange={chooseImage} /><Button className="custom-cover-button full-width" icon={Upload} disabled={exporting} onClick={() => fileInput.current?.click()}>从相册选择封面</Button>{themeId === 'custom' && <label className="cover-position"><span>调整封面位置</span><input type="range" min="0" max="100" value={position} onChange={e => setPosition(Number(e.target.value))} /></label>}<div className="share-quote-control"><div className="share-control-heading"><span className="section-label">送给今天的一句话</span><button className="text-link" title="随机换一句，中法双语同步更新" onClick={changeQuote}><RefreshCw size={12} /> 换一句</button></div><p lang="fr" className="share-quote-text" data-testid="share-quote">{quote.text}</p><p className="share-quote-translation">{quote.translation}</p><span className="share-quote-author">{quote.author} · {quote.work}</span></div><label className="checkbox-label share-word-toggle"><input type="checkbox" checked={showWords} onChange={e => setShowWords(e.target.checked)} /><span>在卡片上展示今天背过的动词</span></label><p className="share-count-note">完整学完、标记掌握或完成复习后计入。同一动词每天只计一次。</p></div></div><div className="share-dialog-footer"><div className="share-export-actions"><Button icon={Download} disabled={drawing || exporting || !stats} onClick={() => exportImage(false)}>保存图片</Button><Button variant="primary" icon={Share2} disabled={drawing || exporting || !stats} onClick={() => exportImage(true)}>{exporting ? '正在导出…' : '分享卡片'}</Button></div>{loadError && <button className="text-link" onClick={loadStats}>重新读取学习数据</button>}{error && <p className="share-message is-error" role="alert">{error}</p>}{message && <p className="share-message" role="status">{message}</p>}<p className="share-private-note">封面和学习记录仅在本机处理。</p></div></Modal>;
}
