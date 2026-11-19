// 테스트 전용. 실제 자연어/임베딩/모델의 정확도를 흉내 낸 운영 구현이 아니다.
import type {
  Overrides, ParsedQuery, RecentSearch, SearchAnswer, SearchClient, SearchEvent, SearchRequest,
  SearchResult,
} from '../../src/renderer/features/search/contracts';

export const syntheticRows: SearchResult[] = [
  ['m1', '4분기 예산 재배정 사전 협의 요청', '다음 분기 예산 재배정을 협의해 주세요.', '박지훈', '2026-10-24'],
  ['m2', '출장비 예산 초과분 처리 문의', '출장비 예산 초과분을 확인해 주세요.', '정혜원', '2026-10-18'],
  ['m3', '판촉비 예산 전용 문의', '남은 예산을 행사비로 전용할 수 있나요?', '박지훈', '2026-10-09'],
].map(([mail_id, subject, snippet, from_name, day], index) => ({
  mail_id, subject, snippet, from_name, from_addr: 'synthetic@example.invalid',
  number: index + 1, received_at: `${day}T09:00:00+09:00`, score: 0.03 - index * 0.001,
  reason: '기간 일치 · 키워드 일치', match_terms: ['예산'], missing_conditions: [],
  sources: ['keyword'], direction: 'received',
}));

export class SyntheticSearchClient implements SearchClient {
  requests: SearchRequest[] = [];
  delay: (query: string) => Promise<void> = async () => {};
  answerOverride: SearchAnswer | null = null;
  private records = new Map<string, { query: string; overrides: Overrides }>();

  async *search(request: SearchRequest): AsyncIterable<SearchEvent> {
    this.requests.push(structuredClone(request));
    // 늦은 서버가 취소를 무시하는 상황도 검사할 수 있게 의도적으로 signal을 쓰지 않는다.
    await this.delay(request.query);
    if (request.query === '해석 오류') {
      yield { type: 'error', data: { code: 'parse_failed', message: '질문을 이해하지 못했어요.' } }; return;
    }
    const previous = request.search_id ? this.records.get(request.search_id)?.overrides : {};
    const overrides: Overrides = { ...previous, ...request.overrides };
    const search_id = (this.records.size + 1).toString(16).padStart(32, '0');
    this.records.set(search_id, { query: request.query, overrides });
    const parsed: ParsedQuery = {
      filters: { period: { start: '2026-10-01', end_before: '2026-11-01' } }, topic: '예산', expansions: [],
    };
    const { topic, ...filters } = overrides;
    Object.assign(parsed.filters, filters);
    if (topic !== undefined) parsed.topic = topic;
    yield { type: 'parsed', data: { search_id, parsed, reference_date: '2026-11-19' } };
    await new Promise((resolve) => setTimeout(resolve, 30));
    const rows = request.query === '빈 결과' ? [] : syntheticRows.map((row) => ({ ...row }));
    const partial: SearchResult[] = rows.length && parsed.filters.period ? [{
      ...syntheticRows[0], mail_id: 'm4', number: 4, subject: '기간 밖 합성 예산 메일',
      missing_conditions: ['기간'], reason: '키워드 일치', received_at: '2026-11-10T09:00:00+09:00',
    }] : [];
    yield { type: 'results', data: { results: rows, partial, semantic_enabled: false, truncated: false } };
    await new Promise((resolve) => setTimeout(resolve, 30));
    if (request.query === '답변 오류') {
      yield { type: 'answer_error', data: { code: 'answer_unavailable', message: '답변 기능이 아직 연결되지 않았어요.' } }; return;
    }
    yield { type: 'answer', data: this.answerOverride ?? {
      text: rows.length ? '합성 메일 발췌' : '찾은 메일이 없습니다',
      sentences: rows.map((row) => ({ mail_id: row.mail_id, quote: row.snippet })),
      citations: rows.map((row) => ({ mail_id: row.mail_id, number: row.number })),
    } };
  }

  async recent(): Promise<RecentSearch[]> {
    return [...this.records.entries()].reverse().filter(([, row], index, all) =>
      all.findIndex(([, other]) => other.query === row.query) === index,
    ).slice(0, 3).map(([search_id, row]) => ({
      search_id, query: row.query, created_at: '2026-11-19T09:00:00+09:00',
    }));
  }
}
