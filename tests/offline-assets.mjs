import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve, extname, sep } from 'node:path';
export async function offlineApp(page, context) {
  const errors = [], unexpected = [];
  page.on('pageerror', error => errors.push(error.message));
  const root = fileURLToPath(new URL('../dist-mobile/', import.meta.url));
  const origin = 'https://appassets.androidplatform.net';
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    const path = resolve(root, '.' + decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname));
    if (url.origin !== origin || !path.startsWith(root.endsWith(sep) ? root : root + sep) || url.pathname.startsWith('/api/')) { unexpected.push(url.href); return route.abort(); }
    try {
      const types = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.json': 'application/json' };
      await route.fulfill({ status: 200, contentType: types[extname(path)] || 'application/octet-stream', body: await readFile(path) });
    } catch { await route.fulfill({ status: 404, body: '' }); }
  });
  await context.setOffline(true);
  await page.goto(origin + '/index.html');
  return { errors, unexpected };
}
