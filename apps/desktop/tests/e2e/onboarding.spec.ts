import { expect, test } from '@playwright/test';

test('첫 실행 화면에서 연결을 건너뛰지 못하고 새로 열어도 첫 단계가 유지된다', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');

  await expect(page).toHaveURL(/#\/onboarding\/1$/);
  await expect(page.getByRole('heading', { name: 'Gmail 계정 연결' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: '첫 실행 설정 단계' }).getByRole('listitem')).toHaveCount(5);
  await expect(page.getByRole('button', { name: '다음' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Google 계정으로 연결' })).toBeDisabled();

  await page.goto('/#/mail/inbox');
  await expect(page).toHaveURL(/#\/onboarding\/1$/);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Gmail 계정 연결' })).toBeVisible();
  expect(errors).toEqual([]);
});

test('설정 창 크기에서 글꼴·레이아웃·비활성 버튼이 올바르게 표시된다', async ({ page }) => {
  await page.goto('/');
  await page.evaluate(() => document.fonts.ready);

  const layout = await page.evaluate(() => ({
    horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth,
    verticalOverflow: document.documentElement.scrollHeight > window.innerHeight,
    sidebarWidth: document.querySelector('aside')?.getBoundingClientRect().width,
    font: getComputedStyle(document.body).fontFamily,
  }));
  expect(layout.horizontalOverflow).toBe(false);
  expect(layout.verticalOverflow).toBe(false);
  expect(layout.sidebarWidth).toBe(280);
  expect(layout.font).toContain('Pretendard');
  await expect(page.getByRole('button', { name: '다음' })).toHaveCSS('opacity', '0.4');
  await expect(page.locator('[aria-current="step"]')).toHaveCount(1);
  await page.screenshot({ path: '../../artifacts/F0-onboarding-browser.png' });
});
