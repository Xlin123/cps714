# Reports decisions

## 2026-11-25: Admin usage reports (LMS-20; #21, #75, #76)

**Context.** Admins want summary reports: loans over time and popular
titles. The tickets named `GET /api/admin/reports` and "reports page with
charts".

**Decision.**

- `GET /api/reports?weeks=` behind a new admin-only capability,
  `view_reports`. `weeks` is 1-52 (default 12), so the query and the chart
  are bounded.
- Weeks run Monday to Sunday in UTC, matching the server's clock for every
  other date. The current, partial week is the last bucket.
- Loans are grouped by day in SQL (at most 364 rows) and folded into weeks
  by a pure function, `reports.weekly_counts`, which also fills empty weeks
  with 0 so the time axis has no gaps.
- Popular titles reuse `dashboard.most_borrowed` with a start date; removed
  books are left out, as on the dashboard. Categories are ranked the same
  way, removed books included, since a category outlives its books.
- Charts are hand-built (SVG columns, CSS bars) rather than a chart library,
  to avoid a new dependency. One series per chart, so one hue (`--chart`)
  and no legend; the title names it. The colour was checked with a palette
  validator for both themes; the dark-mode UI accent failed the lightness
  band for marks, so charts use their own token. Every value is reachable
  without hovering: bars carry their value, and the weekly chart has a table
  view and a tooltip on hover and keyboard focus.

**Consequences.** Counts are by checkout date only; returns, overdue rates
and fines over time would be further series. Admins in other time zones see
UTC weeks.
