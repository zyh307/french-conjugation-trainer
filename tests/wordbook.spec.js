import { test, expect } from '@playwright/test';
import { offlineApp } from './offline-assets.mjs';

test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
test('wordbook direct practice, learned filter, returning a word and editing word goals', async ({ page, context }) => {
  const { errors, unexpected } = await offlineApp(page, context);
  await page.getByRole('button', { name: '修改目标', exact: true }).click();
  await page.getByLabel('每日目标（个动词）').fill('2');
  await page.getByRole('button', { name: '保存', exact: true }).click();
  await expect(page.locator('.daily-card')).toContainText('每天 2 个动词');
  await page.getByRole('button', { name: '底部导航：词典' }).click();
  await expect(page.locator('.verb-meaning')).toHaveText('是；处于');
  await page.getByRole('button', { name: '立即练习 être 现在时', exact: true }).click();
  await expect(page.locator('.practice-card-top .soft-badge')).toHaveText('选择变位');
  const forms = { je: 'suis', tu: 'es', il: 'est', nous: 'sommes', vous: 'êtes', ils: 'sont' };
  const label = p => ({ il: 'il / elle', ils: 'ils / elles' }[p] || p);
  for (let i = 0; i < 18; i++) {
    await expect(page.locator('.practice-meaning')).toHaveText('是；处于');
    const stage = await page.locator('.practice-card-top .soft-badge').innerText();
    if (stage === '拼写练习') await expect(page.locator('.stem-hint')).toHaveText(/^答案长度：[1-9]\d* 个字母$/);
    expect(stage).toBe(i < 6 ? '选择变位' : i < 12 ? '反向选择' : '拼写练习');
    if (stage === '反向选择') {
      const form = await page.locator('.practice-question h1').innerText();
      const p = Object.keys(forms).find(p => forms[p] === form);
      await page.locator('.quiz-options').getByText(label(p), { exact: true }).click();
    } else {
      const p = (await page.locator('.person-badge').innerText()).split(' / ')[0];
      if (stage === '选择变位') await page.locator('.quiz-options').getByText(forms[p], { exact: true }).click();
      else await page.getByLabel('输入正确变位', { exact: true }).fill(forms[p]);
    }
    await page.getByRole('button', { name: '确认答案', exact: true }).click();
    await expect(page.locator('.answer-feedback')).toHaveClass(/correct/);
    await expect(page.locator('.practice-progress')).toContainText(`${i + 1} / 18 题`);
    await page.getByRole('button', { name: '继续下一题', exact: true }).click();
  }
  await expect(page.getByRole('heading', { name: '这一组，漂亮完成。' })).toBeVisible();
  await page.getByRole('button', { name: '回到学习空间' }).click();
  await page.getByRole('group', { name: '单词本分类' }).getByRole('button', { name: '复习本', exact: true }).click();
  await expect(page.locator('.verb-list')).toContainText('être');
  await expect(page.locator('.tense-table-card').first()).toContainText('已背 1 天');
  await expect(page.locator('.tense-table-card')).toHaveCount(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'preview-wordbook-mobile.png', fullPage: true });
  await page.getByRole('button', { name: '放回练习本 être 现在时', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: '确认转移', exact: true }).click();
  await expect(page.locator('.verb-list')).not.toContainText('être');
  await page.getByRole('button', { name: '底部导航：总览' }).click();
  await expect(page.locator('.daily-card')).toContainText('今日完成动词');
  await expect(page.locator('.daily-card .ring')).toContainText('1 / 2');
  await page.getByRole('button', { name: '底部导航：学习' }).click();
  await page.getByRole('button', { name: '开始这一组' }).click();
  await expect(page.locator('.practice-question h1')).toHaveText('être');
  await expect(page.locator('.practice-question .verb-meaning')).toHaveText('是；处于');
  const bounds = await page.getByRole('button', { name: '熟悉，加入已会', exact: true }).boundingBox();
  expect(bounds.y + bounds.height).toBeLessThan(790);
  expect(errors).toEqual([]); expect(unexpected).toEqual([]);
});
