// F3 전용 계약. 공통 OpenAPI 생성 타입은 운영 등록 승인 뒤 재생성한다.
export type DateRange = { start: string; end_before: string };
export type Direction = 'received' | 'sent';
export type Counterparty = { kind: 'name' | 'address' | 'organization'; value: string };
export type Filters = {
  period?: DateRange | null;
  counterparty?: Counterparty | null;
  directions?: Direction[] | null;
  needs_reply?: boolean | null;
  replied?: boolean | null;
  category?: string | null;
  has_attachment?: boolean | null;
};
export type ParsedQuery = { filters: Filters; topic: string | null; expansions: string[] };
export type Overrides = Filters & { topic?: string | null };
export type SearchRequest = { ai_provider?: import('../../../shared/ai-bridge').AIChoice; query: string; overrides?: Overrides; search_id?: string };
export type SearchResult = {
  mail_id: string;
  number: number;
  score: number;
  reason: string;
  snippet: string;
  match_terms: string[];
  missing_conditions: string[];
  sources: ('keyword' | 'metadata' | 'vector')[];
  subject: string;
  from_name: string;
  from_addr: string;
  received_at: string;
  direction: Direction;
};
export type SearchAnswer = {
  text: string;
  sentences: { mail_id: string; quote: string }[];
  citations: { number: number; mail_id: string }[];
};
export type SearchFailure = { code: string; message: string };
export type RecentSearch = { search_id: string; query: string; created_at: string };
export type SearchEvent =
  | { type: 'parsed'; data: { search_id: string; parsed: ParsedQuery; reference_date: string } }
  | { type: 'results'; data: {
    results: SearchResult[]; partial: SearchResult[]; semantic_enabled: boolean; truncated: boolean;
  } }
  | { type: 'answer'; data: SearchAnswer }
  | { type: 'answer_error' | 'error'; data: SearchFailure };

export interface SearchClient {
  search(request: SearchRequest, signal: AbortSignal): AsyncIterable<SearchEvent>;
  recent(signal: AbortSignal): Promise<RecentSearch[]>;
}

export interface SearchNavigation {
  openMail?(request: { mail_id: string; direction: Direction; source: 'F3' }): void;
  openDraft?(request: { mail_id: string; source: 'F3' }): void;
  backToInbox?(): void;
}

export class SearchClientError extends Error {}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}
const mailId = (value: unknown): value is string =>
  typeof value === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(value);

function day(value: unknown): value is string {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
    && Number.isFinite(Date.parse(`${value}T00:00:00Z`))
    && new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;
}

function filters(value: unknown): value is Filters {
  if (!record(value)) return false;
  if (value.period !== null && value.period !== undefined && (!record(value.period)
    || !day(value.period.start) || !day(value.period.end_before)
    || value.period.start >= value.period.end_before)) return false;
  if (value.counterparty !== null && value.counterparty !== undefined && (!record(value.counterparty)
    || !['name', 'address', 'organization'].includes(String(value.counterparty.kind))
    || typeof value.counterparty.value !== 'string' || !value.counterparty.value.trim())) return false;
  if (value.directions !== null && value.directions !== undefined && (!strings(value.directions)
    || value.directions.length < 1 || value.directions.length > 2
    || new Set(value.directions).size !== value.directions.length
    || !value.directions.every((item) => ['received', 'sent'].includes(item)))) return false;
  return ['needs_reply', 'replied', 'has_attachment'].every((key) =>
    value[key] === null || value[key] === undefined || typeof value[key] === 'boolean')
    && (value.category === null || value.category === undefined || typeof value.category === 'string');
}

function result(value: unknown): value is SearchResult {
  return record(value) && mailId(value.mail_id) && Number.isInteger(value.number)
    && Number(value.number) > 0 && typeof value.score === 'number' && Number.isFinite(value.score)
    && ['reason', 'snippet', 'subject', 'from_name', 'from_addr', 'received_at']
      .every((key) => typeof value[key] === 'string')
    && strings(value.match_terms) && strings(value.missing_conditions)
    && strings(value.sources) && value.sources.every((source) => ['keyword', 'metadata', 'vector'].includes(source))
    && ['received', 'sent'].includes(String(value.direction))
    && Number.isFinite(Date.parse(String(value.received_at)));
}

export function readSearchEvent(value: unknown): SearchEvent {
  if (!record(value) || !record(value.data)) throw new SearchClientError('검색 응답 형식을 확인하지 못했어요.');
  const data = value.data;
  let valid = false;
  switch (value.type) {
    case 'parsed':
      valid = typeof data.search_id === 'string' && /^[a-f0-9]{32}$/.test(data.search_id)
        && day(data.reference_date) && record(data.parsed)
        && filters(data.parsed.filters) && strings(data.parsed.expansions)
        && (data.parsed.topic === null || typeof data.parsed.topic === 'string');
      break;
    case 'results': {
      const rows = [...(Array.isArray(data.results) ? data.results : []),
        ...(Array.isArray(data.partial) ? data.partial : [])];
      valid = Array.isArray(data.results) && Array.isArray(data.partial) && rows.every(result)
        && new Set(rows.map((row) => row.mail_id)).size === rows.length
        && new Set(rows.map((row) => row.number)).size === rows.length
        && typeof data.semantic_enabled === 'boolean' && typeof data.truncated === 'boolean';
      break;
    }
    case 'answer':
      valid = typeof data.text === 'string' && Array.isArray(data.sentences)
        && data.sentences.every((sentence) => record(sentence) && mailId(sentence.mail_id)
          && typeof sentence.quote === 'string' && sentence.quote.length > 0)
        && Array.isArray(data.citations) && data.citations.every((citation) =>
          record(citation) && mailId(citation.mail_id) && Number.isInteger(citation.number));
      break;
    case 'error':
    case 'answer_error':
      valid = typeof data.code === 'string' && typeof data.message === 'string';
  }
  if (!valid) throw new SearchClientError('검색 응답 형식을 확인하지 못했어요.');
  return value as SearchEvent;
}

export function readRecentSearches(value: unknown): RecentSearch[] {
  if (!Array.isArray(value) || value.length > 3 || !value.every((item) => record(item)
    && typeof item.search_id === 'string' && /^[a-f0-9]{32}$/.test(item.search_id)
    && typeof item.query === 'string' && typeof item.created_at === 'string')) {
    throw new SearchClientError('최근 검색을 확인하지 못했어요.');
  }
  return value as RecentSearch[];
}
