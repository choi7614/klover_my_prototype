import { AIExecutionNotice } from '../ai-settings/ai-execution';
import { AIChoiceControl } from '../ai-settings/ai-choice';
import type { AIChoice } from '../../../shared/ai-bridge';
import { useEffect, useRef, useState, type ComponentProps, type FormEvent } from 'react';
import { Search, X } from 'lucide-react';
import { Button as BaseButton } from '@/components/ui/button';
import type { Counterparty, Overrides, SearchClient, SearchNavigation, SearchResult } from './contracts';
import { useSearch } from './use-search';
import './search.css';

type Props = {
  client: SearchClient;
  identityKey: string;
  navigation?: SearchNavigation;
  initialQuery?: string;
  autoSearch?: boolean;
};

function Button({ className, ...props }: ComponentProps<typeof BaseButton>) {
  return <BaseButton {...props} className={['f3-button', className].filter(Boolean).join(' ')} />;
}

function nextDay(day: string, offset = 1): string {
  const value = new Date(`${day}T00:00:00Z`);
  value.setUTCDate(value.getUTCDate() + offset);
  return value.toISOString().slice(0, 10);
}

function highlight(text: string, terms: string[]) {
  const matches = terms.filter(Boolean).sort((a, b) => b.length - a.length);
  if (!matches.length) return text;
  const escaped = matches.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  return text.split(new RegExp(`(${escaped.join('|')})`, 'gi')).map((part, index) => (
    matches.some((term) => term.toLowerCase() === part.toLowerCase())
      ? <mark key={index}>{part}</mark> : part
  ));
}

function ResultCard({ row, highlighted, navigation }: {
  row: SearchResult; highlighted: boolean; navigation: SearchNavigation;
}) {
  return <article id={`f3-result-${row.mail_id}`} tabIndex={-1}
    className={`f3-result ${highlighted ? 'f3-result-highlight' : ''}`} aria-label={`검색 결과 ${row.number}`}>
    <span className="f3-number">{row.number}</span>
    <div className="f3-result-content">
      <div className="f3-result-meta"><span><strong>{row.from_name || row.from_addr}</strong></span>
        <time dateTime={row.received_at}>{new Intl.DateTimeFormat('ko-KR', {
          timeZone: 'Asia/Seoul', month: 'long', day: 'numeric',
        }).format(new Date(row.received_at))}</time></div>
      <button className="f3-mail-title" disabled={!navigation.openMail}
        title={navigation.openMail ? '메일 열기' : '메일 열기 연결 준비 중'}
        onClick={() => navigation.openMail?.({ mail_id: row.mail_id, direction: row.direction, source: 'F3' })}>
        {row.subject || '(제목 없음)'}
      </button>
      <blockquote>{highlight(row.snippet, row.match_terms)}</blockquote>
      <div className="f3-result-actions">
        <span className="f3-tag">{row.direction === 'received' ? '받은 메일' : '보낸 메일'}</span>
        <span className="f3-reason">{row.reason}</span>
        {row.missing_conditions.length > 0 && <span className="f3-missing">
          미충족: {row.missing_conditions.join(', ')}
        </span>}
        <Button variant="secondary" className="f3-draft" disabled={!navigation.openDraft}
          title={navigation.openDraft ? undefined : '답장 초안 연결 준비 중'}
          onClick={() => navigation.openDraft?.({ mail_id: row.mail_id, source: 'F3' })}>
          ◆ 답장 초안
        </Button>
      </div>
    </div>
  </article>;
}

function SearchScreen({ client, identityKey, navigation = {}, initialQuery = '', autoSearch = false }: Props) {
  const [provider, setProvider] = useState<AIChoice>('default');
  const { state, recent, recentError, search, reSearch, retry, openRecent } = useSearch(client, identityKey, provider);
  const [query, setQuery] = useState(initialQuery);
  const [sort, setSort] = useState('relevance');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [party, setParty] = useState('');
  const [topic, setTopic] = useState('');
  const [partyKind, setPartyKind] = useState<'name' | 'address'>('name');
  const [direction, setDirection] = useState('both');
  const [filterError, setFilterError] = useState('');
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const highlightTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const filters = state.parsed?.filters;
    setStart(filters?.period?.start ?? '');
    setEnd(filters?.period ? nextDay(filters.period.end_before, -1) : '');
    setParty(filters?.counterparty?.value ?? '');
    setTopic(state.parsed?.topic ?? '');
    setPartyKind(filters?.counterparty?.kind === 'address' ? 'address' : 'name');
    setDirection(filters?.directions?.length === 1 ? filters.directions[0] : 'both');
  }, [state.parsed]);

  useEffect(() => {
    if (autoSearch && initialQuery.trim()) void search(initialQuery.trim());
  }, [autoSearch, initialQuery, search]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault(); input.current?.focus();
      } else if (event.key === 'Escape') navigation.backToInbox?.();
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
    };
  }, [navigation]);

  useEffect(() => () => {
    if (highlightTimer.current) clearTimeout(highlightTimer.current);
  }, []);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (query.trim()) { setFilterError(''); void search(query.trim()); }
  };
  const changeFilters = (event: FormEvent) => {
    event.preventDefault();
    if ((start && !end) || (!start && end) || (start && end && start > end)) {
      setFilterError('시작일과 종료일을 올바르게 입력해 주세요.'); return;
    }
    setFilterError('');
    const counterpart: Counterparty | null = party.trim() ? { kind: partyKind, value: party.trim() } : null;
    void reSearch({ period: start ? { start, end_before: nextDay(end) } : null,
      counterparty: counterpart,
      ...(topic.trim() !== (state.parsed?.topic ?? '') ? { topic: topic.trim() || null } : {}),
      directions: direction === 'both' ? null : [direction as 'received' | 'sent'] });
  };
  const cite = (identifier: string) => {
    const card = document.getElementById(`f3-result-${identifier}`);
    card?.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
    card?.focus({ preventScroll: true });
    setHighlighted(identifier);
    if (highlightTimer.current) clearTimeout(highlightTimer.current);
    highlightTimer.current = setTimeout(() => setHighlighted(null), 1000);
  };
  const widen = () => {
    if (!state.referenceDate) return;
    const today = new Date(`${state.referenceDate}T00:00:00Z`);
    const first = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth() - 3, 1));
    const lastDay = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0)).getUTCDate();
    first.setUTCDate(Math.min(today.getUTCDate(), lastDay));
    void reSearch({ period: { start: first.toISOString().slice(0, 10), end_before: nextDay(state.referenceDate) } });
  };
  const filters = state.parsed?.filters;
  const chips: { key: keyof Overrides; label: string; value: string }[] = [];
  if (filters?.period) chips.push({ key: 'period', label: '기간', value: `${filters.period.start} ~ ${nextDay(filters.period.end_before, -1)}` });
  if (filters?.counterparty) chips.push({ key: 'counterparty', label: '상대', value: filters.counterparty.value });
  if (state.parsed?.topic) chips.push({ key: 'topic', label: '주제', value: state.parsed.topic });
  if (filters?.directions) chips.push({ key: 'directions', label: '대상', value: filters.directions.map((item) => item === 'received' ? '받은 메일' : '보낸 메일').join('·') });
  const busy = ['parsing', 'searching', 'answering'].includes(state.phase);
  const showResults = ['answering', 'done'].includes(state.phase) || state.results.length > 0;
  const results = [...state.results].sort((a, b) => sort === 'newest'
    ? Date.parse(b.received_at) - Date.parse(a.received_at) : a.number - b.number);

  return <section className="f3-search-page" aria-label="자연어 검색">
    <header className="f3-search-header">
      <h1>자연어 검색</h1>      <AIExecutionNotice value={state.aiExecution} />
      <AIChoiceControl purpose="search" value={provider} onChange={setProvider} disabled={['parsing', 'searching', 'answering'].includes(state.phase)} />
      <form onSubmit={submit} className="f3-query-form">
        <span className="f3-ai" aria-hidden="true">◆</span>
        <label className="sr-only" htmlFor="f3-query">검색 질문</label>
        <input ref={input} id="f3-query" value={query} maxLength={2000}
          placeholder="무엇이든 물어보세요" onChange={(event) => setQuery(event.target.value)} />
        <kbd>Ctrl K</kbd>
        <Button type="submit" variant="secondary" disabled={!query.trim()}><Search aria-hidden="true" />검색</Button>
      </form>
      {navigation.backToInbox && <Button variant="secondary" onClick={navigation.backToInbox}>받은편지함으로</Button>}
    </header>
    <div className="f3-understood" aria-live="polite">
      <strong>이렇게 이해했어요</strong>
      {state.phase === 'parsing' && !state.parsed ? <>
        <span>◆ 질문을 이해하고 있어요…</span>
        {[1, 2, 3].map((number) => <span key={number} className="f3-skeleton f3-chip-skeleton" />)}
      </> : chips.map((chip) => <button className="f3-chip" key={chip.key}
        aria-label={`${chip.label} 조건 삭제`} onClick={() => void reSearch({ [chip.key]: null })}>
        <b>{chip.label}</b> {chip.value}<X size={14} aria-hidden="true" />
      </button>)}
      {state.parsed && <button className="f3-add-condition" onClick={() => document.getElementById('f3-filters')?.focus()}>
        + 조건 추가
      </button>}
    </div>
    {state.parsed && <div className="f3-scope-summary" aria-label="실제 검색 범위">
      <p>검색 범위: 이 계정에 저장된 메일만 검색해요. 가져오지 않은 과거 메일은 포함되지 않아요.</p>
      {filters?.period && <p>적용 기간(한국 시간): {filters.period.start} ~ {nextDay(filters.period.end_before, -1)} · 종료일 포함</p>}
      <p>원래 검색어: {[state.parsed.topic, ...(state.parsed.original_terms ?? [])].filter(Boolean).filter((term, index, terms) => terms.indexOf(term) === index).join(', ') || '조건만 검색'}</p>
      <p>자동 확장어: {state.parsed.expansions.join(', ') || '없음'}</p>
    </div>}
    <div className="f3-search-body">
      <main className="f3-results" aria-busy={busy}>
        {state.phase === 'idle' && <div className="f3-empty"><Search aria-hidden="true" />
          <h2>찾고 싶은 메일을 말해 주세요</h2><p>기간, 보낸 사람, 주제로 검색할 수 있어요.</p></div>}
        {state.error && <div role="alert" className="f3-error"><p>{state.error}</p>
          <Button variant="secondary" onClick={() => void retry()}>다시 시도</Button></div>}
        {state.phase === 'searching' && <div role="status"><p>조건에 맞는 메일을 찾고 있어요…</p>
          {[1, 2, 3].map((number) => <div key={number} className="f3-skeleton f3-card-skeleton" />)}</div>}
        {showResults && <>
          <div className="f3-answer" aria-label="AI 답변">
            <h2>◆ AI 답변</h2>
            {state.phase === 'answering' && <p role="status">◆ 근거를 확인하고 있어요…</p>}
            {state.answerError && <p role="status">{state.answerError.message}</p>}
            {state.answer && state.results.length > 0 && state.answer.sentences.length === 0 &&
              <p>관련 후보는 있지만 답변할 근거가 부족해요. 메일을 확인해 주세요.</p>}
            {state.answer && state.results.length > 0 && state.answer.sentences.map((sentence, index) => {
              const citation = state.answer!.citations.find((item) => item.mail_id === sentence.mail_id)!;
              return <p key={index}>{sentence.quote} <button className="f3-citation"
                aria-label={`근거 ${citation.number}번 메일`} onClick={() => cite(citation.mail_id)}>
                {citation.number}</button></p>;
            })}
            {state.results.length === 0 && <div className="f3-empty-result">
              <p>조건에 맞는 메일을 찾지 못했어요.</p><span>기간을 넓혀 볼까요? </span>
              <Button variant="secondary" onClick={widen}>최근 3개월</Button>
            </div>}
          </div>
          <div className="f3-result-heading"><h2>조건에 맞는 메일 {results.length}건</h2>
            <label>정렬 <select aria-label="결과 정렬" value={sort} onChange={(event) => setSort(event.target.value)}>
              <option value="relevance">관련도순</option><option value="newest">최신순</option>
            </select></label></div>
          <p className="f3-search-method">{state.semantic ? '키워드·의미 검색 결과' : '키워드·조건 검색 결과 · 이번 검색은 의미 검색을 사용하지 않았어요.'}</p>
          {state.warnings.map((warning) => <p role="status" key={warning.code}>{warning.message}</p>)}
          {state.coverage && <p className="f3-search-method">의미 검색 가능 메일 {state.coverage.compatible_mails} / 조건 내 저장 메일 {state.coverage.eligible_mails}건 · 검사한 청크 {state.coverage.scanned_chunks}개</p>}
          {state.truncated && <p role="status">일부 결과만 표시하고 있어요. 조건을 좁혀 주세요.</p>}
          {results.map((row) => <ResultCard key={row.mail_id} row={row} highlighted={highlighted === row.mail_id} navigation={navigation} />)}
          {state.partial.length > 0 && <details className="f3-partial"><summary>
            조건을 일부만 만족하는 메일 {state.partial.length}건 더 보기
          </summary>{state.partial.map((row) => <ResultCard key={row.mail_id} row={row} highlighted={highlighted === row.mail_id} navigation={navigation} />)}</details>}
        </>}
        <div className="f3-followup" aria-disabled="true">◆ 이어서 질문하기… <span>2차</span></div>
      </main>
      <aside className="f3-filter-panel" aria-label="검색 필터">
        <h2>필터</h2>
        <form id="f3-filters" tabIndex={-1} onSubmit={changeFilters}>
          <fieldset disabled={!state.parsed}>
            <legend className="sr-only">검색 조건 수정</legend>
            <label>시작일<input type="date" aria-label="시작일" value={start} onChange={(event) => setStart(event.target.value)} /></label>
            <label>종료일<input type="date" aria-label="종료일" value={end} onChange={(event) => setEnd(event.target.value)} /></label>
            <label>상대 기준<select aria-label="상대 기준" value={partyKind} onChange={(event) => setPartyKind(event.target.value as 'name' | 'address')}>
              <option value="name">이름</option><option value="address">메일 주소</option>
            </select></label>
            <label>상대<input aria-label="상대" value={party} maxLength={200} onChange={(event) => setParty(event.target.value)} /></label>
            <label>주제<input aria-label="주제" value={topic} maxLength={200} onChange={(event) => setTopic(event.target.value)} /></label>
            <label>대상<select aria-label="대상" value={direction} onChange={(event) => setDirection(event.target.value)}>
              <option value="both">받은 메일 + 보낸 메일</option><option value="received">받은 메일</option><option value="sent">보낸 메일</option>
            </select></label>
            <Button variant="secondary" type="submit">조건 적용</Button>
          </fieldset>
          {filterError && <p role="alert">{filterError}</p>}
        </form>
        <fieldset disabled className="f3-unsupported"><legend>카테고리·첨부파일·회신 상태</legend>
          <p>메일 분석 연결 후 사용할 수 있어요.</p>
        </fieldset>
        <section className="f3-recent"><h2>최근 검색</h2>
          {recent.length === 0 && <p>아직 검색 기록이 없어요.</p>}
          {recentError && <p role="status">최근 검색을 불러오지 못했어요.</p>}
          {recent.map((row) => <button key={row.search_id} onClick={() => { setQuery(row.query); void openRecent(row); }}>{row.query}</button>)}
        </section>
      </aside>
    </div>
  </section>;
}

// 계정 변경 시 이전 계정의 결과가 한 프레임도 남지 않게 기능 상태를 새로 만든다.
export function SearchPage(props: Props) {
  return <SearchScreen key={props.identityKey} {...props} />;
}
