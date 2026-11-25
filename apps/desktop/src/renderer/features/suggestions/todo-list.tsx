import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { ArrowLeft, SquareCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { F5Client, Todo, TodoStatus } from './types';

const inputClass = 'h-9 min-w-0 rounded-md border border-input bg-background px-2 text-body focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-40';
const weekdays = ['일', '월', '화', '수', '목', '금', '토'];

/** 마감 날짜(YYYY-MM-DD)를 "마감 MM/DD(요일)"로 보여 준다. */
export function dueLabel(due: string | null | undefined) {
  if (!due || !/^\d{4}-\d{2}-\d{2}$/.test(due)) return '마감 없음';
  const day = new Date(`${due}T00:00:00Z`);
  if (!Number.isFinite(day.getTime())) return '마감 없음';
  return `마감 ${due.slice(5, 7)}/${due.slice(8, 10)}(${weekdays[day.getUTCDay()]})`;
}

function message(error: unknown) {
  const code = error instanceof Error ? error.message : '';
  if (code === 'suggestions_unavailable') return '할 일 서버 연결을 준비 중이에요.';
  if (code === 'stale_version' || code === 'conflict') return '할 일이 바뀌었어요. 목록을 다시 불러왔어요.';
  return '할 일을 처리하지 못했어요. 연결 상태를 확인하고 다시 시도해 주세요.';
}

function newRequestId() {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `todo-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/** 사이드바 '할 일' 스마트 보기. 앱 안 할 일만 다루며 외부 서비스에는 등록하지 않는다. */
export function TodoListPage({ client, mailboxPath = '/mail/inbox' }: { client: F5Client; mailboxPath?: string }) {
  const [status, setStatus] = useState<TodoStatus>('open');
  const [items, setItems] = useState<Todo[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [due, setDue] = useState('');
  const [adding, setAdding] = useState(false);
  const sequence = useRef(0);

  const load = useCallback(async (next: string | null, append: boolean) => {
    const current = ++sequence.current;
    setLoading(true);
    setError('');
    try {
      const page = await client.todos({ status, limit: 50, ...(next ? { cursor: next } : {}) });
      if (current !== sequence.current) return;
      const rows = Array.isArray(page.items) ? page.items.filter(row => row.status === status) : [];
      setItems(previous => append ? [...previous, ...rows.filter(row => !previous.some(item => item.todo_id === row.todo_id))] : rows);
      setCursor(page.next_cursor && page.next_cursor !== next ? page.next_cursor : null);
    } catch (failure) {
      if (current === sequence.current) setError(message(failure));
    } finally {
      if (current === sequence.current) setLoading(false);
    }
  }, [client, status]);

  useEffect(() => { setItems([]); setCursor(null); setNotice(''); void load(null, false); }, [load]);

  async function toggle(todo: Todo) {
    if (busy) return;
    setBusy(todo.todo_id);
    setError('');
    setNotice('');
    try {
      const updated = await client.updateTodo(todo.todo_id, { version: todo.version, status: todo.status === 'open' ? 'completed' : 'open' });
      if (updated.todo_id !== todo.todo_id) throw new Error('invalid_response');
      // 목록에서 바로 사라지면 삭제된 것처럼 보이므로 그 자리에 남기고(줄긋기), 어디로 갔는지 알려 준다.
      setItems(previous => previous.map(item => item.todo_id === todo.todo_id ? updated : item));
      setNotice(updated.status === 'completed'
        ? `‘${updated.title}’을(를) 완료로 표시했어요. 삭제된 것이 아니라 ‘완료’ 탭에서 볼 수 있고, 체크를 다시 눌러 되돌릴 수 있어요.`
        : `‘${updated.title}’을(를) 진행 중으로 되돌렸어요.`);
    } catch (failure) {
      setError(message(failure));
      void load(null, false);
    } finally { setBusy(null); }
  }

  async function add(event: FormEvent) {
    event.preventDefault();
    const text = title.trim();
    if (!text || adding) return;
    setAdding(true);
    setError('');
    try {
      const created = await client.createTodo({ title: text, due: due || null, request_id: newRequestId() });
      setTitle('');
      setDue('');
      if (status === 'open') setItems(previous => [created, ...previous.filter(item => item.todo_id !== created.todo_id)]);
    } catch (failure) { setError(message(failure)); }
    finally { setAdding(false); }
  }

  return <main className="flex min-h-screen flex-col bg-canvas text-foreground">
    <header className="flex h-14 items-center gap-3 border-b bg-background px-5">
      <a href={`#${mailboxPath}`} className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-body text-muted-foreground hover:bg-accent focus-visible:outline-ring">
        <ArrowLeft className="size-4" aria-hidden="true" />받은편지함</a>
      <h1 className="flex items-center gap-2 text-title font-bold"><SquareCheck className="size-5 text-cat-work-fg" aria-hidden="true" />할 일</h1>
    </header>
    <div className="mx-auto w-full max-w-[816px] flex-1 px-7 py-5">
      <div role="tablist" aria-label="할 일 상태" className="mb-4 flex gap-2">
        {(['open', 'completed'] as const).map(value => <Button key={value} role="tab" aria-selected={status === value}
          variant={status === value ? 'default' : 'secondary'} className="h-8 px-3" onClick={() => setStatus(value)}>
          {value === 'open' ? '진행 중' : '완료'}</Button>)}
      </div>
      {status === 'open' && <form onSubmit={event => void add(event)} className="mb-4 flex flex-wrap items-end gap-2" aria-label="할 일 추가">
        <label className="grid min-w-[240px] flex-1 gap-1 text-caption text-muted-foreground">제목
          <input className={inputClass} value={title} maxLength={300} onChange={event => setTitle(event.target.value)} /></label>
        <label className="grid gap-1 text-caption text-muted-foreground">마감
          <input type="date" className={inputClass} value={due} onChange={event => setDue(event.target.value)} /></label>
        <Button type="submit" variant="secondary" className="h-9 px-3" disabled={adding || !title.trim()}>{adding ? '추가 중…' : '+ 할 일 추가'}</Button>
      </form>}
      {error && <p role="alert" className="mb-3 text-caption text-danger">{error}</p>}
      {notice && <p role="status" className="mb-3 rounded-leaf-sm bg-muted px-3 py-2 text-caption text-muted-foreground">{notice}</p>}
      {loading && !items.length && <div role="status" className="space-y-2"><span className="sr-only">할 일 불러오는 중</span>{[1, 2, 3].map(key => <div key={key} className="h-12 animate-pulse rounded-md bg-muted" />)}</div>}
      {!loading && !error && !items.length && <p className="py-10 text-center text-body text-muted-foreground">{status === 'open' ? '진행 중인 할 일이 없어요.' : '완료한 할 일이 없어요.'}</p>}
      <ul className="divide-y overflow-hidden rounded-leaf bg-background shadow-card" hidden={!items.length}>
        {items.map(todo => <li key={todo.todo_id} className="flex items-center gap-3 px-4 py-3" data-testid="todo-item">
          <input type="checkbox" className="size-4 accent-primary" checked={todo.status === 'completed'} disabled={busy !== null}
            aria-label={`${todo.title} ${todo.status === 'open' ? '완료로 표시' : '진행 중으로 되돌리기'}`} onChange={() => void toggle(todo)} />
          <span className="min-w-0 flex-1">
            <span className={`block truncate text-body ${todo.status === 'completed' ? 'text-muted-foreground line-through' : ''}`}>{todo.title}</span>
            <span className="block text-caption text-muted-foreground">{dueLabel(todo.due)}</span>
          </span>
          {todo.mail_id && <a href={`#/mail/inbox/${encodeURIComponent(todo.mail_id)}`} className="shrink-0 text-caption text-muted-foreground underline underline-offset-2 focus-visible:outline-ring">근거 메일</a>}
        </li>)}
      </ul>
      {cursor && <Button variant="secondary" className="mt-3 w-full" disabled={loading} onClick={() => void load(cursor, true)}>{loading ? '불러오는 중…' : '더 보기'}</Button>}
    </div>
  </main>;
}
