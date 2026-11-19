import { expect, test } from '@playwright/test';
import { resolve } from 'node:path';

const path = '/features/weekly-report/preview/';
test.beforeEach(async ({ request }) => {
  await expect.poll(async () => (await request.post('/__f4_review/reports/weekly', { data: {} })).status()).toBe(200);
  const current = await (await request.post('/__f4_review/reports/weekly', { data: {} })).json();
  const reset = await request.post('/__f4_review/reports/weekly', {
    data: { regenerate: true, expected_revision: current.revision },
  });
  expect(reset.status()).toBe(200);
});

test('근거·제외 목록·편집·복사·저장·새로고침 재조회를 함께 검증한다', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto(path);
  await expect(page.getByText('9건 (6개 업무)')).toBeVisible();
  await expect(page.getByText(/검토용 테스트 대역/)).toBeVisible();
  await page.screenshot({ path: resolve('../../artifacts/F4-weekly-report.png'), fullPage: true });
  await page.getByRole('button', { name: '항목 1-1 근거 3개' }).click();
  await page.getByRole('complementary').getByRole('button', { name: /^3분기 결산 자료 확인 요청/ }).click();
  await expect(page.getByRole('dialog', { name: '근거 메일 원문' })).toContainText('부서별 자료를 확인해 주세요.');
  await page.getByRole('button', { name: '닫기' }).click();
  await page.getByRole('button', { name: '제외된 메일 보기 ›' }).click();
  await expect(page.getByRole('dialog', { name: '제외된 메일' })).toContainText('3건');
  await page.getByRole('button', { name: '닫기' }).click();
  await page.getByLabel('항목 내용 1-1').fill('사용자가 확인한 결산 보고 문장');
  await page.getByRole('button', { name: '복사', exact: true }).click();
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toContain('사용자가 확인한 결산 보고 문장');
  await page.getByRole('button', { name: '변경 내용 저장' }).click();
  await expect(page.getByText('편집한 내용을 저장했습니다.')).toBeVisible();
  await page.reload();
  await expect(page.getByLabel('항목 내용 1-1')).toHaveValue('사용자가 확인한 결산 보고 문장');
});

test('재생성 전 확인·취소와 AI 실패 시 편집본 보존을 검증한다', async ({ page }) => {
  await page.goto(path);
  await page.getByLabel('항목 내용 1-1').fill('실패해도 남아 있어야 하는 편집본');
  await page.getByRole('button', { name: '다시 만들기' }).click();
  await expect(page.getByRole('dialog', { name: '다시 만들기 전 확인' })).toBeVisible();
  await page.getByRole('button', { name: '편집 계속하기' }).click();
  await expect(page.getByLabel('항목 내용 1-1')).toHaveValue('실패해도 남아 있어야 하는 편집본');
  await page.route('**/__f4_review/reports/weekly', async (route) => {
    if (route.request().postDataJSON()?.regenerate) {
      await route.fulfill({ status: 502, contentType: 'application/json', body: JSON.stringify({ error: { code: 'ai_failed' } }) });
    } else await route.continue();
  });
  await page.getByRole('button', { name: '다시 만들기' }).click();
  await page.getByRole('button', { name: '계속 진행' }).click();
  await expect(page.getByRole('alert')).toContainText('기존 내용은 보존됩니다.');
  await expect(page.getByLabel('항목 내용 1-1')).toHaveValue('실패해도 남아 있어야 하는 편집본');
  await page.screenshot({ path: resolve('../../artifacts/F4-preserved-edit.png'), fullPage: true });
});

test('새 항목에 근거가 있어야 저장할 수 있다', async ({ page }) => {
  await page.goto(path);
  await page.getByRole('button', { name: '항목 추가' }).first().click();
  await page.getByLabel('항목 내용 1-7').fill('근거를 직접 연결한 추가 업무');
  await expect(page.getByRole('button', { name: '변경 내용 저장' })).toBeDisabled();
  await page.getByText('근거 메일 변경').click();
  await page.getByRole('checkbox').first().check();
  await page.getByRole('button', { name: '변경 내용 저장' }).click();
  await expect(page.getByText('편집한 내용을 저장했습니다.')).toBeVisible();
  await page.reload();
  await expect(page.getByLabel('항목 내용 1-7')).toHaveValue('근거를 직접 연결한 추가 업무');
});

test('빈 기간과 1280 화면에서도 범위·제외 목록을 확인한다', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto(path);
  await expect(page.getByText('9건 (6개 업무)')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByLabel('시작일').fill('2026-09-21');
  await page.getByLabel('종료일').fill('2026-09-25');
  await page.getByRole('button', { name: '보고서 열기' }).click();
  await expect(page.getByText('이 기간에 주고받은 업무 메일이 없어요')).toBeVisible();
  await expect(page.getByText('0건 (0개 업무)')).toBeVisible();
  await page.getByRole('button', { name: '제외된 메일 보기 ›' }).click();
  await expect(page.getByRole('dialog', { name: '제외된 메일' })).toContainText('0건');
});
