const CURRENCY = new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD' });

/** Formats a whole number of cents as dollars, e.g. `formatCents(125)` gives "$1.25". */
export function formatCents(cents: number): string {
  return CURRENCY.format(cents / 100);
}
