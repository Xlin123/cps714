import { useEffect, useState } from 'react';
import { fetchDemoAccounts } from '../auth/api';
import type { DemoAccount } from '../auth/api';

/** Renders one fill-in button per demo account; renders nothing when demo is off. */
export function DemoAccountButtons({ onPick }: { onPick: (account: DemoAccount) => void }) {
  const [accounts, setAccounts] = useState<DemoAccount[]>([]);

  useEffect(() => {
    let isCancelled = false;
    fetchDemoAccounts().then((found) => {
      if (!isCancelled) setAccounts(found);
    });
    return () => {
      isCancelled = true;
    };
  }, []);

  if (accounts.length === 0) return null;
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
