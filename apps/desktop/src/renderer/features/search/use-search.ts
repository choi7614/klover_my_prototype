import { useCallback, useEffect, useRef, useState } from 'react';
import {
  readSearchEvent, readRecentSearches, SearchClientError, type Overrides, type ParsedQuery, type RecentSearch, type SearchAnswer,
  type SearchClient, type SearchFailure, type SearchRequest, type SearchResult,
} from './contracts';

type Phase = 'idle' | 'parsing' | 'searching' | 'answering' | 'done' | 'error';
export type SearchState = {
  phase: Phase;
  parsed: ParsedQuery | null;
  results: SearchResult[];
  partial: SearchResult[];
  answer: SearchAnswer | null;
  answerError: SearchFailure | null;
  error: string | null;
  semantic: boolean;
  truncated: boolean;
  referenceDate: string | null;
};
const emptyState: SearchState = {
  phase: 'idle', parsed: null, results: [], partial: [], answer: null,
  answerError: null, error: null, semantic: false, truncated: false, referenceDate: null,
};

function validAnswer(answer: SearchAnswer, results: SearchResult[]): boolean {
  const numbers = new Map(results.map((row) => [row.mail_id, row.number]));
  const citations = new Map(answer.citations.map((citation) => [citation.mail_id, citation.number]));
  return answer.sentences.every((sentence) => numbers.has(sentence.mail_id)
    && citations.get(sentence.mail_id) === numbers.get(sentence.mail_id))
    && answer.citations.every((citation) => numbers.get(citation.mail_id) === citation.number)
    && (results.length === 0 ? answer.sentences.length === 0 : answer.sentences.length > 0);
}

export function useSearch(client: SearchClient, identityKey: string, provider: import('../../../shared/ai-bridge').AIChoice = 'default') {
  const providerRef = useRef(provider);
  providerRef.current = provider;
  const [state, setState] = useState<SearchState>(emptyState);
  const [recent, setRecent] = useState<RecentSearch[]>([]);
  const [recentError, setRecentError] = useState(false);
  const sequence = useRef(0);
  const recentSequence = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const recentController = useRef<AbortController | null>(null);
  const current = useRef<{ ai_provider?: import('../../../shared/ai-bridge').AIChoice; query: string; search_id?: string; overrides: Overrides }>({
    query: '', overrides: {},
  });

  const refreshRecent = useCallback(async () => {
    const id = ++recentSequence.current;
    recentController.current?.abort();
    const abort = new AbortController();
    recentController.current = abort;
    try {
      const rows = readRecentSearches(await client.recent(abort.signal));
      if (id === recentSequence.current && !abort.signal.aborted) {
        setRecent(rows);
        setRecentError(false);
      }
    } catch {
      if (id === recentSequence.current && !abort.signal.aborted) setRecentError(true);
    }
  }, [client]);

  useEffect(() => {
    ++sequence.current;
    controller.current?.abort();
    current.current = { query: '', overrides: {} };
    setState(emptyState);
    setRecent([]);
    setRecentError(false);
    void refreshRecent();
    return () => {
      ++sequence.current;
      ++recentSequence.current;
      controller.current?.abort();
      recentController.current?.abort();
    };
  }, [client, identityKey, refreshRecent]);

  const execute = useCallback(async (request: SearchRequest, keepParsed: boolean) => {
    const id = ++sequence.current;
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setState((previous) => ({ ...emptyState, phase: 'parsing', parsed: keepParsed ? previous.parsed : null }));
    let phase: 'start' | 'parsed' | 'results' | 'finished' = 'start';
    let results: SearchResult[] = [];
    try {
      for await (const raw of client.search(request, abort.signal)) {
        // 취소를 무시하는 상대라도 이전 사용자/이전 요청의 응답은 표시하지 않는다.
        if (id !== sequence.current || abort.signal.aborted) return;
        const event = readSearchEvent(raw);
        if (event.type === 'error') throw new SearchClientError(event.data.message);
        if (event.type === 'parsed' && phase === 'start') {
          phase = 'parsed';
          current.current.search_id = event.data.search_id;
          setState((previous) => ({ ...previous, phase: 'searching', parsed: event.data.parsed,
            referenceDate: event.data.reference_date }));
        } else if (event.type === 'results' && phase === 'parsed') {
          phase = 'results';
          results = event.data.results;
          setState((previous) => ({ ...previous, phase: 'answering', results,
            partial: event.data.partial, semantic: event.data.semantic_enabled,
            truncated: event.data.truncated }));
        } else if ((event.type === 'answer' || event.type === 'answer_error') && phase === 'results') {
          phase = 'finished';
          if (event.type === 'answer' && validAnswer(event.data, results)) {
            setState((previous) => ({ ...previous, phase: 'done', answer: event.data }));
          } else {
            setState((previous) => ({ ...previous, phase: 'done', answerError: event.type === 'answer_error'
              ? event.data : { code: 'invalid_answer', message: '답변의 근거를 확인하지 못했어요.' } }));
          }
        } else {
          throw new SearchClientError('검색 응답 순서를 확인하지 못했어요.');
        }
      }
      if (id !== sequence.current || abort.signal.aborted) return;
      if (phase !== 'finished') throw new SearchClientError('검색 응답이 중간에 끊겼어요. 다시 시도해 주세요.');
      void refreshRecent();
    } catch (error) {
      if (id !== sequence.current || abort.signal.aborted) return;
      setState((previous) => ({ ...previous, phase: 'error', answer: null,
        error: error instanceof SearchClientError ? error.message : '검색을 완료하지 못했어요. 다시 시도해 주세요.' }));
    }
  }, [client, refreshRecent]);

  const search = useCallback((query: string) => {
    current.current = { query, overrides: {}, ai_provider: providerRef.current };
    return execute({ query, ai_provider: providerRef.current }, false);
  }, [execute]);

  const reSearch = useCallback((changes: Overrides) => {
    if (!current.current.search_id) return;
    current.current.overrides = { ...current.current.overrides, ...changes };
    current.current.ai_provider = providerRef.current;
    return execute({ ...current.current }, true);
  }, [execute]);

  const retry = useCallback(() => {
    current.current.ai_provider = providerRef.current;
    return execute({ ...current.current }, true);
  }, [execute]);
  const openRecent = useCallback((row: RecentSearch) => {
    // 최근 검색의 상대 날짜는 다시 누르는 날의 한국 날짜로 해석한다.
    return search(row.query);
  }, [search]);

  return { state, recent, recentError, search, reSearch, retry, openRecent };
}
