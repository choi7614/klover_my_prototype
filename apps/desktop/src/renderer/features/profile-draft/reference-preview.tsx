import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from './controls';
import { problemText, type F2Client, type MailDetail } from './contracts';

export function ReferencePreview({ client, mailId, onClose }: { client: F2Client; mailId: string; onClose(): void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [mail, setMail] = useState<MailDetail | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    if (dialog.current) {
      if (typeof dialog.current.showModal === 'function') dialog.current.showModal();
      else dialog.current.open = true;
    }
    client.mail(mailId).then(value => { if (active) setMail(value); })
      .catch(error => { if (active) setError(problemText(error)); });
    return () => { active = false; };
  }, [client, mailId]);

  return <dialog ref={dialog} aria-label="참고 메일 미리보기" onCancel={onClose} className="fixed inset-0 m-auto w-[560px] max-w-full rounded-lg border bg-background p-6 text-foreground shadow-pop">
    <div className="mb-4 flex items-center gap-3"><h2 className="flex-1 text-title font-semibold">참고 메일 미리보기</h2><Button variant="secondary" onClick={onClose}>닫기</Button></div>
    {error ? <p role="alert" className="text-body">{error}</p> : mail ? <>
      <h3 className="text-title font-semibold">{mail.subject}</h3>
      <p className="mt-1 text-caption text-muted-foreground">{mail.from_name || mail.from_addr} · {new Date(mail.received_at).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })}</p>
      <p className="mt-4 max-h-80 overflow-y-auto whitespace-pre-wrap text-body">{mail.body_text}</p>
    </> : <Skeleton label="참고 메일을 불러오고 있어요" />}
  </dialog>;
}
