import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { offlineApp } from './offline-assets.mjs';

const words = JSON.parse(readFileSync(new URL('../src/generated/wordlists.json', import.meta.url), 'utf8'));
async function browse(page, mobile) {
  if (mobile) await page.getByRole('button', { name: '底部导航：学习' }).click();
  else await page.locator('.sidebar').getByRole('button', { name: '练习本', exact: true }).click();
  await page.locator('.level-option').filter({ hasText: '生僻' }).click();
  await page.locator('.tense-option').filter({ hasText: '未完成过去时' }).click();
  await page.getByLabel('动词数量').fill('6');
  await page.getByRole('button', { name: '查看词表', exact: true }).click();
  await expect(page.getByRole('heading', { name: '生僻 · 未完成过去时', exact: true })).toBeVisible();
  await expect(page.locator('.learning-wordlist-rows>button')).toHaveCount(Object.keys(words['生僻']['未完成过去时']).length);
  await expect(page.locator('.verb-detail')).toHaveCount(0);
  await page.getByLabel('搜索当前词表').fill('resoudre');
  await expect(page.locator('.learning-wordlist-rows>button')).toHaveCount(1);
  await expect(page.locator('.learning-wordlist-rows>button')).toHaveText('résoudre');
  await page.getByRole('button', { name: '查看 résoudre', exact: true }).click();
  await expect(page.locator('.verb-detail-header h2')).toHaveText('résoudre');
  await expect(page.locator('.verb-meaning')).toHaveText('解决；解答');
  await expect(page.locator('.tense-table-card')).toHaveCount(1);
  await expect(page.locator('.tense-table-card')).toContainText('未完成过去时');
  for (const form of Object.values(words['生僻']['未完成过去时']['résoudre'])) await expect(page.locator('.conjugation-grid')).toContainText(form);
  await page.getByRole('button', { name: '返回词表', exact: true }).click();
  await expect(page.getByLabel('搜索当前词表')).toHaveValue('resoudre');
  await page.getByRole('button', { name: '查看 résoudre', exact: true }).click();
  await page.getByRole('button', { name: '立即练习 résoudre 未完成过去时', exact: true }).click();
  await expect(page.locator('.practice-card-top')).toContainText('选择变位');
  await expect(page.locator('.practice-question h1')).toHaveText('résoudre');
  await expect(page.locator('.practice-question')).toContainText('未完成过去时');
  await page.getByRole('button', { name: '保存并离开', exact: true }).click();
  await expect(page.locator('.verb-detail-header h2')).toHaveText('résoudre');
  await page.getByRole('button', { name: '返回词表', exact: true }).click();
  await page.getByRole('button', { name: '返回学习设置', exact: true }).click();
  await expect(page.getByLabel('动词数量')).toHaveValue('6');
  await expect(page.locator('.level-option.selected')).toContainText('生僻');
  await expect(page.locator('.tense-option.selected')).toContainText('未完成过去时');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
}

test('learning wordlist on desktop opens scoped details and direct practice', async ({ page }) => {
  await page.goto('/');
  await browse(page, false);
});

test('offline mobile learning wordlist opens scoped details and direct practice', async ({ page, context }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const { errors, unexpected } = await offlineApp(page, context);
  await browse(page, true);
  await page.getByRole('button', { name: '查看词表', exact: true }).click();
  await page.screenshot({ path: 'preview-learning-wordlist-mobile.png', fullPage: true });
  expect(errors).toEqual([]); expect(unexpected).toEqual([]);
});
