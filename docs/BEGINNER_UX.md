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

### Why we renamed things

| Old Name | New Name | Why |
|---|---|---|
| Financial Plan | My Dashboard | "Financial Plan" overlapped with Goals and Retirement. Dashboard is concrete. |
| Planning Tools | Calculators | "Tools" is vague. "Calculators" is what they literally are. |
| Life Planning | Retirement & Benefits | Concrete — describes SS, RMDs, pensions, insurance. |
| Financial Health | Financial Checkup | Checkup implies actionable diagnosis, not just metrics. |
| Categories & Labels | Spending Categories | Plain language. |

### Nav groups

```
Top Level (always visible)
  Overview · Calendar · Investments · Accounts

Spending (unlocked by any account)
  Transactions · Budgets · Spending Categories
  Recurring & Bills (linked account) · Rules

Analytics (unlocked by any account)
  Cash Flow · Net Worth Timeline · Reports & Trends
  Smart Insights · Financial Checkup
  Rental Properties (rental account only)

Planning (progressive unlock)
  Goals → Retirement Planner → My Dashboard    ← beginner-first order
  Debt Payoff (debt accounts) · Mortgage · Education (529)
  Tax Center · Retirement & Benefits            ← consolidated hubs
  Calculators (advanced) · PE Performance (advanced)
```

### Hub pages

Three previously separate pages are now **consolidated hubs** with tabs:

**Tax Center** (`/tax-center`)
- Tax Projection · Tax Buckets · Charitable Giving

**Retirement & Benefits** (`/life-planning`)
- SS Optimizer · Variable Income · Estate & Beneficiaries
- RMD Planner · Insurance Audit · Pension Modeler

**Calculators** (`/investment-tools`)
- Approachable first: FIRE · Loan Modeler · HSA Optimizer · Employer Match · What-If
- Advanced last: Bond Ladder · Equity Compensation · Tax-Equiv Yield · Asset Location · Cost Basis

---

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
