import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FakeEventSource } from '../test/fakeEventSource';
import { makeHit, makeSummary } from '../test/fixtures';
import { useSearchStream } from './useSearchStream';

const URL = '/api/v1/search/stream?tenant_id=TNT-LAW-01';
let now = 0;

beforeEach(() => {
  now = 1000;
  FakeEventSource.reset();
  vi.stubGlobal('EventSource', FakeEventSource);
  vi.spyOn(performance, 'now').mockImplementation(() => now);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const result = (position: number, total = 2) => ({
  position,
  total,
  elapsed_ms: position * 120,
  hit: makeHit({ docket_id: `SYN-LAW-2024-000${position}` }),
});

function emit(type: string, data: unknown, afterMs = 0) {
  now += afterMs;
  act(() => FakeEventSource.latest.emit(type, data));
}

describe('useSearchStream', () => {
  it('is idle until a search is started', () => {
    const { result: hook } = renderHook(() => useSearchStream());

    expect(hook.current.state).toEqual({ status: 'idle', hits: [], expected: null, summary: null });
    expect(FakeEventSource.instances).toHaveLength(0);
  });

  it('collects rulings as they arrive, with the time each one took', () => {
    const { result: hook } = renderHook(() => useSearchStream());
    act(() => hook.current.start(URL));

    expect(FakeEventSource.latest.url).toBe(URL);
    expect(hook.current.state.status).toBe('streaming');

    emit('result', result(1), 125);
    emit('result', result(2), 121);

    expect(hook.current.state.expected).toBe(2);
    expect(hook.current.state.hits.map((hit) => [hit.position, hit.arrivedMs])).toEqual([
      [1, 125],
      [2, 246],
    ]);
    expect(hook.current.state.summary).toBeNull();
  });

  it('finishes on the summary and closes the source so it is not replayed', () => {
    const { result: hook } = renderHook(() => useSearchStream());
    act(() => hook.current.start(URL));
    const source = FakeEventSource.latest;
    emit('result', result(1));

    emit('analytics_summary', makeSummary(1));

    expect(hook.current.state.status).toBe('done');
    expect(hook.current.state.summary?.analytics.rulings).toBe(1);
    expect(source.readyState).toBe(FakeEventSource.CLOSED);
    // The browser reports the end of a finite stream as an error; it changes nothing.
    act(() => source.fail(false));
    expect(hook.current.state.status).toBe('done');
    expect(FakeEventSource.instances).toHaveLength(1);
  });

  it('reports an interrupted stream and keeps what had arrived', () => {
    const { result: hook } = renderHook(() => useSearchStream());
    act(() => hook.current.start(URL));
    const source = FakeEventSource.latest;
    emit('result', result(1));

    act(() => source.fail(false));

    expect(hook.current.state.status).toBe('error');
    expect(hook.current.state.hits).toHaveLength(1);
    expect(source.readyState).toBe(FakeEventSource.CLOSED);
  });

  it('a new search replaces the running one and ignores its late events', () => {
    const { result: hook } = renderHook(() => useSearchStream());
    act(() => hook.current.start(URL));
    const first = FakeEventSource.latest;
    emit('result', result(1));

    act(() => hook.current.start(`${URL}&q=costs`));
    act(() => first.emit('result', result(2)));

    expect(first.readyState).toBe(FakeEventSource.CLOSED);
    expect(hook.current.state.hits).toEqual([]);
    expect(FakeEventSource.latest.url).toBe(`${URL}&q=costs`);
  });

  it('cancel and unmount close the source', () => {
    const { result: hook, unmount } = renderHook(() => useSearchStream());
    act(() => hook.current.start(URL));
    const first = FakeEventSource.latest;

    act(() => hook.current.cancel());
    expect(first.readyState).toBe(FakeEventSource.CLOSED);
    expect(hook.current.state.status).toBe('idle');

    act(() => hook.current.start(URL));
    const second = FakeEventSource.latest;
    unmount();
    expect(second.readyState).toBe(FakeEventSource.CLOSED);
  });
});
