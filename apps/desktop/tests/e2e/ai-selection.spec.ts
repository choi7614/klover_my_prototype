import { expect, test } from '@playwright/test';

// 화면 통합만 검사한다. 실제 계정·메일·키·외부 AI는 사용하지 않는다.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    let state = { defaults: { draft: 'ollama', search: 'ollama', weekly_report: 'ollama' }, external_consent: false, claude_key_set: false, local_configured: true, claude_model: 'synthetic-model' };
    const calls: unknown[] = [];
    const profile = { name: '합성 사용자', title: '', org: '검사팀', greeting: '', closing: '', signature: '', formality: 70, reply_length: 'normal', report_sections: ['highlights'], report_recipient: '합성 팀장', report_style: 'bullet', excluded_phrases: [] };
    const mail = { mail_id: 'synthetic', subject: '합성 자료 요청', from_name: '합성 발신자', from_addr: 'sender@example.invalid', body_text: '합성 자료를 검토해 주세요.', received_at: '2026-11-20T00:00:00Z', analysis_status: 'done' };
    const ok = (data: unknown) => Promise.resolve({ ok: true, data });
    Object.assign(window, { testCalls: calls, klover: {
      platform: 'test',
      mail: { session: () => ok({ user_id: 'synthetic', account_id: 'synthetic', email: 'synthetic@example.invalid', sync_started_at: '2026-11-20T00:00:00Z' }) },
      ai: {
        get: () => ok(state),
        save: (r: { defaults: typeof state.defaults; external_consent: boolean; api_key?: string }) => { state = { ...state, defaults: r.defaults, external_consent: r.external_consent, claude_key_set: !!r.api_key || state.claude_key_set }; return ok(state); },
        check: (provider: string) => ok({ status: 'reachable', provider }),
      },
      f2: {
        profile: () => ok({ profile, exists: true, version: 1 }), mail: () => ok(mail),
        createDraft: (request: unknown) => { calls.push(request); return ok({ draft_id: 'synthetic-draft', mail_id: 'synthetic', body: '요청을 확인했습니다. 검토하겠습니다.', directions: ['검토 후 회신', '추가 문의'], selected_direction: '검토 후 회신', evidence: [], references: [], version: 1, profile_version: 1 }); },
      },
      weeklyReport: {
        options: () => ok({ default_period: { start: '2026-11-20', end: '2026-11-20' }, profile, remaining_days: 0, available_on: '2026-11-20', generation: 'ai' }),
        generate: (request: unknown) => { calls.push(request); return ok({ report_id: 'synthetic-report', revision: 1, period: { start: '2026-11-20', end: '2026-11-20' }, title: '합성 첫 주 보고', subtitle: '합성 사용자', recipient: '합성 팀장', style: 'bullet', sections: [{ name: 'highlights', items: [] }], scope: { total: 0, grouped: 0, groups: 0, excluded: 0 }, evidence_mails: [], status: 'empty', generation: 'none', partial_period: true, created_at: '2026-11-20T00:00:00Z', updated_at: '2026-11-20T00:00:00Z' }); },
      },
    } });
  });
});

test('AI 설정에서 기본값·전송 허용·키 입력과 연결 검사를 제공한다', async ({ page }) => {
  await page.goto('/#/settings/ai');
  await page.getByLabel('답장 초안·수정').selectOption('claude');
  await page.getByLabel('Claude API 키 등록·교체').fill('synthetic-key-never-real');
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: '설정 저장' }).click();
  await expect(page.getByLabel('Claude API 키 등록·교체')).toHaveValue('');
  await page.getByRole('button', { name: 'Claude 연결 검사' }).click();
  await expect(page.getByRole('status')).toHaveText('Claude 연결 확인 완료');
  await page.screenshot({ path: 'artifacts/ai-selection/settings.png', fullPage: true });
});

test('답장은 선택 후 생성하며 빈 인사·마무리 프로필로도 화면을 표시한다', async ({ page }) => {
  await page.goto('/#/reply/synthetic');
  await expect(page.getByRole('button', { name: '초안 만들기' })).toBeEnabled();
  expect(await page.evaluate(() => (window as unknown as { testCalls: unknown[] }).testCalls)).toEqual([]);
  await page.getByLabel('이번 요청의 AI').selectOption('claude');
  await page.getByRole('button', { name: '초안 만들기' }).click();
  await expect(page.getByLabel('답장 본문')).toHaveValue('요청을 확인했습니다. 검토하겠습니다.');
  expect(await page.evaluate(() => (window as unknown as { testCalls: unknown[] }).testCalls)).toEqual([{ mail_id: 'synthetic', ai_provider: 'claude' }]);
  await page.screenshot({ path: 'artifacts/ai-selection/draft.png', fullPage: true });
});

test('첫날 보고서는 대기 없이 선택 AI로 요청하고 실제 기간을 표시한다', async ({ page }) => {
  await page.goto('/#/report/weekly');
  await expect(page.getByRole('button', { name: '보고서 열기' })).toBeEnabled();
  expect(await page.evaluate(() => (window as unknown as { testCalls: unknown[] }).testCalls)).toEqual([]);
  await page.getByLabel('이번 요청의 AI').selectOption('claude');
  await page.getByRole('button', { name: '보고서 열기' }).click();
  await expect(page.getByText('합성 첫 주 보고', { exact: true })).toBeVisible();
  await expect(page.getByText(/일부 기간 자료 ·/)).toContainText('2026-11-20');
  expect(await page.evaluate(() => (window as unknown as { testCalls: { ai_provider: string }[] }).testCalls[0].ai_provider)).toBe('claude');
  await page.screenshot({ path: 'artifacts/ai-selection/weekly.png', fullPage: true });
});
