import { useEffect, useState } from 'react';
import type { DependencyList } from 'react';

export type LoadState<T> =
  { status: 'loading' } | { status: 'loaded'; data: T } | { status: 'failed'; error: string };

/**
 * Runs `load` on mount and whenever `deps` change, dropping results that arrive
 * after unmount or after a newer load started. The last loaded data stays shown
 * while a newer load is in flight. `reload` runs it again with the same deps.
 *
 *     const { state, reload } = useLoad(() => fetchBooks(offset), [offset]);
 */
export function useLoad<T>(load: () => Promise<T>, deps: DependencyList) {
  const [state, setState] = useState<LoadState<T>>({ status: 'loading' });
  const [generation, setGeneration] = useState(0);

  // `deps` stands in for `load`, which is a new closure on every render, so the
  // effect cannot list `load` itself.
  /* oxlint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    let isCancelled = false;
    load()
      .then((data) => {
        if (!isCancelled) setState({ status: 'loaded', data });
      })
      .catch((err: unknown) => {
        if (!isCancelled) {
          setState({ status: 'failed', error: err instanceof Error ? err.message : String(err) });
        }
      });
    return () => {
      isCancelled = true;
    };
  }, [...deps, generation]);
  /* oxlint-enable react-hooks/exhaustive-deps */

  return { state, reload: () => setGeneration((n) => n + 1) };
}
