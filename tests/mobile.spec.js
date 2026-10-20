import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve, extname, sep } from 'node:path';

test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 1 });
test('offline Android assets, three-verb order, compact question and persisted progress', async ({ page, context }) => {
  const errors = [], unexpected = [];
  page.on('pageerror', error => errors.push(error.message));
  const root = fileURLToPath(new URL('../dist-mobile/', import.meta.url));
  const origin = 'https://appassets.androidplatform.net';
  // Mirror MainActivity's local HTTPS asset interceptor. No API or network service.
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
  await expect(page.getByRole('heading', { name: 'Bonjour，继续向前。' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: '手机底部导航' })).toBeVisible();
  await page.getByRole('button', { name: '底部导航：学习' }).click();
  await page.getByLabel('动词数量').fill('6');
  await page.getByRole('button', { name: '开始这一组' }).click();
  const verbs = [];
  for (let i = 0; i < 3; i++) {
    await expect(page.locator('.practice-batch')).toContainText('第 1 / 2 组');
    await expect(page.locator('.practice-card-top .soft-badge')).toHaveText('掌握度判断');
    verbs.push(await page.locator('.practice-question h1').innerText());
    // All three actions must fit without scrolling this 390 x 844 screen.
    const bounds = await page.getByRole('button', { name: '熟悉，加入已会', exact: true }).boundingBox();
    expect(bounds.y + bounds.height).toBeLessThan(790);
    if (i === 0) await page.screenshot({ path: 'preview-mobile-practice.png', fullPage: true });
    await page.getByRole('button', { name: '还不熟悉', exact: true }).click();
  }
  expect(new Set(verbs).size).toBe(3);
  await expect(page.locator('.practice-card-top .soft-badge')).toHaveText('选择变位');
  await page.screenshot({ path: 'preview-mobile-options.png', fullPage: true });
  const before = await page.locator('.practice-question h1').innerText();
  await page.reload();
  await page.getByRole('button', { name: '保存并离开' }).isVisible().then(async visible => {
    if (!visible) { await page.getByRole('button', { name: '打开导航', exact: true }).click(); await page.getByRole('button', { name: '学习总览', exact: true }).click(); await page.getByRole('button', { name: '继续上次练习' }).click(); }
  });
  await expect(page.locator('.practice-question h1')).toHaveText(before);
  await expect(page.locator('.practice-batch')).toContainText('第 1 / 2 组');
  await page.getByRole('button', { name: '保存并离开' }).click();
  await page.getByRole('button', { name: '底部导航：词典' }).click();
  await expect(page.locator('.verb-detail-header h2')).toHaveText('être');
  await expect(page.locator('.tense-table-card')).toHaveCount(3);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(unexpected).toEqual([]); expect(errors).toEqual([]);
});
