import { useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';
import type { StreamStatus, TenantSnapshot } from '../types/lexstream';

export const RETRY_MS = 3000;
// The backend sends an update or a heartbeat event at least every 5 s. If
// nothing arrives for this long the connection is considered dead and rebuilt.
// This catches the case where a proxy keeps the browser side open after the
// backend has gone away, which EventSource alone does not report.
export const STALE_MS = 8000;
const FAILURES_BEFORE_DISCONNECTED = 3;

/**
 * Subscribes to the state stream of one tenant's partition (crawl stages, new
 * rulings, resets). Each event carries a full snapshot, so a client that
 * reconnects is consistent again after one message.
 *
 * Changing the tenant closes the stream, drops the previous tenant's snapshot
 * at once and opens a new stream, so one tenant's data is never shown under
 * another tenant's name.
 *
 * EventSource reconnects by itself after network errors, but it gives up when
 * the server answers with an HTTP error (for example a 502 while the backend
 * restarts). That case is retried manually here.
 */
export function useTenantStream(tenantId: string | null): {
  snapshot: TenantSnapshot | null;
  status: StreamStatus;
} {
  const [snapshot, setSnapshot] = useState<TenantSnapshot | null>(null);
  const [status, setStatus] = useState<StreamStatus>('RECONNECTING');

  useEffect(() => {
    setSnapshot(null);
    setStatus('RECONNECTING');
    if (!tenantId) return undefined;

    let source: EventSource | null = null;
    let retryTimer: number | undefined;
    let staleTimer: number | undefined;
    let disposed = false;
    let failures = 0;

    const recordFailure = () => {
      failures += 1;
      setStatus(failures >= FAILURES_BEFORE_DISCONNECTED ? 'DISCONNECTED' : 'RECONNECTING');
    };

    const armStaleTimer = () => {
      window.clearTimeout(staleTimer);
      staleTimer = window.setTimeout(() => {
        recordFailure();
        scheduleRetry();
      }, STALE_MS);
    };

    const scheduleRetry = () => {
      source?.close();
      // A rebuild is already on its way: the silence timer must not fire again
      // and count the same outage twice.
      window.clearTimeout(staleTimer);
      window.clearTimeout(retryTimer);
      retryTimer = window.setTimeout(connect, RETRY_MS);
    };

    const onSnapshot = (event: MessageEvent<string>) => {
      const next = JSON.parse(event.data) as TenantSnapshot;
      // Defence in depth: a snapshot for any other tenant is never rendered.
      if (disposed || next.tenant.tenant_id !== tenantId) return;
      failures = 0;
      setStatus('CONNECTED');
      setSnapshot(next);
      armStaleTimer();
    };

    function connect() {
      if (disposed || !tenantId) return;
      source = new EventSource(api.stateStreamUrl(tenantId));
      // Armed from the start: a connection that is accepted but never sends a
      // byte fires neither `open` nor `error`, and must still be given up on.
      armStaleTimer();
      source.addEventListener('snapshot', onSnapshot as EventListener);
      source.addEventListener('update', onSnapshot as EventListener);
      source.addEventListener('heartbeat', armStaleTimer);
      source.onopen = () => {
        failures = 0;
        setStatus('CONNECTED');
        armStaleTimer();
      };
      source.onerror = () => {
        recordFailure();
        if (source?.readyState === EventSource.CLOSED) {
          scheduleRetry();
        } else {
          // The browser is reconnecting by itself: give that attempt a full window.
          armStaleTimer();
        }
      };
    }

    connect();

    return () => {
      disposed = true;
      window.clearTimeout(retryTimer);
      window.clearTimeout(staleTimer);
      source?.close();
    };
  }, [tenantId]);

  return { snapshot, status };
}

/**
 * Counts how many times the stream came back after having been up. Requests
 * list it as a dependency to be repeated once the backend returns.
 *
 * It deliberately ignores the first connection, a drop, and a change of `key`
 * (the tenant). A drop must not trigger a request: that request would fail and
 * wipe the results the offline banner says are still on screen.
 */
export function useReconnects(connected: boolean, key: string | null): number {
  const [count, setCount] = useState(0);
  const seen = useRef<{ key: string | null; state: 'never' | 'up' | 'down' }>({ key, state: 'never' });

  useEffect(() => {
    if (seen.current.key !== key) {
      // In the render that changes the tenant, `connected` still describes the
      // previous tenant's stream. It is not read: the new stream reports itself
      // on the next change of the flag.
      seen.current = { key, state: 'never' };
      return;
    }
    if (connected) {
      if (seen.current.state === 'down') setCount((value) => value + 1);
      seen.current.state = 'up';
    } else if (seen.current.state === 'up') {
      seen.current.state = 'down';
    }
  }, [connected, key]);

  return count;
}
