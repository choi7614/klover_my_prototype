import { useCallback, useEffect, useState, useRef } from 'react';
import { MAX_BATCH, type AnalysisCategory, type AutoAnalysisState, type MailAnalysisView } from '../../../shared/f1-bridge';
import { AnalysisClientError, type MailAnalysisClient } from './client';

/** 분석 대기 메일이 있고 자동 분석이 켜져 있을 때만 다시 확인한다(WebSocket 연결 전 임시 방식). */
export const POLL_MS = 3000;
export const MAX_POLLS = 60;

export type RetryNotice = { mailId: string; message: string };

export function useMailAnalysis(client: MailAnalysisClient | undefined, mailIds: string[]) {
  const revision = useRef(0);
  const currentClient = useRef(client); currentClient.current = client;
  const key = [...new Set(mailIds)].join(',');
  const [views, setViews] = useState<Record<string, MailAnalysisView>>({});
  const [state, setState] = useState<AutoAnalysisState | null>(null);
  const [round, setRound] = useState(0);
  const [retryNotice, setRetryNotice] = useState<RetryNotice | null>(null);

  useEffect(() => {
    if (!client || !key) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let polls = 0;
    const ids = key.split(',');
    const groups: string[][] = [];
    for (let index = 0; index < ids.length; index += MAX_BATCH) groups.push(ids.slice(index, index + MAX_BATCH));
    const load = async () => {
      const started = revision.current;
      let batches;
      try { batches = await Promise.all(groups.map(group => client.batch(group))); }
      catch { return; } // 불러오지 못하면 지금 보이는 내용을 그대로 두고 다시 묻지 않는다.
      if (!active || started !== revision.current) return;
      const items = batches.flatMap(batch => batch.items);
      const auto = batches[0]?.auto_analysis ?? null;
      setViews(previous => {
        const next = { ...previous };
        for (const item of items) next[item.mail_id] = item;
        return next;
      });
      setState(auto);
      const waiting = auto === 'ready' && items.some(item => item.analysis_status === 'pending');
      if (waiting && ++polls < MAX_POLLS) timer = setTimeout(() => void load(), POLL_MS);
    };
    void load();
    return () => { active = false; if (timer) clearTimeout(timer); };
  }, [client, key, round]);

  const retry = useCallback(async (mailId: string) => {
    if (!client) return;
    setRetryNotice(null);
    try {
      await client.retry(mailId);
      setViews(previous => previous[mailId]
        ? { ...previous, [mailId]: { ...previous[mailId], analysis_status: 'pending', failure_code: null } }
        : previous);
      setRound(value => value + 1);
    } catch (error) {
      setRetryNotice({ mailId, message: error instanceof AnalysisClientError ? error.message : 'AI 분석을 다시 시작하지 못했습니다.' });
    }
  }, [client]);

  const setCategory = useCallback(async (mailId: string, category: AnalysisCategory) => {
    if (!client?.setCategory) throw new Error('category_unavailable');
    revision.current += 1;
    try {
      const result = await client.setCategory(mailId, category);
      if (currentClient.current !== client) return;
      revision.current += 1;
      setViews(previous => previous[mailId] ? { ...previous, [mailId]: { ...previous[mailId], category: result.effective_category } } : previous);
    } finally { if (currentClient.current === client) setRound(value => value + 1); }
  }, [client]);

  return { setCategory: client?.setCategory ? setCategory : undefined, views, state, retry, retryNotice };
}
