# RiskAnalysisPanel - Manual Test Cases

## Test Case 1: No Holdings Data (Show Unknown)

**Setup:**
- Have investment accounts with balances but no holdings data
- Example: Chase Bank Brokerage with $45,680.25 balance, 0 holdings

**Expected Results:**
- ✅ Diversification Score shows "Unknown"
- ✅ Diversification Score help text shows "No holdings data"
- ✅ Progress bar is hidden
- ✅ Holdings count is hidden
- ✅ Top Concentrations shows "Unknown"
- ✅ Top Concentrations shows "No holdings data available"

**Actual Results:**
- [ ] Verified on: ___________

---

## Test Case 2: With Holdings Data (Show Calculated Values)

**Setup:**
- Have investment accounts with holdings data
- Example: Brokerage with VTI ($20,000), AAPL ($15,000)

**Expected Results:**
- ✅ Diversification Score shows calculated number (e.g., "42")
- ✅ Diversification Score help text shows "out of 100"
- ✅ Progress bar is visible with appropriate color
- ✅ Holdings count shows "2 holdings"
- ✅ Top Concentrations shows either:
   - Concentration warnings if any holding > 20% OR
   - "✓ No excessive concentrations" if all holdings < 20%

**Actual Results:**
- [ ] Verified on: ___________

---

## Test Case 3: Mixed Scenario

**Setup:**
- Some accounts with holdings, some without
- Example: 401k with holdings + Brokerage without holdings

**Expected Results:**
- ✅ Diversification Score calculated based on available holdings only
- ✅ Progress bar visible
- ✅ Holdings count reflects only accounts with holdings
- ✅ Top Concentrations calculated from available holdings

**Actual Results:**
- [ ] Verified on: ___________

---

## Test Case 4: Edge Case - All Holdings Below 20%

**Setup:**
- Multiple holdings, all individually < 20% of portfolio
- Example: 10 holdings at ~10% each

**Expected Results:**
- ✅ Top Concentrations shows "✓ No excessive concentrations"
- ✅ Message shows "All holdings are below 20% of portfolio"

**Actual Results:**
- [ ] Verified on: ___________

---

## Test Case 5: Edge Case - Single Large Holding

**Setup:**
- One holding > 20% of portfolio
- Example: AAPL at $50,000 out of $100,000 total (50%)

**Expected Results:**
- ✅ Top Concentrations shows warning alert
- ✅ Holding listed with orange badge showing percentage
- ✅ Alert text: "These holdings each represent more than 20% of your portfolio"

**Actual Results:**
- [ ] Verified on: ___________

---

## Related Backend Tests

Comprehensive backend tests exist in `backend/tests/unit/test_holdings_api.py`:
- `TestInvestmentAccountsWithoutHoldings::test_includes_investment_accounts_without_holdings`
- `TestInvestmentAccountsWithoutHoldings::test_treemap_with_cash_and_investment_accounts`
- `TestInvestmentAccountsWithoutHoldings::test_multiple_investment_accounts_without_holdings`
- `TestInvestmentAccountsWithoutHoldings::test_mixed_investment_accounts_with_and_without_holdings`

All backend tests **PASS** ✅
