import { expect, test } from '@playwright/test';

test('S07 합성 결과·근거·메일/초안 연결 계약과 기본 창 크기', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByText('F3 독립 검사 · 합성 데이터 · 앱 미통합')).toBeVisible();
  await expect(page.locator('label[for="f3-query"]')).toHaveCSS('position', 'absolute');
  await expect(page.getByRole('button', { name: '검색', exact: true })).toHaveCSS('height', '36px');
  await page.getByRole('textbox', { name: '검색 질문' }).press('Enter');
  await expect(page.getByRole('heading', { name: '조건에 맞는 메일 3건' })).toBeVisible();
  await page.getByRole('button', { name: '근거 2번 메일' }).click();
  await expect(page.getByRole('article', { name: '검색 결과 2' })).toBeFocused();
  await page.getByRole('button', { name: '출장비 예산 초과분 처리 문의' }).click();
  await expect(page.getByRole('status')).toContainText('메일 열기 계약: m2');
  await page.getByRole('article', { name: '검색 결과 1' }).getByRole('button', { name: '답장 초안' }).click();
  await expect(page.getByRole('status')).toContainText('초안 열기 계약: m1');
  for (const [width, height] of [[1440, 900], [1280, 720], [760, 900]]) {
    await page.setViewportSize({ width, height });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `artifacts/f3-search-${width}.png`, fullPage: true });
  }
  expect(errors).toEqual([]);
});

test('조건 삭제·필터 오류·빈 결과·해석 오류·답변 미연결', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: '검색', exact: true }).click();
  await page.getByRole('button', { name: '기간 조건 삭제' }).click();
  await expect(page.getByRole('button', { name: '기간 조건 삭제' })).toHaveCount(0);
  await page.getByLabel('시작일', { exact: true }).fill('2026-11-20');
  await page.getByLabel('종료일', { exact: true }).fill('2026-11-10');
  await page.getByRole('button', { name: '조건 적용' }).click();
  await expect(page.getByRole('alert')).toContainText('시작일과 종료일');
  const query = page.getByRole('textbox', { name: '검색 질문' });
  await query.fill('빈 결과'); await query.press('Enter');
  await expect(page.getByText('조건에 맞는 메일을 찾지 못했어요.')).toBeVisible();
  await page.screenshot({ path: 'artifacts/f3-search-empty.png', fullPage: true });
  await query.fill('해석 오류'); await query.press('Enter');
  await expect(page.getByRole('alert')).toContainText('질문을 이해하지 못했어요.');
  await query.fill('답변 오류'); await query.press('Enter');
  await expect(page.getByText('답변 기능이 아직 연결되지 않았어요.')).toBeVisible();
  await expect(page.getByRole('heading', { name: '조건에 맞는 메일 3건' })).toBeVisible();
});
