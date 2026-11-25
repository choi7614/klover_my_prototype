// main 전용: 로컬 서버를 부르는 요청의 공통 뼈대.
// 토큰 헤더, 리다이렉트 금지, 캐시 금지, 시간 제한을 한 곳에서 정한다.
// 응답을 해석하는 방법(상태코드→오류 코드 등)은 기능마다 달라서 각 클라이언트에 둔다.

/** readLocalAPI가 확인해 돌려주는 주소와 토큰. */
export interface LocalTarget {
  base: URL;
  token: string;
}

export interface LocalRequestOptions {
  method: string;
  path: string;
  /** 있으면 JSON으로 보내고 Content-Type을 붙인다. */
  body?: object | null;
  timeoutMs: number;
}

/** 서버 응답 본문으로 받아들이는 최대 글자 수. 이보다 크면 잘못된 응답으로 본다. */
export const MAX_RESPONSE_CHARS = 2_000_000;

/**
 * fetch에 넘길 주소·옵션·시간 제한 신호를 만든다.
 * signal을 함께 돌려주므로 호출한 쪽이 시간 초과(signal.aborted)를 구분할 수 있다.
 */
export function localRequest(
  local: LocalTarget,
  { method, path, body, timeoutMs }: LocalRequestOptions,
): { url: URL; init: RequestInit; signal: AbortSignal } {
  const signal = AbortSignal.timeout(timeoutMs);
  return {
    url: new URL(path, local.base),
    signal,
    init: {
      method,
      headers: {
        Authorization: `Bearer ${local.token}`,
        Accept: 'application/json',
        ...(body ? { 'Content-Type': 'application/json' } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      redirect: 'error',
      cache: 'no-store',
      signal,
    },
  };
}
