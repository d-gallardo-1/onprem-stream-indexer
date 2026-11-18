import { useEffect, useState } from 'react';

export interface Fetched<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  /** Counts successful loads, so a caller can react to each one. */
  version: number;
}

export interface FetchOptions {
  /** Wait this long after the last change before asking; debounces typing. */
  delayMs?: number;
  /**
   * Keep the last good value when a reload fails. For data that stays valid
   * across reloads (the tenant list); not for answers to a query, where a
   * stale answer under a new question would mislead.
   */
  keepDataOnError?: boolean;
}

/**
 * Loads a value and reloads it whenever `deps` change. A response that arrives
 * after a newer request started is discarded, so a slow answer for a previous
 * tenant or query can never replace the current one.
 */
export function useFetched<T>(
  load: ((signal: AbortSignal) => Promise<T>) | null,
  deps: readonly unknown[],
  { delayMs = 0, keepDataOnError = false }: FetchOptions = {},
): Fetched<T> {
  const [state, setState] = useState<Fetched<T>>({
    data: null,
    error: null,
    loading: true,
    version: 0,
  });

  useEffect(() => {
    if (!load) return undefined;
    const controller = new AbortController();
    setState((current) => ({ ...current, loading: true }));
    const timer = window.setTimeout(() => {
      load(controller.signal)
        .then((data) => {
          if (controller.signal.aborted) return;
          setState((current) => ({
            data,
            error: null,
            loading: false,
            version: current.version + 1,
          }));
        })
        .catch((cause: unknown) => {
          if (controller.signal.aborted) return;
          const error = cause instanceof Error ? cause.message : 'Request failed';
          setState((current) => ({
            ...current,
            data: keepDataOnError ? current.data : null,
            error,
            loading: false,
          }));
        });
    }, delayMs);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
    // The caller lists what the request depends on; `load` is rebuilt every render.
  }, deps);

  return state;
}
