import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { _electron } from 'playwright';
import { expect } from '@playwright/test';

const require = createRequire(import.meta.url);
const desktop = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const root = resolve(desktop, '../..');
const temporary = await mkdtemp(resolve(tmpdir(), 'klover-mail-integration-'));
const token = 'S'.repeat(43);
const tokenFile = resolve(temporary, 'mail-api-token');
await writeFile(tokenFile, token + '\n', { mode: 0o600 });
const reservation = createServer();
await new Promise(resolve => reservation.listen(0, '127.0.0.1', resolve));
const port = reservation.address().port;
await new Promise(resolve => reservation.close(resolve));
const base = `http://127.0.0.1:${port}`;
const server = spawn('uv', ['run', '--locked', '--directory', resolve(root, 'apps/server'), 'python', resolve(desktop, 'tests/mail-api-fixture.py'), '--port', String(port), '--token-file', tokenFile], {
  cwd: root, env: { ...process.env, PYTHONPATH: resolve(root, 'apps/server') }, stdio: 'ignore',
});
let application;
try {
  await expect.poll(async () => {
    try { return (await fetch(base + '/health', { signal: AbortSignal.timeout(500) })).status; }
    catch { return 0; }
  }, { timeout: 30000 }).toBe(200);
  const environment = { ...process.env, KLOVER_API_BASE_URL: base, KLOVER_API_TOKEN_FILE: tokenFile,
    XDG_CONFIG_HOME: resolve(temporary, 'config'), XDG_CACHE_HOME: resolve(temporary, 'cache') };
  delete environment.ELECTRON_RUN_AS_NODE;
  application = await _electron.launch({ executablePath: require('electron'), args: [resolve(desktop, 'out/main/index.js')], cwd: desktop, env: environment });
  const page = await application.firstWindow();
  await expect(page.getByText('demo@example.invalid', { exact: true })).toBeVisible();
  const errors = [];
  const external = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => { if (request.url().startsWith('http')) external.push(request.url()); });
  await page.getByRole('button', { name: /합성 메일 1/ }).click();
  await expect(page.getByTestId('mail-text-body')).toContainText('합성 본문 mail-1');
  assert.equal(await page.getByTestId('mail-text-body').locator('img,script,iframe').count(), 0);
  await expect(page.getByTestId('mail-text-body')).toContainText('<script>bad()</script>');
  await page.getByRole('button', { name: '다음 페이지' }).click();
  await page.getByRole('button', { name: /합성 메일 2/ }).click();
  await expect(page.getByTestId('mail-text-body')).toContainText('합성 본문 mail-2');
  await expect(page.getByRole('button', { name: '다음 페이지' })).toHaveCount(0);
  const snapshot = await page.evaluate(() => ({ keys: Object.keys(window.klover), methods: Object.keys(window.klover.mail), node: typeof window.require, process: typeof window.process, dom: document.body.textContent }));
  assert.deepEqual(snapshot.keys, ['platform', 'mail']);
  assert.deepEqual(snapshot.methods, ['session', 'inbox', 'detail']);
  assert.equal(snapshot.node, 'undefined');
  assert.equal(snapshot.process, 'undefined');
  assert.equal(snapshot.dom.includes(token), false);
  assert.equal(snapshot.dom.includes(tokenFile), false);
  assert.deepEqual(external, []);
  assert.deepEqual(errors, []);
  const output = resolve(root, 'artifacts/F0-mailbox-electron.png');
  await mkdir(dirname(output), { recursive: true });
  await page.screenshot({ path: output });
  await page.getByRole('button', { name: '목록 새로고침' }).click();
  await expect(page.getByText('받은편지함이 비어 있습니다')).toBeVisible();
  assert.equal(await readFile(tokenFile, 'utf8'), token + '\n');
  await writeFile(tokenFile, 'T'.repeat(43) + '\n');
  await page.getByRole('button', { name: '목록 새로고침' }).click();
  await expect(page.getByRole('heading', { name: 'Gmail 계정 연결' })).toBeVisible();
  await expect(page.getByText('demo@example.invalid', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('alert')).toContainText('인증');
  console.log('통과: 실제 FastAPI 읽기 라우터 → Node fetch → typed IPC/preload → Electron 계정·목록·본문·페이지·빈 목록·인증 오류');
  console.log('합성 저장소 사용. 실제 Gmail·맥북 확인과 구분합니다.');
} finally {
  await application?.close();
  if (server.exitCode === null) {
    const closed = new Promise(resolve => server.once('exit', resolve));
    server.kill('SIGTERM');
    await closed;
  }
  await rm(temporary, { recursive: true, force: true });
}
