import { useCallback, useEffect, useRef, useState } from 'react';
import type { SearchHit, StreamedResult, StreamSummary } from '../types/lexstream';

// The backend pauses about 120 ms between rulings. If nothing arrives for this
// long the stream is given up on. This catches a proxy that keeps the browser
// side open after the backend has gone away, which fires neither an event nor
// an error and would otherwise leave the button on "Streaming…" for good.
export const STALL_MS = 10_000;

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
 * the summary, on the first error, on a malformed event and on silence.
 */
export function useSearchStream() {
  const [state, setState] = useState<SearchStreamState>(IDLE);
  const source = useRef<EventSource | null>(null);
  const stallTimer = useRef<number | undefined>(undefined);

  const close = useCallback(() => {
    window.clearTimeout(stallTimer.current);
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

      const fail = () => {
        if (source.current !== stream) return; // a newer search replaced this one
        close();
        setState((current) => ({ ...current, status: 'error' }));
      };
      const armStallTimer = () => {
        window.clearTimeout(stallTimer.current);
        stallTimer.current = window.setTimeout(fail, STALL_MS);
      };
      /** Runs `handle` with the decoded event; a payload that is not JSON ends the stream. */
      const on = <T>(type: string, handle: (payload: T) => void) =>
        stream.addEventListener(type, ((event: MessageEvent<string>) => {
          if (source.current !== stream) return;
          let payload: T;
          try {
            payload = JSON.parse(event.data) as T;
          } catch {
            fail();
            return;
          }
          handle(payload);
        }) as EventListener);

      on<StreamedResult>('result', (result) => {
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
        armStallTimer();
      });

      on<StreamSummary>('analytics_summary', (summary) => {
        close();
        setState((current) => ({ ...current, status: 'done', expected: summary.total, summary }));
      });

      stream.onerror = fail;
      armStallTimer();
    },
    [close],
  );

  useEffect(() => close, [close]);

  return { state, start, cancel };
}
