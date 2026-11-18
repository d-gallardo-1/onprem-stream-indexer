import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FakeEventSource } from '../test/fakeEventSource';
import { IND as BETA, LAW as ALPHA, makeSnapshot } from '../test/fixtures';
import { RETRY_MS, STALE_MS, useReconnects, useTenantStream } from './useTenantStream';

beforeEach(() => {
  vi.useFakeTimers();
  FakeEventSource.reset();
  vi.stubGlobal('EventSource', FakeEventSource);
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const emit = (type: string, data?: unknown) => act(() => FakeEventSource.latest.emit(type, data));
const advance = (ms: number) => act(() => vi.advanceTimersByTime(ms));

function start(tenantId: string | null = ALPHA.tenant_id) {
  return renderHook(({ id }) => useTenantStream(id), { initialProps: { id: tenantId } });
}

describe('useTenantStream', () => {
  it('opens the stream of the selected tenant and renders its snapshots', () => {
    const { result } = start();

    expect(FakeEventSource.latest.url).toBe('/api/v1/ingest/stream?tenant_id=TNT-LAW-01');
    expect(result.current).toEqual({ snapshot: null, status: 'RECONNECTING' });

    emit('snapshot', makeSnapshot(ALPHA, 10));
    emit('update', makeSnapshot(ALPHA, 11));

    expect(result.current.status).toBe('CONNECTED');
    expect(result.current.snapshot?.corpus.rulings).toBe(11);
  });

  it('does not connect until a tenant is known', () => {
    start(null);

    expect(FakeEventSource.instances).toHaveLength(0);
  });

  it('drops the old tenant at once when the tenant changes', () => {
    const { result, rerender } = start();
    emit('snapshot', makeSnapshot(ALPHA));
    const first = FakeEventSource.latest;

    rerender({ id: BETA.tenant_id });

    expect(first.readyState).toBe(FakeEventSource.CLOSED);
    expect(result.current).toEqual({ snapshot: null, status: 'RECONNECTING' });
    expect(FakeEventSource.latest.url).toBe('/api/v1/ingest/stream?tenant_id=TNT-IND-02');

    emit('snapshot', makeSnapshot(BETA));
    expect(result.current.snapshot?.tenant.tenant_id).toBe(BETA.tenant_id);
  });

  it('never renders a snapshot that belongs to another tenant', () => {
    const { result, rerender } = start();
    const first = FakeEventSource.latest;
    rerender({ id: BETA.tenant_id });

    // A late message on the closed stream, and a wrong one on the new stream.
    act(() => first.emit('update', makeSnapshot(ALPHA)));
    emit('snapshot', makeSnapshot(ALPHA));

    expect(result.current.snapshot).toBeNull();
  });

  it('reconnects by hand after the server answered with an HTTP error', () => {
    const { result } = start();
    emit('snapshot', makeSnapshot());

    act(() => FakeEventSource.latest.fail(true));
    expect(result.current.status).toBe('RECONNECTING');
    expect(FakeEventSource.instances).toHaveLength(1);

    advance(RETRY_MS);
    expect(FakeEventSource.instances).toHaveLength(2);

    emit('snapshot', makeSnapshot(ALPHA, 13));
    expect(result.current.status).toBe('CONNECTED');
    expect(result.current.snapshot?.corpus.rulings).toBe(13);
  });

  it('reports disconnected after three failures in a row and keeps the last snapshot', () => {
    const { result } = start();
    emit('snapshot', makeSnapshot());

    for (let attempt = 0; attempt < 3; attempt += 1) {
      act(() => FakeEventSource.latest.fail(true));
      advance(RETRY_MS);
    }

    expect(result.current.status).toBe('DISCONNECTED');
    expect(result.current.snapshot).not.toBeNull();
  });

  it('rebuilds a connection that went silent, and a heartbeat keeps it alive', () => {
    start();
    emit('snapshot', makeSnapshot());

    advance(STALE_MS - 1000);
    emit('heartbeat');
    advance(STALE_MS - 1000);
    expect(FakeEventSource.instances).toHaveLength(1);

    advance(1000 + RETRY_MS);
    expect(FakeEventSource.instances).toHaveLength(2);
  });

  it('closes the stream and stops its timers on unmount', () => {
    const { unmount } = start();
    const source = FakeEventSource.latest;

    unmount();
    advance(STALE_MS + RETRY_MS);

    expect(source.readyState).toBe(FakeEventSource.CLOSED);
    expect(FakeEventSource.instances).toHaveLength(1);
  });
});

describe('useReconnects', () => {
  const run = (connected: boolean, key: string | null = 'TNT-LAW-01') =>
    renderHook(({ up, id }) => useReconnects(up, id), { initialProps: { up: connected, id: key } });

  it('does not count the first connection or a drop', () => {
    const { result, rerender } = run(false);
    rerender({ up: true, id: 'TNT-LAW-01' });
    expect(result.current).toBe(0);

    rerender({ up: false, id: 'TNT-LAW-01' });
    expect(result.current).toBe(0); // losing the stream must not trigger a reload
  });

  it('counts each return of a stream that had been up', () => {
    const { result, rerender } = run(true);
    for (const up of [false, true, false, true]) rerender({ up, id: 'TNT-LAW-01' });

    expect(result.current).toBe(2);
  });

  it('starts over when the tenant changes, so a switch is not a reconnect', () => {
    const { result, rerender } = run(true);
    rerender({ up: false, id: 'TNT-IND-02' }); // the new tenant's stream is still opening
    rerender({ up: true, id: 'TNT-IND-02' });

    expect(result.current).toBe(0);
  });
});
