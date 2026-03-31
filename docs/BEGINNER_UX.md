# Beginner UX — Progressive Disclosure System

Nest Egg serves both first-time personal finance users and experienced investors.
This document describes the progressive disclosure strategy that prevents day-one overwhelm
while keeping advanced features accessible to power users.

---

## Core Principle

> **Show the right tool at the right time.**
> Don't show a bond ladder builder to someone who just signed up.

Navigation visibility is gated by what the user actually has, not what they might want someday.

---

## Day-One View (Zero Accounts)

When a brand-new user opens Nest Egg, they see **four items only**:

| Item | Why always visible |
|---|---|
| Overview | The landing page — everyone needs a home |
| Calendar | Shows upcoming bills/events at a glance |
| Investments | Core portfolio view |
| Accounts | Where they add their first account |

Everything else is **locked** until they add an account.

---

## After First Account — Progressive Unlocking

Once any account exists, nearly all non-advanced items unlock automatically.
A few require a specific account type:

| Path | Unlocking condition |
|---|---|
| `/transactions`, `/budgets`, `/categories` | Any account |
| `/cash-flow`, `/net-worth-timeline`, `/reports` | Any account |
| `/smart-insights`, `/financial-health` | Any account |
| `/goals`, `/retirement`, `/financial-plan` | Any account |
| `/tax-center`, `/life-planning` | Any account |
| `/recurring-bills` | Linked (Plaid) bank account |
| `/rental-properties` | Rental property account |
| `/debt-payoff` | Credit card, loan, or mortgage account |
| `/mortgage` | Mortgage account |
| `/education` | 529 account |

---

## Advanced Features — Opt-In Only

Two pages are hidden behind an explicit **"Show advanced features"** toggle
in Preferences → Navigation:

| Path | What it contains |
|---|---|
| `/investment-tools` | FIRE, Loan Modeler, HSA Optimizer, Employer Match, What-If, Bond Ladder, Equity Comp, Tax-Equiv Yield, Asset Location, Cost Basis |
| `/pe-performance` | Private equity TVPI, DPI, MOIC, IRR, capital call history |

These are gated separately from the account-based progressive disclosure.
Individual items can also be toggled on/off without the master toggle.

---

## Navigation Structure & Naming

### Renaming decisions

| Old Name | Current Name | Why |
|---|---|---|
| My Dashboard (Planning nav) | *(removed)* | Duplicated Overview. Health score available as a dashboard widget. |
| Retirement Planner | Retirement | Shorter, clearer. |
| Retirement & Benefits | Life Planning | Avoids confusion with Retirement Planner. Describes SS, RMDs, estate, insurance. |
| Smart Insights (standalone nav) | Recommendations (tab in Financial Checkup) | Insights belong inside a health checkup, not as a separate destination. |
| Financial Plan | My Dashboard | "Financial Plan" overlapped with Goals and Retirement. |
| Planning Tools | Calculators | "Tools" is vague. "Calculators" is what they literally are. |
| Financial Health | Financial Checkup | Checkup implies actionable diagnosis, not just metrics. |
| Categories & Labels | Spending Categories | Plain language. |

### Nav groups (current)

```
Top Level (always visible)
  Overview · Calendar · Investments · Accounts

Spending (unlocked by any account)
  Transactions · Budgets · Spending Categories
  Recurring & Bills (linked account) · Rules

Analytics (unlocked by any account)
  Cash Flow · Net Worth Timeline · Reports & Trends
  Financial Checkup (includes Recommendations tab)
  PE Performance (private equity accounts only)
  Rental Properties (rental account only)

Planning (progressive unlock)
  Goals · Retirement              ← beginner-first order
  Debt Payoff (debt) · Mortgage · Education (529)
  Tax Center · Life Planning      ← consolidated hubs
  Calculators (advanced)
```

### Hub pages

**Tax Center** (`/tax-center`)
- Tax Projection · Tax Buckets · Charitable Giving

**Life Planning** (`/life-planning`)
- SS Optimizer · Variable Income · Estate & Beneficiaries
- RMD Planner · Insurance Audit · Pension Modeler

**Financial Checkup** (`/financial-health`)
- Financial Ratios · Liquidity & Emergency Fund · Credit Score · Recommendations

**Calculators** (`/investment-tools`)
- Approachable first: FIRE · Loan Modeler · HSA Optimizer · Employer Match · What-If
- Advanced last: Bond Ladder · Equity Compensation · Tax-Equiv Yield · Asset Location · Cost Basis

### Simple Mode banner

New users (login_count ≤ 3) see a dismissable blue banner on the Overview page:
> "You're in Simple Mode. Advanced features unlock as you add accounts and enable them in Preferences."

Rendered by `BeginnerModeBanner`, dismissal stored in `nest-egg-beginner-banner-dismissed` (localStorage).

### Recommendations tab preference

On by default. Users can toggle it off in Preferences > Navigation > "Show Recommendations tab".
Stored in `nest-egg-show-recommendations-tab` (localStorage).

## Locked Nav Behavior

When `show_locked_nav = true` (default), locked items are shown **dimmed** with a tooltip:

- "Add an account to unlock"
- "Connect a bank account to unlock" (Plaid-gated items)
- "Add a mortgage account to unlock"
- etc.

When `show_locked_nav = false`, locked items are hidden entirely.
This preference lives in localStorage as `show_locked_nav`.

---

## Implementation

### `useNavDefaults.ts`

Central source of truth:
- `NAV_SECTIONS` — canonical nav structure (labels, paths, flags)
- `buildConditionalDefaults(accounts)` — returns `Record<string, boolean>` per-path visibility
- `getLockedNavTooltip(path)` — tooltip text for locked items
- `useNavDefaults(...)` — hook that fetches accounts + profile and returns computed defaults

### `Layout.tsx`

Reads `buildConditionalDefaults` output and applies it via `filterVisible`:
```typescript
const isNavVisible = (path: string): boolean => {
  if (path in navOverridesState) return navOverridesState[path];
  return conditionalDefaults[path] ?? true;
};
```

Advanced items also checked against `showAdvancedNav` toggle.

### `PreferencesPage.tsx`

- Shows per-item on/off toggles (uses `isItemOn` with `conditionalDefaults`)
- "Show advanced features" master toggle writes `/investment-tools` and `/pe-performance` to the overrides store
- Per-item toggle changes set `pendingReload = true`; Apply button triggers reload
- "Reset to defaults" clears all overrides and reloads

### Test coverage

- `navPreferences.test.ts` — 61 tests covering isItemOn, isNavVisible, toggleAdvanced, reset, NAV_SECTIONS structure
- `navConsolidation.test.ts` — 28 tests covering hub paths, conditionalDefaults, filterVisible
- `navVisibility.test.ts` — 62 tests covering buildConditionalDefaults, account gating, override priority

---

## Savings Goals — Beginner UX Design

The Savings Goals page (`/goals`) is often the first planning feature a new user tries.
Every element is designed to work equally well for a first-timer and a power user.

---

### Plain-language form fields

Every field in the goal creation/edit form has a `FormHelperText` with a plain-language explanation:

| Field | Helper text |
|---|---|
| Target Amount | "How much do you want to save in total? For an emergency fund, aim for 3–6 months of living expenses." |
| Current Amount | "How much have you already set aside? Enter 0 if you're starting fresh." |
| Linked Account | "Link a savings or checking account and Nest Egg can track your progress automatically." |
| Auto-sync | "When on, your goal's current amount updates automatically whenever you visit this page — no manual entry needed." |
| Start Date | "Usually today. Used to calculate whether you're on pace." |
| Target Date | "When do you want to reach this goal? Leave blank if there's no deadline — we'll still track your progress." |
| Description | "Optional — add context like 'Europe trip 2026' or '3-month runway for job search'." |

---

### Progress card tooltips

Goal cards expose rich data that can confuse beginners without context:

| Metric | Tooltip |
|---|---|
| **On Track** badge | "You've saved enough so far to hit your target on time. Keep it up!" |
| **Behind Schedule** badge | "You're behind pace. To still reach your goal on time, aim to save $X per month." |
| **Per Month** stat | "Save $X each month to reach your goal by the target date." |
| **Days Left** stat | "N days until your target date." |
| **Overdue** stat | "This goal is past its target date." |

The "Days Left" label automatically becomes **"Overdue"** (orange) when the target date has passed,
so beginners don't need to understand a negative number.

---

### Allocation method plain labels

When multiple goals share a linked account, Nest Egg allocates the balance between them.
The technical names ("waterfall", "proportional") are replaced with plain-language button labels:

| Internal name | Button label | Tooltip |
|---|---|---|
| `waterfall` | **Top Priority First** | "Your account balance fills Goal #1 completely before moving to Goal #2. Great when one goal matters most — like an emergency fund." |
| `proportional` | **Split Evenly** | "Your balance is split across all goals at once, each getting a share based on its size. Good when all goals matter equally." |

---

### View mode labels

| Old label | New label | Tooltip |
|---|---|---|
| Priority Order | **My Priority** | "See all goals in the order you want to fund them. Drag to reorder." |
| By Account | **By Account** | "Group goals by the account they're saving toward." |

---

### Empty state personalization

The empty state description adapts based on the user's onboarding goal:

| Onboarding goal | Message |
|---|---|
| `retirement` | "You said you want to plan for retirement — start by building an emergency fund so unexpected costs don't derail your progress." |
| `investments` | "Goals work alongside your investments. Set a savings target to fund your next contribution or build a cash buffer." |
| `spending` | "You said you want to track spending — pair that with a savings goal so you know what you're saving toward each month." |
| (default) | "Set savings goals to track progress toward vacations, emergency funds, down payments, and more." |

---

### Quick-start templates

Four one-click templates remove the blank-slate problem for beginners:

| Template | What it creates |
|---|---|
| Emergency Fund | 6 × avg monthly expenses target; auto-links to highest-balance checking/savings account |
| Vacation Fund | $4,000 target, 12-month deadline |
| Home Down Payment | $60,000 target, 5-year deadline |
| Debt Payoff Reserve | 10% of total debt (min $1,000) |

Each template card has an × button that dismisses it permanently (via `localStorage`).
Templates also auto-hide once the corresponding goal type exists.

---

### Test coverage

`savingsGoalsLogic.test.ts` covers all beginner UX helpers as pure-function tests:

- Overdue label logic (`getDaysLabel`, `getDaysColor`, `getDaysDisplay`)
- On-track tooltip text (positive / behind-with-monthly / behind-without-monthly)
- Per-month tooltip text (positive required / zero required)
- Allocation method labels and tooltip content
- GoalForm helper text content for all 6 fields
- Template dismiss logic (accumulation, deduplication, visibility)
