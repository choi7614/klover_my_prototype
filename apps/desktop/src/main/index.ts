import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { app, BrowserWindow, Menu, session } from 'electron';

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

  if (!app.isPackaged && process.env.ELECTRON_RENDERER_URL) {
    void window.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    void window.loadFile(join(currentDirectory, '../renderer/index.html'));
  }
}

app.setAppUserModelId('com.koscom.klover');

void app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
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
