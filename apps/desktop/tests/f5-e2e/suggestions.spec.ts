import { test, expect } from '@playwright/test';

test('수정·겹침·테스트 승인·무시와 안전한 본문 표시', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('./');
  await expect(page.getByText('합성 데이터 검사 전용', { exact: false })).toBeVisible();
  const card = page.getByTestId('suggestion-calendar');
  await card.getByLabel('제목').fill('브라우저에서 수정한 합성 회의');
  await card.getByLabel('장소').fill('검사 회의실');
  await card.getByRole('button', { name: '겹치는 일정 확인' }).click();
  await expect(card.getByText('같은 시간에 1건의 일정이 있습니다.')).toBeVisible();
  await card.getByRole('button', { name: '캘린더에 추가' }).click();
  await expect(card.getByText('테스트 실행을 확인했어요. 실제 캘린더에는 등록하지 않았어요.')).toBeVisible();
  await expect(page.getByText('✓ 캘린더에 추가했어요')).toHaveCount(0);
  await page.getByTestId('suggestion-todo').getByRole('button', { name: '무시' }).click();
  await expect(page.getByTestId('suggestion-todo').getByText('무시함')).toBeVisible();
  await expect(page.getByRole('button', { name: '회신 초안 만들기' })).toBeDisabled();
  await expect(page.getByTestId('mail-evidence').locator('script')).toHaveCount(0);
  await page.screenshot({ path: 'artifacts/f5/s04-desktop.png', fullPage: true });
  expect(errors).toEqual([]);
});

test('실패 후 재시도와 1280px 본문 위 패널', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto('./');
  await page.getByLabel('등록 실패 검사').check();
  const card = page.getByTestId('suggestion-calendar');
  await card.getByRole('button', { name: '캘린더에 추가' }).click();
  await expect(card.getByRole('alert')).toBeVisible();
  await expect(page.getByText('✓ 캘린더에 추가했어요')).toHaveCount(0);
  await page.getByLabel('등록 실패 검사').uncheck();
  await card.getByRole('button', { name: '캘린더에 추가' }).click();
  await expect(card.getByText('테스트 실행을 확인했어요. 실제 캘린더에는 등록하지 않았어요.')).toBeVisible();
  const panel = await page.getByRole('complementary', { name: 'AI 제안' }).boundingBox();
  const body = await page.getByRole('region', { name: '메일 본문' }).boundingBox();
  expect(panel && body && panel.y < body.y).toBeTruthy();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: 'artifacts/f5/s04-compact.png', fullPage: true });
});
