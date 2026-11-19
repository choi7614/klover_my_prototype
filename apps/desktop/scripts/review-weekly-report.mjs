import { mkdtemp, writeFile } from 'node:fs/promises';
import { randomBytes } from 'node:crypto';
import { tmpdir } from 'node:os';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';

const desktop = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const repository = resolve(desktop, '../..');
const reviewDirectory = await mkdtemp(join(tmpdir(), 'klover-f4-review-'));
const tokenFile = join(reviewDirectory, 'synthetic-token');
await writeFile(tokenFile, randomBytes(32).toString('base64url'), { mode: 0o600, flag: 'wx' });
const python = resolve(repository, 'apps/server/.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const api = spawn(python, ['-m', 'app.cli.review_weekly_report', '--fixture', resolve(repository, 'fixtures/mails/F4-weekly-report.json'),
  '--database', join(reviewDirectory, 'synthetic-reports.db'), '--token-file', tokenFile, '--test-double'],
{ cwd: resolve(repository, 'apps/server'), stdio: ['ignore', 'inherit', 'inherit'] });
const vite = spawn(process.execPath, [resolve(desktop, 'node_modules/vite/bin/vite.js'), '--config', 'vite.weekly-report.config.ts'],
  { cwd: desktop, stdio: ['ignore', 'inherit', 'inherit'], env: { ...process.env, F4_REVIEW_TOKEN_FILE: tokenFile } });

let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  api.kill('SIGTERM'); vite.kill('SIGTERM');
  process.exitCode = code;
}
for (const child of [api, vite]) {
  child.on('error', () => stop(1));
  child.on('exit', (code) => { if (!stopping) stop(code || 1); });
}
process.on('SIGINT', () => stop());
process.on('SIGTERM', () => stop());
console.log('F4 테스트 대역 검토: http://127.0.0.1:5174/features/weekly-report/preview/');
console.log('가짜 메일만 사용하며 실제 계정·키·메일·AI에는 접근하지 않습니다.');
