import assert from 'node:assert/strict';
import { mkdir, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { _electron } from 'playwright';

const require = createRequire(import.meta.url);
const desktopDirectory = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const temporaryDirectory = await mkdtemp(resolve(tmpdir(), 'klover-electron-'));
const environment = {
  ...process.env,
  XDG_CONFIG_HOME: resolve(temporaryDirectory, 'config'),
  XDG_CACHE_HOME: resolve(temporaryDirectory, 'cache'),
};
delete environment.ELECTRON_RUN_AS_NODE;

let application;
try {
  application = await _electron.launch({
    executablePath: require('electron'),
    args: [resolve(desktopDirectory, 'out/main/index.js')],
    cwd: desktopDirectory,
    env: environment,
  });
  const page = await application.firstWindow();
  await page.getByRole('heading', { name: 'Gmail 계정 연결' }).waitFor();
  assert.equal(await page.getByRole('button', { name: '다음' }).isDisabled(), true);
  assert.equal(await page.getByRole('button', { name: 'Google 계정으로 연결' }).isDisabled(), true);

  const windowState = await application.evaluate(({ BrowserWindow }) => {
    const window = BrowserWindow.getAllWindows()[0];
    const preferences = window.webContents.getLastWebPreferences();
    return {
      bounds: window.getBounds(),
      resizable: window.isResizable(),
      maximizable: window.isMaximizable(),
      contextIsolation: preferences.contextIsolation,
      nodeIntegration: preferences.nodeIntegration,
      sandbox: preferences.sandbox,
    };
  });
  assert.equal(windowState.bounds.width, 1040);
  assert.equal(windowState.bounds.height, 680);
  assert.equal(windowState.resizable, false);
  // Electron의 isMaximizable/maximizable은 macOS·Windows에서만 지원한다.
  if (process.platform !== 'linux') assert.equal(windowState.maximizable, false);
  assert.equal(windowState.contextIsolation, true);
  assert.equal(windowState.nodeIntegration, false);
  assert.equal(windowState.sandbox, true);
  assert.deepEqual(await page.evaluate(() => ({
    nodeAccess: typeof window.require,
    platform: window.klover?.platform,
    exposedKeys: Object.keys(window.klover || {}),
  })), { nodeAccess: 'undefined', platform: process.platform, exposedKeys: ['platform'] });

  const screenshotPath = resolve(desktopDirectory, '../../artifacts/F0-onboarding-electron.png');
  await mkdir(dirname(screenshotPath), { recursive: true });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: screenshotPath });

  // 첫 실행 설정 중에는 창을 닫으면 트레이에 남지 않고 프로세스가 종료되어야 한다.
  const closed = application.waitForEvent('close');
  await application.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].close());
  await closed;
  application = undefined;
  console.log('통과: 실제 Electron 창, 1040×680 크기, 진행 제한, 화면 격리, 창 닫기 종료');
  if (process.platform === 'linux') console.log('미확인: Windows 최대화 제한·트레이·자동 실행');
  console.log(`화면 캡처: ${screenshotPath}`);
} finally {
  await application?.close();
  await rm(temporaryDirectory, { recursive: true, force: true });
}
