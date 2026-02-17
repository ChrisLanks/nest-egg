# Teller API Integration

## Why Teller?

**🆓 100 FREE accounts/month in production!**
- After 100: Only $1/account/month (half the price of Plaid's $2+)
- No sandbox complexity - real connections from day 1
- Clean, simple API
- Great for personal projects and startups

## Teller vs Plaid Feature Comparison

| Feature | Teller | Plaid | Notes |
|---------|--------|-------|-------|
| **Pricing** | 100 FREE/mo, then $1/account | ~$0.50-$2/account | Teller wins for small apps |
| **Bank Coverage** | 5,000+ US banks | 11,000+ institutions | Plaid has broader coverage |
| **Account Types** | ✅ Checking, Savings, Credit | ✅ All types | Both support main types |
| **Transactions** | ✅ Full history | ✅ Full history | Feature parity |
| **Balances** | ✅ Real-time | ✅ Real-time | Feature parity |
| **Identity** | ✅ Account holder info | ✅ Full identity | Both support |
| **Webhooks** | ✅ Real-time updates | ✅ Real-time updates | Feature parity |
| **Investments** | ❌ Limited | ✅ Full support | Plaid better for investments |
| **Liabilities** | ✅ Loans, Credit Cards | ✅ Full support | Feature parity |
| **Sandbox** | Production only | Full sandbox | Teller uses real connections |
| **Setup Complexity** | ⭐⭐⭐⭐⭐ Very simple | ⭐⭐⭐ Moderate | Teller easier |

## Teller API Capabilities

### 1. Account Linking (Teller Connect)
```javascript
// User visits Teller Connect URL
https://teller.io/connect/app/{YOUR_APP_ID}

// Returns: enrollment object with access_token
{
  "enrollment": {
    "id": "enrollment_abc123",
    "institution": {
      "name": "Bank of America",
      "id": "bofa"
    },
    "accessToken": "test_token_..."
  }
}
```

### 2. Accounts API
**Endpoint:** `GET /accounts`

**Response:**
```json
[
  {
    "id": "acc_abc123",
    "enrollment_id": "enrollment_abc123",
    "name": "My Checking",
    "type": "depository",  // depository, credit, loan, investment
    "subtype": "checking",  // checking, savings, credit_card, etc.
    "status": "open",
    "institution": {
      "name": "Bank of America",
      "id": "bofa"
    },
    "last_four": "1234",
    "balance": {
      "available": "1234.56",
      "ledger": "1234.56",  // Current balance
      "limit": null  // Credit limit for credit cards
    },
    "currency": "USD"
  }
]
```

**Account Types Supported:**
- `depository`: Checking, Savings, Money Market, CD
- `credit`: Credit Cards
- `loan`: Personal Loans, Student Loans, Mortgages
- `investment`: Brokerage (limited)

### 3. Transactions API
**Endpoint:** `GET /accounts/{account_id}/transactions`

**Parameters:**
- `from_date`: ISO date (e.g., "2024-01-01")
- `to_date`: ISO date (optional)
- `count`: Number of transactions (default: 500)

**Response:**
```json
[
  {
    "id": "txn_abc123",
    "account_id": "acc_abc123",
    "date": "2024-02-15",
    "description": "STARBUCKS",
    "amount": "-5.67",  // Negative = debit, Positive = credit
    "status": "posted",  // posted or pending
    "type": "card_payment",  // card_payment, ach, wire, check, etc.
    "details": {
      "category": "Food and Drink",
      "counterparty": {
        "name": "Starbucks",
        "type": "merchant"
      },
      "processing_status": "complete"
    },
    "running_balance": "1228.89"
  }
]
```

**Transaction Types:**
- `card_payment`: Debit/credit card transactions
- `ach`: ACH transfers
- `wire`: Wire transfers
- `check`: Check deposits/payments
- `atm`: ATM withdrawals
- `fee`: Bank fees
- `interest`: Interest earned
- `dividend`: Investment dividends
- `other`: Other types

### 4. Balance Updates
**Endpoint:** `GET /accounts/{account_id}/balances`

Real-time balance information:
```json
{
  "available": "1234.56",
  "ledger": "1234.56",
  "limit": null
}
```

### 5. Account Details
**Endpoint:** `GET /accounts/{account_id}/details`

Extended account information:
```json
{
  "account_number": "****1234",  // Masked
  "routing_numbers": {
    "ach": "011000015",
    "wire": "026009593"
  }
}
```

### 6. Identity
**Endpoint:** `GET /accounts/{account_id}/identity`

Account holder information:
```json
{
  "account_id": "acc_abc123",
  "names": ["JOHN DOE"],
  "addresses": [
    {
      "street": "123 Main St",
      "city": "San Francisco",
      "state": "CA",
      "zip": "94102"
    }
  ],
  "emails": ["john@example.com"],
  "phone_numbers": ["+14155551234"]
}
```

### 7. Webhooks
**Supported Events:**
- `enrollment.connected`: New enrollment created
- `enrollment.disconnected`: User disconnected
- `account.opened`: New account detected
- `account.closed`: Account closed
- `transaction.posted`: New transaction posted
- `transaction.pending`: New pending transaction
- `balance.updated`: Balance changed

**Webhook Payload:**
```json
{
  "event": "transaction.posted",
  "payload": {
    "enrollment_id": "enrollment_abc123",
    "account_id": "acc_abc123",
    "transaction": { /* full transaction object */ }
  },
  "timestamp": "2024-02-15T10:30:00Z"
}
```

## Implementation in Nest Egg

### Backend Support

✅ **Implemented:**
- Account linking flow
- Account sync from Teller
- Transaction sync from Teller
- Automatic deduplication
- Balance tracking
- Type mapping to our AccountType enum

✅ **Planned:**
- Webhook handlers for real-time updates
- Identity data sync
- Account details sync
- Background sync jobs

### Data Quality Comparison

| Data Point | Teller Quality | Plaid Quality |
|------------|----------------|---------------|
| Account Names | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Balances | ⭐⭐⭐⭐⭐ Real-time | ⭐⭐⭐⭐⭐ Real-time |
| Transaction History | ⭐⭐⭐⭐⭐ 24 months | ⭐⭐⭐⭐⭐ 24 months |
| Merchant Names | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Excellent |
| Categories | ⭐⭐⭐ Basic | ⭐⭐⭐⭐⭐ Detailed |
| Pending Transactions | ⭐⭐⭐⭐⭐ Yes | ⭐⭐⭐⭐⭐ Yes |
| Investment Holdings | ⭐⭐ Limited | ⭐⭐⭐⭐⭐ Full support |

## Limitations

**Teller Does NOT Support:**
- ❌ Investment account holdings (positions)
- ❌ Detailed investment performance
- ❌ Multi-factor authentication details
- ❌ Plaid's 350+ transaction categories (has ~15 basic categories)

**Teller IS Great For:**
- ✅ Cash flow tracking (checking, savings, credit cards)
- ✅ Transaction history and categorization
- ✅ Debt tracking (loans, credit cards)
- ✅ Small/personal finance apps (free tier!)
- ✅ Simple, clean integration

## Recommendations

**Use Teller if:**
- You're building a personal project or startup
- You want to minimize costs (100 free accounts!)
- You primarily track cash flow and basic accounts
- You don't need detailed investment data

**Use Plaid if:**
- You need comprehensive investment tracking
- You require detailed transaction categories
- You need the broadest bank coverage
- Budget allows for higher per-account costs

**Use BOTH (Our Approach):**
- Let users choose their provider
- Teller for cash accounts (free!)
- Plaid for investment accounts
- Best of both worlds 🎉

## Getting Started with Teller

### 1. Sign Up
Visit: https://teller.io/
- Create account
- Get your Application ID
- Get your API Key

### 2. Configure Nest Egg
```bash
# .env
TELLER_APP_ID=your_app_id_here
TELLER_API_KEY=test_key_your_api_key_here
TELLER_ENV=sandbox
TELLER_ENABLED=true
```

### 3. Test Connection
```bash
curl https://api.teller.io/accounts \
  -u "test_key_your_api_key:"
```

### 4. Go Live
```bash
# Production
TELLER_ENV=production
TELLER_API_KEY=live_key_your_api_key_here
```

## API Documentation

**Official Docs:** https://teller.io/docs

**Key Endpoints:**
- Accounts: https://teller.io/docs/api/accounts
- Transactions: https://teller.io/docs/api/transactions
- Webhooks: https://teller.io/docs/api/webhooks
- Authentication: https://teller.io/docs/api/authentication

## Support

**Teller Support:**
- Documentation: https://teller.io/docs
- Email: support@teller.io
- Status: https://status.teller.io

**Nest Egg Integration:**
- See: [backend/app/services/teller_service.py](../backend/app/services/teller_service.py)
- Webhooks: [backend/app/api/v1/teller.py](../backend/app/api/v1/teller.py) (planned)

---

**Last Updated:** February 2026
**Teller API Version:** v1
