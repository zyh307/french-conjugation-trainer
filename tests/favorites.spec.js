import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { offlineApp } from './offline-assets.mjs';
const wordlists = JSON.parse(readFileSync(new URL('../src/generated/wordlists.json', import.meta.url), 'utf8'));
const label = p => ({ il: 'il / elle', ils: 'ils / elles' }[p] || p);
test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
test('favorite list, single practice, batch practice, completion records and persistence', async ({ page, context }) => {
  const { errors, unexpected } = await offlineApp(page, context);
  await page.getByRole('button', { name: '底部导航：词典' }).click();
  await page.getByRole('button', { name: '收藏 être 现在时', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: '确认', exact: true }).click();
  await expect(page.getByRole('button', { name: '收藏 être 现在时', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: '收藏 être 复合过去时', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: '确认', exact: true }).click();
  await page.getByRole('button', { name: '收藏', exact: true }).click();
  await expect(page.locator('.favorite-row')).toHaveCount(2);
  await expect(page.getByTestId('favorite-history-être-现在时')).toHaveText('尚未完成练习');
  async function finish(expected) {
    for (let count = 0; count < expected; count++) {
      await expect(page.locator('.practice-card')).toBeVisible();
      const q = await page.evaluate(() => JSON.parse(localStorage.getItem('conjugaison.device.v1')).active.question);
      const forms = wordlists[q.level][q.temps][q.verbe];
      expect(q.round).not.toBe('judge');
      if (q.round === 'reverse') await page.locator('.quiz-options').getByText(label(q.personne), { exact: true }).click();
      else if (q.round === 'choice') await page.locator('.quiz-options').getByText(forms[q.personne], { exact: true }).click();
      else await page.getByLabel('输入正确变位', { exact: true }).fill(forms[q.personne]);
      await page.getByRole('button', { name: '确认答案', exact: true }).click();
      await expect(page.locator('.answer-feedback')).toHaveClass(/correct/);
      await page.getByRole('button', { name: '继续下一题', exact: true }).click();
    }
    await expect(page.locator('.completion-card')).toBeVisible();
    await page.getByRole('button', { name: '回到学习空间' }).click();
    await page.getByRole('button', { name: '收藏', exact: true }).click();
  }
  await page.getByRole('button', { name: '练习收藏 être 现在时', exact: true }).click();
  await finish(18);
  await expect(page.getByTestId('favorite-history-être-现在时')).toContainText('已完成 1 次');
  await expect(page.getByTestId('favorite-history-être-复合过去时')).toHaveText('尚未完成练习');
  await page.getByRole('button', { name: '一键练习全部收藏', exact: true }).click();
  await finish(36);
  await expect(page.getByTestId('favorite-history-être-现在时')).toContainText('已完成 2 次');
  await expect(page.getByTestId('favorite-history-être-复合过去时')).toContainText('已完成 1 次');
  await page.reload();
  await page.getByRole('button', { name: '收藏', exact: true }).click();
  await expect(page.getByTestId('favorite-history-être-现在时')).toContainText('已完成 2 次');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'preview-favorites-mobile.png', fullPage: true });
  await page.getByRole('button', { name: '移除收藏 être 复合过去时', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: '确认移除', exact: true }).click();
  await expect(page.locator('.favorite-row')).toHaveCount(1);
  expect(errors).toEqual([]); expect(unexpected).toEqual([]);
});
