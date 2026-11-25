import { open } from 'node:fs/promises';
import { constants } from 'node:fs';
import { isAbsolute } from 'node:path';
import { localRequest } from './local-api';
import {
  mailFailure, validInboxQuery, validMailId, validSyncResult,
  type InboxQuery, type MailDetail, type MailPage, type MailReadBridge,
  type MailResult, type MailSession, type MailSummary, type MailSyncResult,
} from '../shared/mail-read';

type Configuration = { baseURL?: string; tokenFile?: string };

export function localAPIURL(value = 'http://127.0.0.1:8000'): URL {
  const url = new URL(value);
  if (url.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname) ||
      url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('configuration');
  }
  return url;
}

// 반환 객체를 새로 구성해 예상하지 않은 서버 필드(토큰·HTML 등)를 IPC로 전달하지 않는다.
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('response');
  return value as Record<string, unknown>;
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('response');
  return value;
}
function date(value: unknown): string {
  const result = text(value);
  if (!Number.isFinite(Date.parse(result))) throw new Error('response');
  return result;
}
function summary(value: unknown): MailSummary {
  const row = record(value);
  if (!validMailId(row.mail_id) || typeof row.is_read !== 'boolean' ||
      !['pending', 'done', 'failed'].includes(String(row.analysis_status))) throw new Error('response');
  return {
    mail_id: row.mail_id, subject: text(row.subject), from_addr: text(row.from_addr),
    from_name: text(row.from_name), preview: text(row.preview), received_at: date(row.received_at),
    is_read: row.is_read, analysis_status: row.analysis_status as MailSummary['analysis_status'],
  };
}
function contacts(value: unknown): MailDetail['to'] {
  if (!Array.isArray(value)) throw new Error('response');
  return value.map(item => { const row = record(item); return { addr: text(row.addr), name: text(row.name) }; });
}

export type LocalAPIConfiguration = Configuration;

/** main 전용: 로컬 API 주소와 토큰 파일을 확인해 읽는다. F2·F3 통로도 같은 규칙을 쓴다. 실패하면 null. */
export async function readLocalAPI(configuration: Configuration): Promise<{ base: URL; token: string } | null> {
  try {
    const base = localAPIURL(configuration.baseURL);
    const file = configuration.tokenFile;
    if (!file || !isAbsolute(file)) return null;
    const handle = await open(file, constants.O_RDONLY | (constants.O_NOFOLLOW ?? 0));
    let token: string;
    try {
      const stat = await handle.stat();
      if (!stat.isFile() || stat.size > 256 || (process.platform !== 'win32' && (stat.mode & 0o077) !== 0)) return null;
      token = (await handle.readFile('utf8')).trim();
    } finally { await handle.close(); }
    return /^[A-Za-z0-9_-]{43}$/.test(token) ? { base, token } : null;
  } catch { return null; }
}

export class MailAPIClient implements MailReadBridge {
  constructor(private readonly configuration: Configuration, private readonly fetcher: typeof fetch = fetch) {}

  // 새 메일 가져오기는 Gmail 수신을 기다리므로 조회보다 길게 기다린다.
  private async request<T>(path: string, parse: (value: unknown) => T, method: 'GET' | 'POST' = 'GET', timeout = 10000): Promise<MailResult<T>> {
    const local = await readLocalAPI(this.configuration);
    if (!local) return mailFailure('configuration');

    try {
      const { url, init } = localRequest(local, { method, path, timeoutMs: timeout });
      const response = await this.fetcher(url, init);
      if (!response.ok) {
        switch (response.status) {
          case 401: return mailFailure('unauthorized');
          case 403: return mailFailure('forbidden');
          case 404: return mailFailure('not_found');
          case 409: return mailFailure('sync_in_progress');
          case 502: return mailFailure('gmail_unavailable');
          case 422: return mailFailure('invalid_request');
          default: return mailFailure('unavailable');
        }
      }
      try { return { ok: true, data: parse(await response.json()) }; }
      catch { return mailFailure('invalid_response'); }
    } catch { return mailFailure('connection'); }
  }

  session(): Promise<MailResult<MailSession>> {
    return this.request('/auth/session', value => {
      const row = record(value);
      return { user_id: text(row.user_id), account_id: text(row.account_id), email: text(row.email), sync_started_at: date(row.sync_started_at) };
    });
  }

  inbox(query?: InboxQuery): Promise<MailResult<MailPage>> {
    if (!validInboxQuery(query)) return Promise.resolve(mailFailure('invalid_request'));
    const parameters = new URLSearchParams({ box: 'inbox', limit: String(query?.limit ?? 20) });
    if (query?.cursor) parameters.set('cursor', query.cursor);
    return this.request(`/mails?${parameters}`, value => {
      const page = record(value);
      if (!Array.isArray(page.items) || page.items.length > (query?.limit ?? 20) ||
          !(page.next_cursor === null || (typeof page.next_cursor === 'string' && page.next_cursor.length > 0 && page.next_cursor.length <= 1024)) ||
          (query?.cursor && page.next_cursor === query.cursor)) throw new Error('response');
      return { items: page.items.map(summary), next_cursor: page.next_cursor as string | null };
    });
  }

  sync(): Promise<MailResult<MailSyncResult>> {
    return this.request('/mails/sync', value => {
      if (!validSyncResult(value)) throw new Error('response');
      return { saved: value.saved, skipped: value.skipped, mode: value.mode, token_refreshed: value.token_refreshed };
    }, 'POST', 120000);
  }

  detail(mailId: string): Promise<MailResult<MailDetail>> {
    if (!validMailId(mailId)) return Promise.resolve(mailFailure('invalid_request'));
    return this.request(`/mails/${encodeURIComponent(mailId)}`, value => {
      const row = record(value);
      const mail = summary(row);
      if (mail.mail_id !== mailId) throw new Error('response');
      return { ...mail, to: contacts(row.to), cc: contacts(row.cc), body_text: text(row.body_text) };
    });
  }
}
