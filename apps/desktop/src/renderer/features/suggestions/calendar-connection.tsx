import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import type { CalendarClient, CalendarConnection } from './types';

export function CalendarConnectionPanel({ client, onChange }: { client: CalendarClient; onChange?: (state: CalendarConnection) => void }) {
  const [state, setState] = useState<CalendarConnection>();
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);
  async function refresh(disconnect = false) {
    if (busy) return;
    setBusy(true); setError(false);
    try {
      const next = await (disconnect ? client.disconnectCalendar() : client.calendarStatus());
      setState(next); onChange?.(next);
    } catch { setError(true); onChange?.({ status: 'calendar_connection_failed', email: '', calendars: [] }); }
    finally { setBusy(false); }
  }
  useEffect(() => { let active = true;
    client.calendarStatus().then(next => { if (active) { setState(next); onChange?.(next); } }, () => { if (active) setError(true); });
    return () => { active = false; };
  }, [client, onChange]);
  const messages: Record<string, string> = {
    connected: '캘린더 연결됨', calendar_not_connected: '캘린더 추가 동의가 필요해요.',
    calendar_scope_required: '필요한 캘린더 권한이 부족해요.',
    calendar_permission_expired: '캘린더 권한이 만료됐어요. 추가 동의를 다시 확인해 주세요.',
    calendar_connection_failed: '캘린더 연결을 확인하지 못했어요.',
  };
  return <section aria-label="캘린더 연결" className="rounded-lg border border-border bg-background p-4 text-body">
    <h2 className="font-bold">Google Calendar 연결</h2>
    <p>{state?.email || '계정 확인 중…'}</p>
    <p role="status">{state ? messages[state.status] || '연결 상태를 확인해 주세요.' : '조회 중…'}</p>
    <p className="text-caption text-muted-foreground">같은 Google 계정으로 추가 권한을 허용한 뒤 연결 상태를 다시 확인해 주세요.</p>
    {client.connectCalendar && <Button variant="secondary" disabled={busy} onClick={() => {
      setBusy(true); setError(false);
      client.connectCalendar!().catch(() => setError(true)).finally(() => setBusy(false));
    }}>Google Calendar 추가 동의</Button>}
    {state?.calendars.map(x => <p key={x.id}>{x.label} · {x.id} · {x.timezone}</p>)}
    {error && <p role="alert">연결 확인에 실패했어요. 서버 상태를 확인해 주세요.</p>}
    <Button variant="secondary" disabled={busy} onClick={() => void refresh()}>연결 상태 다시 확인</Button>
    {state?.status === 'connected' && <Button variant="secondary" disabled={busy} onClick={() => void refresh(true)}>캘린더 연결 해제</Button>}
    <p className="text-caption text-muted-foreground">연결 해제는 이 앱의 Calendar 접근만 중지합니다. Gmail 연결과 이미 등록한 일정은 유지됩니다. Google 계정에 부여한 권한은 남아 있습니다.</p>
  </section>;
}
