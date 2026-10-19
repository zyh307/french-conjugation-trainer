export const coverThemes = [
  { id: 'sage', name: '鼠尾草', colors: ['#d9e6d4', '#f0f0e4', '#c4d6c4'], ink: '#294c39', muted: '#697d67', accent: '#537a59' },
  { id: 'linen', name: '亚麻纸', colors: ['#efe1c9', '#faf4e7', '#e1cfb6'], ink: '#604a32', muted: '#9a866b', accent: '#947452' },
  { id: 'lilac', name: '浅薰衣', colors: ['#e3d9eb', '#f4eef5', '#cfc9e1'], ink: '#514361', muted: '#8a7c99', accent: '#8e76a6' },
  { id: 'clay', name: '陶土色', colors: ['#e8d2c4', '#f8eee3', '#d4b8a9'], ink: '#624536', muted: '#96765f', accent: '#a77b63' },
  { id: 'ink', name: '深墨绿', colors: ['#203a2d', '#354d42', '#172c2b'], ink: '#edf2e6', muted: '#a4b8a4', accent: '#a6c49c', dark: true },
];

function rounded(ctx, x, y, w, h, r) {
  ctx.beginPath(); ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r); ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h); ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r); ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
}
function glass(ctx, x, y, w, h, dark) {
  ctx.save(); ctx.shadowColor = dark ? 'rgba(0,0,0,.12)' : 'rgba(50,65,39,.05)'; ctx.shadowBlur = 38; ctx.shadowOffsetY = 13;
  rounded(ctx, x, y, w, h, 32); ctx.fillStyle = dark ? 'rgba(17,36,28,.68)' : 'rgba(255,255,250,.67)'; ctx.fill();
  ctx.shadowColor = 'transparent'; ctx.lineWidth = 2; ctx.strokeStyle = dark ? 'rgba(230,244,222,.19)' : 'rgba(255,255,255,.88)'; ctx.stroke(); ctx.restore();
}
function lines(ctx, text, width) {
  const tokens = /[\u3400-\u9fff]/.test(text) ? [...text] : text.split(/\s+/);
  const separator = /[\u3400-\u9fff]/.test(text) ? '' : ' ';
  const result = []; let line = '';
  for (const token of tokens) { const candidate = line ? line + separator + token : token; if (line && ctx.measureText(candidate).width > width) { result.push(line); line = token; } else line = candidate; }
  if (line) result.push(line); return result;
}
function text(ctx, value, x, y, font, color, align = 'left') { ctx.font = font; ctx.fillStyle = color; ctx.textAlign = align; ctx.fillText(String(value), x, y); }
function loadImage(source) { return new Promise((resolve, reject) => { const image = new Image(); image.onload = () => resolve(image); image.onerror = () => reject(new Error('这张图片无法读取，请换一张 JPG、PNG 或 WebP 图片。')); image.src = source; }); }

export async function drawSharePoster(canvas, { stats, themeId, customImage, position = 50, quote, showWords = true }, signal) {
  const custom = themeId === 'custom' && customImage;
  const image = custom ? await loadImage(customImage) : null;
  await document.fonts?.ready;
  if (signal?.aborted) return;
  canvas.width = 1080; canvas.height = 1440;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('当前设备无法生成分享图片。');
  const theme = custom ? { ...coverThemes[4], ink: '#f5f6ed', muted: '#d0d9ca' } : coverThemes.find(t => t.id === themeId) || coverThemes[0];
  if (image) {
    const scale = Math.max(1080 / image.width, 1440 / image.height), w = image.width * scale, h = image.height * scale;
    ctx.drawImage(image, (1080 - w) / 2, (1440 - h) * position / 100, w, h);
    const shade = ctx.createLinearGradient(0, 0, 0, 1440); shade.addColorStop(0, 'rgba(8,23,14,.43)'); shade.addColorStop(.5, 'rgba(8,23,14,.28)'); shade.addColorStop(1, 'rgba(8,23,14,.76)'); ctx.fillStyle = shade; ctx.fillRect(0, 0, 1080, 1440);
  } else {
    const base = ctx.createLinearGradient(0, 0, 1080, 1440); theme.colors.forEach((c, i) => base.addColorStop(i / 2, c)); ctx.fillStyle = base; ctx.fillRect(0, 0, 1080, 1440);
    const tint = ctx.createRadialGradient(980, 200, 15, 980, 200, 750); tint.addColorStop(0, theme.dark ? 'rgba(148,186,134,.14)' : 'rgba(255,255,255,.47)'); tint.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = tint; ctx.fillRect(0, 0, 1080, 1440);
    ctx.save(); ctx.translate(875, 280); ctx.rotate(.18); rounded(ctx, -120, -150, 285, 315, 35); ctx.fillStyle = theme.dark ? 'rgba(205,231,197,.025)' : 'rgba(255,255,255,.14)'; ctx.fill(); ctx.strokeStyle = theme.dark ? 'rgba(215,235,207,.13)' : 'rgba(255,255,255,.55)'; ctx.lineWidth = 2; ctx.stroke(); text(ctx, 'é', -59, 91, 'italic 220px Georgia,serif', theme.dark ? 'rgba(220,235,210,.14)' : 'rgba(113,139,101,.15)'); ctx.restore();
  }
  const sans = '"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif';
  ctx.save(); rounded(ctx, 78, 77, 68, 73, 20); ctx.fillStyle = theme.dark ? 'rgba(221,239,210,.14)' : 'rgba(74,111,74,.82)'; ctx.fill(); ctx.strokeStyle = 'rgba(255,255,255,.4)'; ctx.lineWidth = 1.5; ctx.stroke(); text(ctx, 'ç', 109, 130, 'italic 64px Georgia,serif', '#f8faf0', 'center'); ctx.restore();
  text(ctx, 'CONJUGAISON', 166, 108, `600 27px ${sans}`, theme.ink);
  text(ctx, '法语变位器 · 学习记录', 168, 140, `21px ${sans}`, theme.muted);
  text(ctx, stats.date.replaceAll('-', '.'), 1000, 116, `23px ${sans}`, theme.muted, 'right');
  text(ctx, 'UN PEU, CHAQUE JOUR.', 83, 250, `500 21px ${sans}`, theme.muted);
  text(ctx, '把法语，慢慢变成日常。', 80, 315, `500 49px ${sans}`, theme.ink);
  glass(ctx, 72, 379, 936, 397, theme.dark);
  text(ctx, '每一次认真，都有迹可循', 117, 437, `25px ${sans}`, theme.muted);
  ctx.strokeStyle = theme.dark ? 'rgba(231,241,220,.13)' : 'rgba(91,112,78,.12)'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(548, 495); ctx.lineTo(548, 704); ctx.stroke();
  text(ctx, '累计背词', 119, 516, `28px ${sans}`, theme.muted);
  text(ctx, '今日背词', 610, 516, `28px ${sans}`, theme.muted);
  text(ctx, stats.total_words, 114, 670, `500 ${stats.total_words > 999 ? 112 : 137}px ${sans}`, theme.ink);
  text(ctx, stats.today_words, 604, 670, `500 137px ${sans}`, theme.ink);
  text(ctx, '个动词', 124, 718, `25px ${sans}`, theme.muted);
  text(ctx, '个动词', 615, 718, `25px ${sans}`, theme.muted);
  glass(ctx, 72, 818, 936, 398, theme.dark);
  text(ctx, '«', 113, 909, '84px Georgia,serif', theme.accent);
  let size = 47, quoteLines;
  do { ctx.font = `italic ${size}px Georgia,serif`; quoteLines = lines(ctx, quote.text, 829); if (quoteLines.length <= 3) break; size -= 2; } while (size >= 33);
  quoteLines.forEach((line, i) => text(ctx, line, 119, 952 + i * 59, `italic ${size}px Georgia,serif`, theme.ink));
  const translationY = Math.min(1118, 952 + quoteLines.length * 59 + 13);
  ctx.font = `25px ${sans}`;
  lines(ctx, quote.translation, 829).forEach((line, i) => text(ctx, line, 120, translationY + i * 32, `25px ${sans}`, theme.muted));
  text(ctx, `— ${quote.author}`, 120, 1168, `23px ${sans}`, theme.ink);
  text(ctx, quote.work, 961, 1168, 'italic 21px Georgia,serif', theme.muted, 'right');
  if (showWords && stats.today_verbs.length) {
    const verbs = stats.today_verbs.slice(0, 7).join(' · ') + (stats.today_verbs.length > 7 ? ' …' : '');
    text(ctx, '今天的积累', 85, 1275, `23px ${sans}`, theme.muted);
    ctx.font = `26px ${sans}`;
    const wordLines = lines(ctx, verbs, 910).slice(0, 2);
    wordLines.forEach((line, i) => text(ctx, line, 85, 1315 + i * 34, `26px ${sans}`, theme.ink));
  } else text(ctx, '积少成多，步履不停。', 85, 1297, `25px ${sans}`, theme.muted);
  ctx.strokeStyle = theme.dark ? 'rgba(231,241,220,.13)' : 'rgba(91,112,78,.13)'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(84, 1372); ctx.lineTo(995, 1372); ctx.stroke();
  text(ctx, 'Fait pour votre rythme.', 85, 1412, 'italic 21px Georgia,serif', theme.muted);
  text(ctx, '一点一点，每天向前。', 995, 1412, `20px ${sans}`, theme.muted, 'right');
}

export async function prepareCustomCover(file) {
  if (!file || !/^image\/(png|jpe?g|webp|avif)$/.test(file.type)) throw new Error('请选择 JPG、PNG、WebP 或 AVIF 图片。');
  if (file.size > 20 * 1024 * 1024) throw new Error('图片超过 20MB，请选择较小的图片。');
  const url = URL.createObjectURL(file);
  try {
    const image = await loadImage(url), scale = Math.min(1, 1800 / Math.max(image.width, image.height));
    const canvas = document.createElement('canvas'); canvas.width = Math.round(image.width * scale); canvas.height = Math.round(image.height * scale);
    canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', .90);
  } finally { URL.revokeObjectURL(url); }
}

export function canvasBlob(canvas) { return new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('图片生成失败，请重试。')), 'image/png')); }
