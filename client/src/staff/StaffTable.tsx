import { ActionButton } from '../components/ActionButton';
import { setStaffActive } from './api';
import type { StaffMember } from './api';

/** Librarian accounts, each with an activate or deactivate action. */
export function StaffTable({ staff, onChanged }: { staff: StaffMember[]; onChanged: () => void }) {
  if (staff.length === 0) return <p>No librarian accounts yet.</p>;

  return (
    <div className="table-scroll">
      <table className="catalog">
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Email</th>
            <th scope="col">Status</th>
            <th scope="col">
              <span className="visually-hidden">Action</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {staff.map((member) => (
            <tr key={member.id}>
              <td>{member.name}</td>
              <td>{member.email}</td>
              <td className={member.is_active ? undefined : 'unavailable'}>
                {member.is_active ? 'Active' : 'Deactivated'}
              </td>
              <td>
                <ActionButton
                  label={member.is_active ? 'Deactivate' : 'Reactivate'}
                  busyLabel="Saving…"
                  accessibleLabel={`${member.is_active ? 'Deactivate' : 'Reactivate'} ${member.name}`}
                  action={async () => {
                    await setStaffActive(member.id, !member.is_active);
                    onChanged();
                  }}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
