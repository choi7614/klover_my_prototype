import { useEffect, useState, type ReactNode } from 'react';
import { SuggestionReader } from './suggestion-reader';
import type { F5Client, Suggestion } from './types';

/**
 * S04 진입: 메일 읽기 영역에서 해당 메일의 제안을 불러와 SuggestionReader로 보여 준다.
 * 제안이 없거나 불러오는 중이면 기존 S03 모양(fallback)을 그대로 쓴다.
 * 승인 전에는 아무것도 실행하지 않는다. 캘린더·답장 초안 실행은 아직 연결하지 않았다.
 */
export function MailSuggestions({ mailId, body, client, header, fallback }: {
  mailId: string; body: string; client: F5Client; header?: ReactNode; fallback: ReactNode;
}) {
  const [rows, setRows] = useState<Suggestion[] | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    setRows(null);
    setFailed(false);
    client.list({ mail_id: mailId, limit: 50 }).then(page => {
      if (!active) return;
      setRows(Array.isArray(page.items) ? page.items.filter(row => row.mail_id === mailId) : []);
    }, () => { if (active) { setRows([]); setFailed(true); } });
    return () => { active = false; };
  }, [client, mailId]);

  if (!rows || rows.length === 0) {
    return <>
      {failed && <p role="status" className="px-7 pt-3 text-caption text-muted-foreground">AI 제안을 불러오지 못했어요. 메일 본문은 그대로 볼 수 있어요.</p>}
      {fallback}
    </>;
  }
  return <SuggestionReader mailId={mailId} body={body} suggestions={rows} client={client} header={header}
    onChange={row => setRows(current => (current ?? []).map(item => item.suggestion_id === row.suggestion_id ? row : item))} />;
}
