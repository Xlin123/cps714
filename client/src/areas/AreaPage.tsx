import { getJson } from '../api/http';
import { useLoad } from '../hooks/useLoad';

export type Area = 'staff' | 'admin';

const TITLES: Record<Area, string> = { staff: 'Staff', admin: 'Admin' };

async function fetchAreaMessage(area: Area): Promise<string> {
  const body = await getJson<{ message: string }>(`/api/${area}/area`);
  return body.message;
}

/** Placeholder page whose content comes from a role-guarded endpoint. */
export function AreaPage({ area }: { area: Area }) {
  const { state } = useLoad(() => fetchAreaMessage(area), [area]);

  return (
    <div className="page">
      <h1>{TITLES[area]}</h1>
      {state.status === 'failed' ? (
        <p className="error">{state.error}</p>
      ) : (
        <p>{state.status === 'loaded' ? state.data : 'Loading…'}</p>
      )}
    </div>
  );
}
