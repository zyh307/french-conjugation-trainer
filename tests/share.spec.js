import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { offlineApp } from './offline-assets.mjs';

test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 1 });
test('share real word counts, change quote, choose covers, upload a photo and export PNG', async ({ page, context }) => {
  const { errors, unexpected } = await offlineApp(page, context);
  await page.getByRole('button', { name: '底部导航：学习' }).click();
  await page.getByRole('button', { name: '开始这一组' }).click();
  for (let i = 0; i < 3; i++) await page.getByRole('button', { name: '已经掌握', exact: true }).click();
  await page.getByRole('button', { name: '分享这次进步' }).click();
  await expect(page.locator('.share-stat-caption')).toContainText('累计 3 个动词');
  await expect(page.locator('.share-stat-caption')).toContainText('今日 3 个动词');
  const save = page.getByRole('button', { name: '保存图片', exact: true });
  await expect(save).toBeEnabled();
  const oldQuote = await page.getByTestId('share-quote').innerText();
  const oldChinese = await page.locator('.share-quote-translation').innerText();
  await page.getByRole('button', { name: '换一句', exact: true }).click();
  await expect(page.getByTestId('share-quote')).not.toHaveText(oldQuote);
  await expect(page.locator('.share-quote-translation')).not.toHaveText(oldChinese);
  const seen = new Set([oldQuote, await page.getByTestId('share-quote').innerText()]);
  for (let i = 0; i < 13; i++) {
    await page.getByRole('button', { name: '换一句', exact: true }).click();
    const quote = await page.getByTestId('share-quote').innerText();
    expect(seen.has(quote)).toBe(false); seen.add(quote);
    await expect(page.locator('.share-quote-translation')).toContainText(/[\u3400-\u9fff]/);
  }
  expect(seen.size).toBe(15);
  await page.getByRole('button', { name: '封面：浅薰衣', exact: true }).click();
  await expect(page.locator('.poster-frame canvas')).toHaveAttribute('data-cover', 'lilac');
  await expect(save).toBeEnabled();
  const custom = await page.evaluate(() => { const c = document.createElement('canvas'); c.width = 300; c.height = 450; const x = c.getContext('2d'); const g = x.createLinearGradient(0, 0, 300, 450); g.addColorStop(0, '#603552'); g.addColorStop(1, '#16352d'); x.fillStyle = g; x.fillRect(0, 0, 300, 450); return c.toDataURL('image/png').split(',')[1]; });
  await page.getByLabel('上传自选封面').setInputFiles({ name: 'my-cover.png', mimeType: 'image/png', buffer: Buffer.from(custom, 'base64') });
  await expect(page.locator('.poster-frame canvas')).toHaveAttribute('data-cover', 'custom');
  await expect(save).toBeEnabled();
  await page.screenshot({ path: 'preview-share-mobile.png', fullPage: true });
  const downloadPromise = page.waitForEvent('download');
  await save.click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^法语学习-.*\.png$/);
  await download.saveAs('tests/.tmp/share-card.png');
  const png = await readFile('tests/.tmp/share-card.png');
  expect(png.subarray(0, 8).toString('hex')).toBe('89504e470d0a1a0a');
  expect(png.readUInt32BE(16)).toBe(1080); expect(png.readUInt32BE(20)).toBe(1440);

  // Exercise Android bridge dispatch without actually sending to another app.
  await page.evaluate(() => {
    window.__posterCalls = [];
    window.ConjugaisonNative = { shareImage(data) { window.__posterCalls.push(data); window.dispatchEvent(new CustomEvent('conjugaison-export', { detail: { success: true, message: '已打开系统分享。' } })); } };
  });
  await page.getByRole('button', { name: '分享卡片', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('已打开系统分享');
  expect(await page.evaluate(() => window.__posterCalls[0].startsWith('data:image/png;base64,'))).toBe(true);
  expect(errors).toEqual([]); expect(unexpected).toEqual([]);
});
