import { fileURLToPath, pathToFileURL } from 'node:url';
import { join } from 'node:path';
import { app, BrowserWindow, Menu, session, ipcMain, screen } from 'electron';
import { MailAPIClient } from './mail-client';
import { developmentRendererURL, registerMailReadIPC } from './mail-ipc';
import { F2APIClient } from './f2-client';
import { F4APIClient } from './f4-client';
import { registerF4IPC } from './f4-ipc';
import { registerF2IPC } from './f2-ipc';
import { localSearchClientFactory, registerSearchIPC } from './search-ipc';

const currentDirectory = fileURLToPath(new URL('.', import.meta.url));

function createOnboardingWindow(): void {
  const window = new BrowserWindow({
    width: 1040,
    height: 680,
    resizable: false,
    maximizable: false,
    show: false,
    title: 'Klover — 시작하기',
    icon: join(currentDirectory, '../../resources/brand/app-icon-256.png'),
    webPreferences: {
      preload: join(currentDirectory, '../preload/index.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webviewTag: false,
    },
  });

  window.once('ready-to-show', () => window.show());
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', (event) => event.preventDefault());

  const rendererFile = join(currentDirectory, '../renderer/index.html');
  const developmentURL = !app.isPackaged ? developmentRendererURL(process.env.ELECTRON_RENDERER_URL) : undefined;
  const rendererURL = developmentURL ?? pathToFileURL(rendererFile).href;
  const configuration = { baseURL: process.env.KLOVER_API_BASE_URL, tokenFile: process.env.KLOVER_API_TOKEN_FILE };
  const client = new MailAPIClient(configuration);
  let mailboxWindow = false;
  const unregister = registerMailReadIPC(ipcMain, window.webContents, rendererURL, client, () => {
    if (mailboxWindow || window.isDestroyed()) return;
    mailboxWindow = true;
    window.setResizable(true);
    window.setMaximizable(true);
    const available = screen.getDisplayMatching(window.getBounds()).workAreaSize;
    window.setMinimumSize(Math.min(1280, available.width), Math.min(720, available.height));
    window.setSize(Math.min(1440, available.width), Math.min(900, available.height));
    window.center();
    window.setTitle('Klover');
  });
  // F2 프로필·답장 초안, F3 검색 통로. 메일 통로와 같은 신뢰 화면·토큰 규칙을 쓴다.
  const unregisterF2 = registerF2IPC(ipcMain, window.webContents, rendererURL, new F2APIClient(configuration));
  const unregisterSearch = registerSearchIPC(ipcMain, window.webContents, rendererURL, localSearchClientFactory(configuration));
  const unregisterF4 = registerF4IPC(ipcMain, window.webContents, rendererURL, new F4APIClient(configuration));
  window.once('closed', () => { unregister(); unregisterF2(); unregisterSearch(); unregisterF4(); });

  if (developmentURL) {
    void window.loadURL(developmentURL);
  } else {
    void window.loadFile(rendererFile);
  }
}

app.setAppUserModelId('com.koscom.klover');

void app.whenReady().then(() => {
  Menu.setApplicationMenu(process.platform === 'darwin'
    ? Menu.buildFromTemplate([{ role: 'appMenu' }, { role: 'editMenu' }, { role: 'windowMenu' }])
    : null);
  session.defaultSession.setPermissionRequestHandler((_contents, _permission, callback) => {
    callback(false);
  });
  session.defaultSession.setPermissionCheckHandler(() => false);
  createOnboardingWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createOnboardingWindow();
  });
});

// 첫 실행 설정 전에는 닫기 버튼으로 완전히 종료한다(S01).
app.on('window-all-closed', () => app.quit());
