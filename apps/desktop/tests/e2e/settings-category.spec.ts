import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    let category = 'work_request';
    const mail = { mail_id: 'synthetic-mail', subject: '합성 자료 검토 요청', from_name: '합성 발신자', from_addr: 'sender@example.invalid', received_at: '2026-11-20T00:00:00Z', is_read: true, analysis_status: 'done', preview: '합성 자료를 확인해 주세요.' };
    const ok = (data: unknown) => Promise.resolve({ ok: true, data });
    Object.assign(window, { klover: { platform: 'test', mail: {
      session: () => ok({ user_id: 'synthetic', account_id: 'synthetic', email: 'owner@example.invalid', sync_started_at: '2026-11-20T00:00:00Z' }),
      inbox: () => ok({ items: [mail], next_cursor: null }),
      detail: () => ok({ ...mail, to: [], cc: [], body_text: '합성 자료를 확인해 주세요.' }),
    }, analysis: {
      batch: () => ok({ auto_analysis: 'ready', items: [{ mail_id: mail.mail_id, analysis_status: 'done', category, summary: '자료 검토를 요청했습니다.', needs_reply: true, action_items: [], priority: 'normal', priority_reason: '합성 이유', failure_code: null }] }),
      setCategory: (id: string, next: string) => { category = next; return ok({ mail_id: id, user_label: next, effective_category: next }); },
    } } });
  });
});
test('분류를 변경하면 목록과 본문에 반영되고 다시 열어도 유지된다', async ({ page }) => {
  await page.goto('/#/mail/inbox');
  await page.getByRole('button', { name: /합성 자료 검토 요청/ }).click();
  await page.getByRole('combobox', { name: '메일 분류' }).selectOption('notice');
  await expect(page.getByRole('status').filter({ hasText: '분류를 저장했어요' })).toBeVisible();
  await expect(page.getByRole('button', { name: /합성 자료 검토 요청/ })).toContainText('공지');
  await page.getByRole('link', { name: '설정', exact: true }).click();
  await expect(page.getByRole('heading', { name: '설정', exact: true })).toBeVisible();
  await page.getByRole('navigation', { name: '설정 메뉴' }).getByRole('link', { name: /받은편지함/ }).click();
  await page.getByRole('button', { name: /합성 자료 검토 요청/ }).click();
  await expect(page.getByRole('combobox', { name: '메일 분류' })).toHaveValue('notice');
});
test('설정은 작은 창에서도 모든 항목과 준비 중 안내를 보여준다', async ({ page }) => {
  await page.setViewportSize({ width: 900, height: 650 });
  await page.goto('/#/settings');
  await expect(page.getByRole('heading', { name: '설정', exact: true })).toBeVisible();
  for (const name of ['내 프로필·문체', 'AI 설정', '캘린더 연결', '과거 메일 가져오기', '개인정보·학습 데이터']) {
    await expect(page.getByRole('main').getByRole('link', { name: new RegExp(name) })).toBeVisible();
  }
  await expect(page.getByRole('heading', { name: '준비 중인 기능' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: 'artifacts/settings-category/settings-home.png', fullPage: true });
});
