import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SyntheticSearchClient } from '../../../../tests/f3/synthetic-client';
import { SearchPage } from './search-page';
import type { SearchClient } from './contracts';

function search(query = '지난달 예산 메일') {
  fireEvent.change(screen.getByRole('textbox', { name: '검색 질문' }), { target: { value: query } });
  fireEvent.click(screen.getByRole('button', { name: '검색' }));
}
async function results() {
  await screen.findByRole('heading', { name: '조건에 맞는 메일 3건' });
  await screen.findByRole('button', { name: '근거 1번 메일' });
}

describe('F3 독립 검색 화면', () => {
  it('검색 결과와 유효한 근거·부분 결과를 표시하고 F0/F2 계약을 호출한다', async () => {
    const openMail = vi.fn(); const openDraft = vi.fn();
    render(<SearchPage client={new SyntheticSearchClient()} identityKey="u:a" navigation={{ openMail, openDraft }} />);
    search(); await results();
    fireEvent.click(screen.getByRole('button', { name: '근거 2번 메일' }));
    expect(screen.getByRole('article', { name: '검색 결과 2' })).toHaveFocus();
    fireEvent.click(screen.getByRole('button', { name: '출장비 예산 초과분 처리 문의' }));
    expect(openMail).toHaveBeenCalledWith({ mail_id: 'm2', direction: 'received', source: 'F3' });
    fireEvent.click(within(screen.getByRole('article', { name: '검색 결과 2' })).getByRole('button', { name: '◆ 답장 초안' }));
    expect(openDraft).toHaveBeenCalledWith({ mail_id: 'm2', source: 'F3' });
    fireEvent.click(screen.getByText('조건을 일부만 만족하는 메일 1건 더 보기'));
    expect(screen.getByText('미충족: 기간')).toBeVisible();
  });

  it('칩 삭제와 필터 수정은 기존 해석 ID를 유지하고 누적한 override로 재검색한다', async () => {
    const client = new SyntheticSearchClient();
    render(<SearchPage client={client} identityKey="u:a" />);
    search(); await results();
    fireEvent.click(screen.getByRole('button', { name: '기간 조건 삭제' }));
    fireEvent.click(screen.getByRole('button', { name: '주제 조건 삭제' }));
    await waitFor(() => expect(client.requests).toHaveLength(3));
    expect(client.requests[2]).toMatchObject({ search_id: expect.any(String), overrides: { period: null, topic: null } });
    await waitFor(() => expect(screen.queryByRole('button', { name: '주제 조건 삭제' })).not.toBeInTheDocument());
    fireEvent.change(screen.getByLabelText('대상'), { target: { value: 'sent' } });
    fireEvent.click(screen.getByRole('button', { name: '조건 적용' }));
    await waitFor(() => expect(client.requests.at(-1)?.overrides?.directions).toEqual(['sent']));
  });

  it('빈 상태와 오류, 답변 미연결을 결과와 구분한다', async () => {
    render(<SearchPage client={new SyntheticSearchClient()} identityKey="u:a" />);
    search('빈 결과');
    await screen.findByText('조건에 맞는 메일을 찾지 못했어요.');
    expect(screen.getByRole('button', { name: '최근 3개월' })).toBeEnabled();
    search('해석 오류'); await screen.findByRole('alert');
    expect(screen.getByRole('alert')).toHaveTextContent('질문을 이해하지 못했어요.');
    search('답변 오류');
    await screen.findByText('답변 기능이 아직 연결되지 않았어요.');
    expect(screen.getByRole('heading', { name: '조건에 맞는 메일 3건' })).toBeVisible();
    expect(screen.queryByRole('button', { name: '근거 1번 메일' })).not.toBeInTheDocument();
  });

  it('취소를 무시한 오래된 요청의 오류와 결과를 표시하지 않는다', async () => {
    const client = new SyntheticSearchClient();
    let release!: () => void;
    client.delay = (query) => query === '해석 오류' ? new Promise<void>((resolve) => { release = resolve; }) : Promise.resolve();
    render(<SearchPage client={client} identityKey="u:a" />);
    search('해석 오류');
    expect(screen.getByText('◆ 질문을 이해하고 있어요…')).toBeVisible();
    search('빠른 검색'); await results();
    await act(async () => { release(); });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '조건에 맞는 메일 3건' })).toBeVisible();
  });

  it('계정이 바뀌면 결과와 최근 검색을 지우고 이전 계정 응답을 무시한다', async () => {
    const client = new SyntheticSearchClient();
    const { rerender } = render(<SearchPage client={client} identityKey="u:a" />);
    search('계정A 질문'); await results();
    rerender(<SearchPage client={new SyntheticSearchClient()} identityKey="u:b" />);
    expect(screen.queryByRole('heading', { name: '조건에 맞는 메일 3건' })).not.toBeInTheDocument();
    await screen.findByText('아직 검색 기록이 없어요.');
    expect(screen.queryByRole('button', { name: '계정A 질문' })).not.toBeInTheDocument();
  });

  it('유효하지 않은 인용과 HTML을 실행 가능한 응답으로 쓰지 않는다', async () => {
    const client = new SyntheticSearchClient();
    client.answerOverride = { text: '<script>bad()</script>',
      sentences: [{ mail_id: 'foreign', quote: '존재하지 않는 근거' }], citations: [{ mail_id: 'foreign', number: 1 }] };
    render(<SearchPage client={client} identityKey="u:a" />);
    search();
    await screen.findByText('답변의 근거를 확인하지 못했어요.');
    expect(screen.queryByText('존재하지 않는 근거')).not.toBeInTheDocument();
    expect(document.querySelector('script')).toBeNull();
  });

  it('F0/F2 미연결 버튼과 2차 대화 기능은 동작하지 않는다', async () => {
    render(<SearchPage client={new SyntheticSearchClient()} identityKey="u:a" />);
    search(); await results();
    expect(screen.getAllByRole('button', { name: '◆ 답장 초안' }).every((button) => (button as HTMLButtonElement).disabled)).toBe(true);
    expect(screen.getByText(/이어서 질문하기/)).toHaveAttribute('aria-disabled', 'true');
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    expect(screen.getByRole('textbox', { name: '검색 질문' })).toHaveFocus();
  });

  it('주제를 고치면 확장어와 함께 이전 조건이 되살아나지 않고, 최근 질문은 새로 해석한다', async () => {
    const client = new SyntheticSearchClient();
    render(<SearchPage client={client} identityKey="u:a" />);
    search('최근 질문'); await results();
    fireEvent.change(screen.getByLabelText('주제'), { target: { value: '문서-123' } });
    fireEvent.click(screen.getByRole('button', { name: '조건 적용' }));
    await waitFor(() => expect(client.requests.at(-1)?.overrides?.topic).toBe('문서-123'));
    await results();
    fireEvent.click(await screen.findByRole('button', { name: '최근 질문' }));
    await waitFor(() => expect(client.requests.at(-1)).toEqual({ query: '최근 질문' }));
  });

  it('기능 진입의 자동 검색은 F0 라우터 수정 없이 실행할 수 있다', async () => {
    const client = new SyntheticSearchClient();
    render(<SearchPage client={client} identityKey="u:a" initialQuery="지난달 예산" autoSearch />);
    await results();
    expect(client.requests[0]).toEqual({ query: '지난달 예산' });
  });

  it('새 결과가 나온 뒤 도착한 이전 성공 응답도 화면을 덮어쓰지 않는다', async () => {
    const base = new SyntheticSearchClient();
    let release!: () => void;
    const pending = new Promise<void>((resolve) => { release = resolve; });
    const client: SearchClient = {
      recent: () => base.recent(),
      async *search(request) {
        if (request.query === '이전 검색') await pending;
        for await (const event of base.search(request)) {
          if (event.type === 'results') {
            yield { ...event, data: { ...event.data, results: event.data.results.map((row) => ({
              ...row, subject: `${request.query} 결과 ${row.number}`,
            })) } };
          } else yield event;
        }
      },
    };
    render(<SearchPage client={client} identityKey="u:a" />);
    search('이전 검색'); search('새 검색'); await results();
    expect(screen.getByRole('button', { name: '새 검색 결과 1' })).toBeInTheDocument();
    await act(async () => { release(); });
    await waitFor(() => expect(base.requests).toHaveLength(2));
    expect(screen.queryByRole('button', { name: '이전 검색 결과 1' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '새 검색 결과 1' })).toBeInTheDocument();
  });
});
