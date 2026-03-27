# Navigation Structure

Intended nav layout with consolidation notes.

## Top Level
- Overview (`/overview`) — always visible
- Calendar (`/calendar`) — always visible
- Investments (`/investments`) — always visible
- Accounts (`/accounts`) — always visible

## Spending
- Transactions (`/transactions`)
- Budgets (`/budgets`)
- Categories & Labels (`/categories`)
- Recurring & Bills (`/recurring-bills`) — conditional: linked bank account
- Rules (`/rules`) — conditional: any account

## Analytics
- Cash Flow (`/income-expenses`)
- Net Worth Timeline (`/net-worth-timeline`)
- Trends (`/trends`)
- Reports (`/reports`)
- Year in Review (`/year-in-review`)
- Tax Deductible (`/tax-deductible`) — conditional: investments or rental
- Rental Properties (`/rental-properties`) — conditional: rental property account
- Smart Insights (`/smart-insights`)
- Financial Health (`/financial-health`)

## Planning
- Goals (`/goals`)
- Retirement (`/retirement`) — hub containing SS claiming, pension modeler
- Education (`/education`) — conditional: 529 account
- Debt Payoff (`/debt-payoff`) — conditional: debt accounts
- Mortgage (`/mortgage`) — conditional: mortgage account

## Tax Center (`/tax-center`) — hub
Contains: Tax projection, tax buckets, Roth conversion, backdoor Roth, IRMAA, tax-equivalent yield, contribution headroom, charitable giving, cost basis aging, TLH harvest ledger

## Life Planning (`/life-planning`) — hub
Contains: Social Security claiming strategy, estate planning, variable income, insurance audit + policies

## Planning Tools (`/investment-tools`) — advanced hub
Contains: FIRE calculator, equity compensation (RSU/ISO/NSO/ESPP), rebalancing, loan modeler, stress test, asset location, capital gains harvesting

## Consolidation Notes
- All tax-related items live under Tax Center (not scattered in Planning Tools)
- Retirement is a separate hub from Life Planning: Retirement = accumulation/drawdown, Life Planning = protection/estate
- Bond ladder (when built) should go under Planning Tools or Tax Center depending on whether it's optimization or a standalone tool
- Insurance audit + policy tracking lives under Life Planning
