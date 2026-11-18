import { useCallback, useEffect, useRef, useState } from 'react';
import type { SearchHit, StreamedResult, StreamSummary } from '../types/lexstream';

export interface ArrivedHit {
  hit: SearchHit;
  position: number;
  /** Milliseconds between pressing the button and this ruling reaching the browser. */
  arrivedMs: number;
}

export interface SearchStreamState {
  status: 'idle' | 'streaming' | 'done' | 'error';
  hits: ArrivedHit[];
  /** Matches announced by the server, known from the first event. */
  expected: number | null;
  summary: StreamSummary | null;
}

const IDLE: SearchStreamState = { status: 'idle', hits: [], expected: null, summary: null };

/**
 * Progressive search over Server-Sent Events: one `result` event per ruling,
 * then a final `analytics_summary`.
 *
 * The stream is finite. EventSource would treat its end as a dropped
 * connection and ask again, replaying every ruling, so the source is closed on
 * the summary and on the first error.
 */
export function useSearchStream() {
  const [state, setState] = useState<SearchStreamState>(IDLE);
  const source = useRef<EventSource | null>(null);

  const close = useCallback(() => {
    source.current?.close();
    source.current = null;
  }, []);

  const cancel = useCallback(() => {
    close();
    setState(IDLE);
  }, [close]);

  const start = useCallback(
    (url: string) => {
      close();
      const started = performance.now();
      const stream = new EventSource(url);
      source.current = stream;
      setState({ ...IDLE, status: 'streaming' });

      stream.addEventListener('result', ((event: MessageEvent<string>) => {
        if (source.current !== stream) return; // a newer search replaced this one
        const result = JSON.parse(event.data) as StreamedResult;
        const arrived: ArrivedHit = {
          hit: result.hit,
          position: result.position,
          arrivedMs: Math.round(performance.now() - started),
        };
        setState((current) => ({
          ...current,
          expected: result.total,
          hits: [...current.hits, arrived],
        }));
      }) as EventListener);

      stream.addEventListener('analytics_summary', ((event: MessageEvent<string>) => {
        if (source.current !== stream) return;
        const summary = JSON.parse(event.data) as StreamSummary;
        close();
        setState((current) => ({ ...current, status: 'done', expected: summary.total, summary }));
      }) as EventListener);

      stream.onerror = () => {
        if (source.current !== stream) return;
        close();
        setState((current) => ({ ...current, status: 'error' }));
      };
    },
    [close],
  );

  useEffect(() => close, [close]);

  return { state, start, cancel };
}
