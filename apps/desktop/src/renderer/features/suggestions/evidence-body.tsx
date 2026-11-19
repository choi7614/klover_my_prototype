import type { EvidenceSpan, Suggestion } from './types';

export function validEvidence(mailId: string, body: string, spans: EvidenceSpan[]) {
  const points = Array.from(body);
  return spans.length > 0 && spans.every(span =>
    span.mail_id === mailId && Number.isInteger(span.start) && Number.isInteger(span.end)
    && span.start >= 0 && span.end > span.start && span.end <= points.length
    && points.slice(span.start, span.end).join('') === span.quote,
  );
}

export function EvidenceBody({ mailId, body, suggestions, activeId }: {
  mailId: string; body: string; suggestions: Suggestion[]; activeId?: string;
}) {
  const points = Array.from(body);
  const spans = suggestions.filter(row => row.mail_id === mailId && validEvidence(mailId, body, row.evidence_spans))
    .flatMap(row => row.evidence_spans.map(span => ({ ...span, id: row.suggestion_id })));
  const cuts = [...new Set([0, points.length, ...spans.flatMap(span => [span.start, span.end])])].sort((a, b) => a - b);
  return <div data-testid="mail-evidence" className="whitespace-pre-wrap break-words text-[15px] leading-[26px]">
    {cuts.slice(0, -1).map((start, index) => {
      const end = cuts[index + 1];
      const matching = spans.filter(span => span.start <= start && span.end >= end);
      const text = points.slice(start, end).join('');
      return matching.length
        ? <mark key={start} data-active={matching.some(span => span.id === activeId)}
            className="border-b-2 border-ai bg-ai-highlight text-foreground data-[active=true]:bg-ai-subtle data-[active=true]:font-semibold">{text}</mark>
        : <span key={start}>{text}</span>;
    })}
  </div>;
}
