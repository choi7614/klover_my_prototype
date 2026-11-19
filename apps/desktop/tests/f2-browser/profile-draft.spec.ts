import { expect, test } from '@playwright/test';

for (const viewport of [{ width: 1440, height: 900 }, { width: 1280, height: 720 }]) {
  test(`S09 저장·취소·본문 스크롤 ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('/');
    await expect(page.getByLabel('이름', { exact: true })).toHaveValue('홍길동');
    await expect(page.getByRole('button', { name: '저장', exact: true })).toBeInViewport();
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollHeight)).toBeLessThanOrEqual(viewport.height);
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width);
    if (viewport.height === 900) {
      const dimensions = await page.getByTestId('profile-scroll').evaluate(element => [element.scrollHeight, element.clientHeight]);
      expect(dimensions[0]).toBeLessThanOrEqual(dimensions[1] + 1);
    }
    await page.getByLabel('소속', { exact: true }).fill('취소할 변경');
    await page.getByRole('button', { name: '취소', exact: true }).click();
    await expect(page.getByLabel('소속', { exact: true })).toHaveValue('경영지원본부 재무팀');
    await page.getByLabel('첫 인사', { exact: true }).fill('안녕하세요 🌿, 저장된 새 인사입니다.');
    await page.getByLabel('이슈·요청사항 위로').click();
    await page.getByRole('button', { name: '저장', exact: true }).click();
    await expect(page.getByText('저장했어요. 다음 초안부터 반영돼요.')).toBeVisible();
    await expect(page.getByLabel('미리보기').getByText(/저장된 새 인사/)).toBeVisible();
    await page.screenshot({ path: `artifacts/f2/S09-${viewport.width}.png`, fullPage: true });
    await page.getByRole('button', { name: 'S06 초안' }).click();
    await expect(page.getByLabel('답장 본문')).toHaveValue(/안녕하세요 🌿, 저장된 새 인사입니다/);
    expect(errors).toEqual([]);
  });

  test(`S06 편집·실패 보존·발송 없음 ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto('/#reply');
    const editor = page.getByLabel('답장 본문');
    await expect(editor).toHaveValue(/합성 검사/);
    await expect(page.getByRole('button', { name: '보내기', exact: true })).toBeDisabled();
    await expect(page.locator('[data-source="profile.greeting"]')).toContainText('안녕하세요 🌿');
    await page.screenshot({ path: `artifacts/f2/S06-${viewport.width}.png`, fullPage: true });
    const value = await editor.inputValue();
    await editor.fill(value.replace('안녕하세요', '반갑습니다'));
    await expect(page.locator('[data-source="profile.greeting"]')).toHaveCount(0);
    await expect(page.locator('[data-source="profile.signature"]')).toContainText('홍길동 과장');
    await page.getByLabel('합성 AI 실패').check();
    page.on('dialog', dialog => dialog.accept());
    await page.getByRole('button', { name: '다시 쓰기', exact: true }).click();
    await expect(page.getByRole('alert')).toContainText('AI 연결이 준비되지 않았어요');
    await expect(editor).toHaveValue(value.replace('안녕하세요', '반갑습니다'));
    await page.getByRole('button', { name: '임시 저장', exact: true }).click();
    await expect(page.getByRole('status')).toContainText('임시 저장했어요');
    await expect(page.getByRole('button', { name: '보내기', exact: true })).toBeDisabled();
    expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBeLessThanOrEqual(viewport.height);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width);
  });
}

test('AI 준비 부족 화면은 합성 결과도 성공으로 표시하지 않는다', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/?ai=unavailable#reply');
  await expect(page.getByRole('alert')).toContainText('AI 연결이 준비되지 않았어요');
  await expect(page.getByLabel('답장 본문')).toHaveValue('');
  await expect(page.getByRole('button', { name: '직접 쓰기', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: '보내기', exact: true })).toBeDisabled();
});

test('참고 메일을 미리 보고 Escape로 닫는다', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/?references=yes#reply');
  await page.getByRole('button', { name: '합성 참고 자료 메일' }).click();
  const dialog = page.getByRole('dialog', { name: '참고 메일 미리보기' });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText('3분기 예산 집행 현황 자료 요청드립니다');
  await page.keyboard.press('Escape');
  await expect(dialog).toHaveCount(0);
});

test('보고 양식 순서를 끌어서 바꾸고 키보드 버튼으로 되돌린다', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/');
  const list = page.getByRole('list');
  await expect(list).toBeVisible();
  await page.getByRole('listitem').filter({ hasText: '이슈·요청사항' }).dragTo(page.getByRole('listitem').filter({ hasText: '금주 주요 업무' }));
  await expect(page.getByRole('listitem').first()).toContainText('이슈·요청사항');
  await page.getByLabel('이슈·요청사항 아래로').click();
  await expect(page.getByRole('listitem').first()).toContainText('금주 주요 업무');
});
