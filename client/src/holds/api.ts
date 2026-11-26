import { getJson, jsonBody, send } from '../api/http';

/**
 * A member's active hold. `position` is 1 for the first in line; `is_ready`
 * means a copy is on the shelf reserved for this member.
 */
export interface Hold {
  id: number;
  book_id: number;
  book_title: string;
  placed_at: string;
  position: number;
  is_ready: boolean;
}

export interface HoldPage {
  items: Hold[];
  total: number;
}

/** Queues the signed-in member for a book whose copies are all out or reserved. */
export async function placeHold(bookId: number): Promise<Hold> {
  const res = await send(
    '/api/holds',
    jsonBody('POST', { book_id: bookId }),
    'Could not place the hold.',
  );
  return res.json();
}

/** The signed-in member's active holds, oldest first. */
export async function fetchMyHolds(): Promise<HoldPage> {
  return getJson<HoldPage>('/api/holds/mine');
}

export async function cancelHold(holdId: number): Promise<void> {
  await send(`/api/holds/${holdId}`, { method: 'DELETE' }, 'Could not cancel the hold.');
}
