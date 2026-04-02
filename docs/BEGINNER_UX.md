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

Four items are hidden behind an explicit **"Show advanced features"** toggle
in Preferences → Navigation:

| Path | What it contains |
|---|---|
| `/investment-tools` | FIRE, Loan Modeler, HSA Optimizer, Employer Match, What-If, Bond Ladder, Equity Comp, Tax-Equiv Yield, Asset Location, Cost Basis |
| `/pe-performance` | Private equity TVPI, DPI, MOIC, IRR, capital call history |
| `/rental-properties` | Rental income/expense tracking, net operating income per property |
| Tax Center → Charitable Giving tab | Donation tracking and taxable income reduction |

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

### Post-onboarding "what's next" banner

Once a user has ≥1 account and fewer than 5 logins, a dismissable green banner appears
on the Dashboard with 3 next-step quick-links:
- Set a goal → `/goals`
- See your tax projection → `/tax-center`
- Check your net worth → `/net-worth`

Rendered by `PostOnboardingBanner`. Dismissal stored in `nest-egg-post-onboarding-banner-dismissed`.
Hides automatically at login 5 (user is now experienced).

### Accounts page empty state

When no accounts exist, the Accounts page shows a rich 3-card explanatory grid:
- **Checking & Savings** — explains cash flow tracking
- **Investments & Retirement** — explains 401(k), IRA, net worth
- **Loans & Liabilities** — explains DTI, mortgage, payoff timeline

The primary "Add Account" CTA appears above the cards for users who don't need the explanation.

### Dashboard: Customize hidden in Simple Mode

The "Customize" (Edit Layout) button is hidden when `showAdvancedNav = false`.
A muted hint text tells beginners: "Customize your dashboard layout in Advanced mode (Preferences)."
The Refresh button is always visible — it's universally useful.

### User menu Preferences badge

For users with ≤ 5 logins, the "My Preferences" item in the user menu shows a
"Setup" badge (blue, subtle) and a subtitle: "Simple / Advanced mode, display".
This guides new users to the toggle they need to unlock advanced features.

### Nav dropdown label tooltips

The three dropdown labels have hover tooltips (openDelay=400):
- **Spending** — "Track where your money goes — transactions, budgets, categories, and recurring bills"
- **Analytics** — "Charts and scores — net worth over time, cash flow, spending trends, and financial health"
- **Planning** — "Your financial future — goals, retirement, tax strategy, and life milestones"

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

Reads `buildConditionalDefaults` output and applies it via `filterVisible`.
Items are returned as `{ ...item, locked: true, lockedTooltip }` when `getNavState` returns `"locked"`
and `showLockedNav = true` (default). The `NavDropdown` renders locked items at 45% opacity
with a `LockIcon` prefix and a tooltip explaining the unlock condition.

Advanced items checked against `showAdvancedNav` toggle (`nest-egg-show-advanced-nav` localStorage key).

### `PreferencesPage.tsx`

- Shows per-item on/off toggles (uses `isItemOn` with `conditionalDefaults`)
- "Show advanced features" master toggle writes `/investment-tools` and `/pe-performance` to the overrides store
- Per-item toggle changes set `pendingReload = true`; Apply button triggers reload
- "Reset to defaults" clears all overrides and reloads

### Test coverage

- `navPreferences.test.ts` — 61 tests covering isItemOn, isNavVisible, toggleAdvanced, reset, NAV_SECTIONS structure
- `navConsolidation.test.ts` — 28 tests covering hub paths, conditionalDefaults, filterVisible
- `navVisibility.test.ts` — 62 tests covering buildConditionalDefaults, account gating, override priority
- `lockedNavIndicator.test.ts` — 13 tests covering getLockedNavTooltip, filterVisible locked/visible/hidden states, advanced gating, user override precedence
- `taxCenterTooltips.test.ts` — 17 tests covering tab tooltip coverage, plain-language rules, tab-index offset for hidden Charitable Giving tab
- `accountsEmptyState.test.ts` — 11 tests covering empty state render condition and 3-card content
- `postOnboardingBanner.test.ts` — 15 tests covering show/hide conditions and next-step nav targets
- `navDropdownTooltips.test.ts` — 6 tests covering Spending/Analytics/Planning label tooltip content
- `dashboardSimpleMode.test.ts` — 7 tests covering Customize button visibility and hint text
- `userMenuPreferencesBadge.test.ts` — 6 tests covering Setup badge show/hide by login count
- `pageSubtitles.test.ts` — 14 tests covering CashFlow subtitle/tooltips, Preferences advanced description, Rules page copy
- `retirementBeginnerUX.test.ts` — 21 tests covering ScenarioPanel helper text (M), RetirementPage intro banner (N), success rate badge (O)
- `beginnerJargonFixes.test.ts` — 17 tests covering Transactions Pending tooltip + empty state (P), BudgetCard rollover tooltip + overage label (Q), SmartInsights rewording + category tooltips (R)
- `beginnerDefinitions.test.ts` — 19 tests covering Net Worth/Assets/Liabilities tooltips (S), FinancialRatios score scale + entry prompt (T), DebtPayoff strategy badge labels (U)

---

## Retirement — Beginner UX

The Retirement page is the most technically complex page in the app. Three targeted improvements reduce first-visit overwhelm:

### M — ScenarioPanel Return Assumptions helper text

A plain-English guidance block appears directly under the "Return Assumptions" heading:
> "Not sure what to enter? The defaults (7% pre-retirement, 5% post-retirement, 15% volatility) are reasonable starting points based on historical stock market averages. You can always adjust later."

Tooltips on Pre-Retirement Return and Volatility sliders also explain _why_ the defaults are what they are (e.g., 7% accounts for inflation and fees; 15% is typical for a stock-heavy portfolio).

### N — RetirementPage intro banner

A dismissable blue info banner appears at the top of the page the first time a user visits. It explains:
- What Monte Carlo simulation is (1,000 random-market runs)
- What the success rate means (how often money lasts to planning age)
- That 80%+ is generally considered solid
- That defaults are reasonable starting points

Dismissal stored in `nest-egg-retirement-intro-dismissed` (localStorage).

### O — Success rate "Is this good?" badge

A color-coded `<Badge>` appears next to the success rate percentage in the Simulation Summary box:

| Success rate | Badge color | Label |
|---|---|---|
| ≥ 80% | green | Good |
| 60–79% | yellow | Moderate |
| < 60% | red | Needs attention |

Each badge has a tooltip explaining the threshold in plain language.

---

## Core Financial Term Definitions

### S — Net Worth Timeline: stat card tooltips

All three stat card labels now have plain-language tooltips:

| Label | Tooltip |
|---|---|
| **Net Worth** | "Everything you own minus everything you owe. As your savings grow and debts shrink, this number goes up." |
| **Total Assets** | "Everything you own that has value — bank accounts, investments, real estate, and retirement accounts." |
| **Total Liabilities** | "Everything you owe — credit card balances, loans, mortgages. Reducing liabilities directly increases your net worth." |

### T — Financial Health: score scale + targeted entry prompt

The **overall letter grade** (A–F) now has a tooltip explaining the scale:
> "A = 90–100 (excellent) · B = 80–89 (good) · C = 70–79 (fair) · D = 60–69 (needs work) · F = below 60 (at risk). Higher is better."

The **"enter income/spending" alert** is now specific about what each input unlocks:
- Both missing → "Enter your monthly income and spending above to unlock your savings rate, debt-to-income ratio, and overall health score."
- Income missing only → "Enter your monthly income above to unlock your savings rate and debt-to-income ratio."
- Spending missing only → "Enter your monthly spending above to complete your savings rate calculation."

### U — Debt Payoff: plain-English strategy badges

The recommendation badges on the Snowball and Avalanche strategy cards now use plain language with explanatory tooltips:

| Old label | New label | Tooltip |
|---|---|---|
| **Best Psychology** | **Best for Motivation** | "Recommended if motivation matters — quick early wins make it easier to stick with the plan, even if total interest is slightly higher." |
| **Best Savings** | **Saves Most Interest** | "Recommended if saving money is the priority — pays the least interest overall, though the first payoff may take longer." |

---

## Jargon & Empty State Fixes

### P — Transactions: "Pending" explained + smart empty state

The orange "Pending" badge on transaction rows now has a tooltip:
> "This transaction has been initiated but not yet fully processed by your bank. Pending transactions may still be adjusted or cancelled."

The empty state now distinguishes three cases:
- Search query active → "Try adjusting your search query."
- No accounts → "Connect your accounts to start tracking transactions." + Go to Accounts CTA
- Accounts exist but filters returned nothing → "No transactions match your current filters. Try expanding the date range or clearing your filters."

### Q — BudgetCard: overage amount + rollover explanation

**Over budget label** now shows the dollar amount: "Over budget by $200" instead of just "Over budget".

**Rollover line** is wrapped in a Tooltip:
> "Unused budget from the previous period carried forward into this one — it increases your available budget for this period."

### R — Smart Insights: clearer empty state + category tooltips

**"All clear!" empty state** replaced with:
> "Looking good — no action items right now."
> "Insights appear automatically when our analysis detects an opportunity — like a high-fee fund, a savings gap, or a tax move."

**Category filter pills** (Cash, Investing, Tax, Retirement) now have `openDelay=400` tooltips:
- **Cash** — "Liquid savings, emergency fund coverage, and cash management"
- **Investing** — "Portfolio allocation, fees, diversification, and investment gaps"
- **Tax** — "Tax optimization opportunities, deductions, and tax-efficient strategies"
- **Retirement** — "Retirement readiness, contribution gaps, and long-term savings pace"

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
