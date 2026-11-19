import type { Evidence } from './contracts';

/** 서버와 같은 Unicode 코드포인트 좌표. 이모지의 UTF-16 길이로 자르지 않는다. */
export function preserveEvidence(before: string, after: string, evidence: Evidence[]): Evidence[] {
  const oldChars = Array.from(before), newChars = Array.from(after);
  let prefix = 0, suffix = 0;
  while (prefix < Math.min(oldChars.length, newChars.length) && oldChars[prefix] === newChars[prefix]) prefix++;
  while (suffix < Math.min(oldChars.length, newChars.length) - prefix && oldChars[oldChars.length - 1 - suffix] === newChars[newChars.length - 1 - suffix]) suffix++;
  const shift = newChars.length - oldChars.length;
  return evidence.flatMap(item => {
    const [start, end] = item.span;
    if (end <= prefix) return [item];
    if (start >= oldChars.length - suffix) return [{ ...item, span: [start + shift, end + shift] as [number, number] }];
    return [];
  });
}

export function EvidenceBody({ body, evidence }: { body: string; evidence: Evidence[] }) {
  const chars = Array.from(body);
  let position = 0;
  const parts = evidence.flatMap((item, index) => {
    const [start, end] = item.span;
    if (start < position || end > chars.length || end <= start) return [];
    const before = chars.slice(position, start).join('');
    position = end;
    return [before, <span key={index} data-source={item.source} className="underline decoration-ai-border decoration-2 underline-offset-4">{chars.slice(start, end).join('')}</span>];
  });
  return <>{parts}{chars.slice(position).join('')}</>;
}
