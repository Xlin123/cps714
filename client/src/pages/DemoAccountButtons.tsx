import { fetchDemoAccounts } from '../auth/api';
import { useLoad } from '../hooks/useLoad';
import type { DemoAccount } from '../auth/api';

/** Renders one fill-in button per demo account; renders nothing when demo is off. */
export function DemoAccountButtons({ onPick }: { onPick: (account: DemoAccount) => void }) {
  const { state } = useLoad(fetchDemoAccounts, []);

  // The buttons are a convenience; if they can't load, the form still works.
  if (state.status !== 'loaded' || state.data.length === 0) return null;
  const accounts = state.data;
  return (
    <div className="demo-accounts">
      <p>Test accounts:</p>
      {accounts.map((account) => (
        <button key={account.role} type="button" onClick={() => onPick(account)}>
          {account.role}
        </button>
      ))}
    </div>
  );
}
