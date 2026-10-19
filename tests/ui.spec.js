import { test, expect } from '@playwright/test';

test('desktop dashboard, dictionary, theme, search, practice, resume and mobile', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Bonjour，继续向前。' })).toBeVisible();
  await expect(page.locator('.metric-card')).toHaveCount(4);
  await page.screenshot({ path: 'preview-desktop.png', fullPage: true });

  await page.getByRole('button', { name: '动词词典', exact: true }).click();
  await page.getByRole('textbox', { name: '搜索法语动词' }).fill('etre');
  await page.locator('.verb-list').getByRole('button', { name: 'être', exact: true }).click();
  await expect(page.locator('.verb-detail-header h2')).toHaveText('être');
  await expect(page.locator('.tense-table-card')).toHaveCount(3);
  await expect(page.locator('.verb-detail').getByText('suis', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: '切换浅色或深色外观' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.getByRole('button', { name: '学习总览', exact: true }).click();
  await page.screenshot({ path: 'preview-dark.png', fullPage: true });
  await page.getByRole('button', { name: '切换浅色或深色外观' }).click();

  await page.keyboard.press('Control+k');
  await expect(page.getByRole('dialog', { name: '快速前往' })).toBeVisible();
  await page.getByRole('textbox', { name: '快速搜索' }).fill('avoir');
  await page.locator('.command-results').getByText('avoir', { exact: true }).click();
  await expect(page.locator('.verb-detail-header h2')).toHaveText('avoir');

  await page.getByRole('button', { name: '偏好设置', exact: true }).click();
  const fuzzy = page.getByRole('switch', { name: '模糊匹配', exact: true });
  const initial = await fuzzy.getAttribute('aria-checked');
  await fuzzy.click();
  await expect(fuzzy).toHaveAttribute('aria-checked', initial === 'true' ? 'false' : 'true');
  await page.reload();
  await expect(page.getByRole('switch', { name: '模糊匹配', exact: true })).toHaveAttribute('aria-checked', initial === 'true' ? 'false' : 'true');

  await page.getByRole('button', { name: '开始学习', exact: true }).click();
  await page.getByLabel('动词数量').fill('1');
  await page.getByRole('button', { name: '开始这一组' }).click();
  await expect(page.locator('.conjugation-grid')).toBeVisible();
  const verb = await page.locator('.practice-question h1').innerText();
  await page.getByRole('button', { name: '还不熟悉', exact: true }).click();
  await expect(page.locator('.quiz-options')).toBeVisible();
  await page.locator('.quiz-option').first().click();
  await page.getByRole('button', { name: '确认答案', exact: true }).click();
  await expect(page.locator('.answer-feedback')).toBeVisible();
  await page.getByRole('button', { name: '继续下一题', exact: true }).click();
  await page.getByRole('button', { name: '保存并离开' }).click();
  await page.getByRole('button', { name: '学习总览', exact: true }).click();
  await page.reload();
  await page.getByRole('button', { name: '继续上次练习' }).click();
  await expect(page.locator('.practice-card')).toBeVisible();
  await page.getByRole('button', { name: '保存并离开' }).click();
  await page.getByRole('button', { name: '学习总览', exact: true }).click();

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('heading', { name: 'Bonjour，继续向前。' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: 'preview-mobile.png', fullPage: true });
  await page.getByRole('button', { name: '打开导航', exact: true }).click();
  await page.getByRole('button', { name: '动词词典', exact: true }).click();
  await expect(page.locator('.verb-detail')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
