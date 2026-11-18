import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useFetched } from './useFetched';

beforeEach(() => vi.useFakeTimers());

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

/** A request the test settles by hand. */
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (cause: Error) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

/** Lets timers of 0 ms and settled promises run. */
const flush = () => act(async () => { await vi.advanceTimersByTimeAsync(0); });

describe('useFetched', () => {
  it('loads on mount and counts each successful load', async () => {
    const load = vi.fn().mockResolvedValue('first');
    const { result, rerender } = renderHook(({ dep }) => useFetched(load, [dep]), {
      initialProps: { dep: 1 },
    });
    expect(result.current).toEqual({ data: null, error: null, loading: true, version: 0 });

    await flush();
    expect(result.current).toEqual({ data: 'first', error: null, loading: false, version: 1 });

    load.mockResolvedValue('second');
    rerender({ dep: 2 });
    await flush();
    expect(result.current.data).toBe('second');
    expect(result.current.version).toBe(2);
  });

  it('discards a response that arrives after a newer request started', async () => {
    const slow = deferred<string>();
    const fast = deferred<string>();
    const load = vi.fn().mockReturnValueOnce(slow.promise).mockReturnValueOnce(fast.promise);
    const { result, rerender } = renderHook(({ dep }) => useFetched(load, [dep]), {
      initialProps: { dep: 'old' },
    });
    await flush();
    rerender({ dep: 'new' });
    await flush();

    await act(async () => fast.resolve('answer for new'));
    await act(async () => slow.resolve('answer for old'));

    expect(load).toHaveBeenCalledTimes(2);
    expect(load.mock.calls[0][0].aborted).toBe(true);
    expect(result.current.data).toBe('answer for new');
    expect(result.current.version).toBe(1);
  });

  it('debounces: changes inside the delay produce a single request', async () => {
    const load = vi.fn().mockResolvedValue('done');
    const { rerender } = renderHook(({ dep }) => useFetched(load, [dep], { delayMs: 250 }), {
      initialProps: { dep: 'c' },
    });

    await act(async () => { await vi.advanceTimersByTimeAsync(249); });
    expect(load).not.toHaveBeenCalled();
    rerender({ dep: 'co' });
    await act(async () => { await vi.advanceTimersByTimeAsync(249); });
    expect(load).not.toHaveBeenCalled();

    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(load).toHaveBeenCalledTimes(1);
  });

  it('clears the data when a load fails, so a wrong answer is not left on screen', async () => {
    const load = vi.fn().mockResolvedValueOnce('good').mockRejectedValueOnce(new Error('HTTP 502'));
    const { result, rerender } = renderHook(({ dep }) => useFetched(load, [dep]), {
      initialProps: { dep: 1 },
    });
    await flush();
    rerender({ dep: 2 });
    await flush();

    expect(result.current).toEqual({ data: null, error: 'HTTP 502', loading: false, version: 1 });
  });

  it('can keep the last good data when a reload fails, and recovers on the next success', async () => {
    const load = vi.fn()
      .mockResolvedValueOnce('good')
      .mockRejectedValueOnce(new Error('HTTP 502'))
      .mockResolvedValueOnce('fresh');
    const { result, rerender } = renderHook(
      ({ dep }) => useFetched(load, [dep], { keepDataOnError: true }),
      { initialProps: { dep: 1 } },
    );
    await flush();
    rerender({ dep: 2 });
    await flush();
    expect(result.current).toEqual({ data: 'good', error: 'HTTP 502', loading: false, version: 1 });

    rerender({ dep: 3 });
    await flush();
    expect(result.current).toEqual({ data: 'fresh', error: null, loading: false, version: 2 });
  });

  it('does nothing without a loader and ignores a response after unmount', async () => {
    const idle = renderHook(() => useFetched<string>(null, []));
    await flush();
    expect(idle.result.current.data).toBeNull();

    const pending = deferred<string>();
    const load = vi.fn().mockReturnValue(pending.promise);
    const { result, unmount } = renderHook(() => useFetched(load, []));
    await flush();
    unmount();
    await act(async () => pending.resolve('late'));
    expect(result.current.data).toBeNull();
  });
});
