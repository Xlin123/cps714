import { useEffect, useState } from 'react';

export type Area = 'staff' | 'admin';

const TITLES: Record<Area, string> = { staff: 'Staff', admin: 'Admin' };

async function fetchAreaMessage(area: Area): Promise<string> {
  const res = await fetch(`/api/${area}/area`);
  if (!res.ok) throw new Error(`GET /api/${area}/area failed with ${res.status}`);
  const body: { message: string } = await res.json();
  return body.message;
}

/** Placeholder page whose content comes from a role-guarded endpoint. */
export function AreaPage({ area }: { area: Area }) {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;
    fetchAreaMessage(area)
      .then((found) => {
        if (!isCancelled) setMessage(found);
      })
      .catch((err: unknown) => {
        if (!isCancelled) setError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      isCancelled = true;
    };
  }, [area]);

  return (
    <div className="page">
      <h1>{TITLES[area]}</h1>
      {error ? <p className="error">{error}</p> : <p>{message ?? 'Loading…'}</p>}
    </div>
  );
}
