# Access Control Model

Nest Egg uses a layered access control model built around three concepts:
**identity** (who you are), **membership** (which household you belong to),
and **role** (what you can do inside a household).  Every data endpoint is
scoped to an organisation (household), so a user from one household can never
see another household's data unless they are explicitly invited as a guest.

---

## 1. Identity — Authentication

Authentication is handled by a pluggable **IdentityProviderChain** configured
via environment variables.  The application ships with a built-in HS256 JWT
provider and out-of-the-box support for external OIDC providers.

### Built-in provider (default)

The application issues its own short-lived access tokens (HS256 JWT) signed
with `SECRET_KEY`.  This requires no external services and is the default for
self-hosted deployments.

### External OIDC providers

Set `IDENTITY_PROVIDER_CHAIN` to include one or more of:

| Provider | Key env vars | Groups claim |
|----------|-------------|-------------|
| `cognito` | `IDP_COGNITO_ISSUER`, `IDP_COGNITO_CLIENT_ID`, `IDP_COGNITO_ADMIN_GROUP` | `cognito:groups` |
| `keycloak` | `IDP_KEYCLOAK_ISSUER`, `IDP_KEYCLOAK_CLIENT_ID`, `IDP_KEYCLOAK_ADMIN_GROUP`, `IDP_KEYCLOAK_GROUPS_CLAIM` | configurable (default `groups`) |
| `okta` | `IDP_OKTA_ISSUER`, `IDP_OKTA_CLIENT_ID`, `IDP_OKTA_GROUPS_CLAIM` | configurable (default `groups`) |
| `google` | `IDP_GOOGLE_CLIENT_ID` | none (no group support) |

Example — accept both Cognito and the built-in provider:

```
IDENTITY_PROVIDER_CHAIN=cognito,builtin
IDP_COGNITO_ISSUER=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_abc123
IDP_COGNITO_CLIENT_ID=your_app_client_id
IDP_COGNITO_ADMIN_GROUP=nest-egg-admins
```

The chain tries each provider in order; the first to recognise the JWT's `iss`
claim handles validation.  A single deployment can accept tokens from multiple
IdPs simultaneously without code changes.

### How external groups map to application roles

When an external provider is used, the JWT's group claim is read on every
login.  If the user is a member of the configured `admin_group`, their
`is_org_admin` flag is set to `True`; if they leave the group their flag is
cleared on the next login.  This means Keycloak / Cognito group membership
is the **authoritative source of truth** for admin status when an external IdP
is in use — the app's local flag simply mirrors it.

For providers without group support (Google), admin status must be set
manually via `PATCH /api/v1/household/members/{user_id}/role`.

### Making endpoints provider-agnostic

Endpoints depend on `get_current_user` (or `get_organization_scoped_user` via
the router-level dependency).  Both return a plain `User` object; they do not
expose which provider validated the token.  This means:

- No endpoint code changes are needed to switch providers.
- The `X-Auth-Provider` response header shows which provider handled the
  request (useful for debugging).
- If you add a new OIDC provider, implement the `IdentityProvider` ABC in
  `app/services/identity/` and register it in `build_chain()` in
  `app/services/identity/chain.py`.

---

## 2. Membership — Organisation Scoping

Every user belongs to exactly one **organisation** (household).  All database
queries include `organization_id == current_user.organization_id`.  There is
no way for a regular authenticated user to read another household's data — the
scoping is enforced at every query in every service layer.

A user who creates an account gets a fresh organisation automatically.  Users
can join an existing household via a household invitation (see §4).

---

## 3. Roles within a household

### Member roles

| Role | Identifier | Default | Capabilities |
|------|-----------|---------|-------------|
| **Org Admin** | `user.is_org_admin = True` | No — must be promoted | Full access: invite/remove members, manage guest access, promote/demote admins, manage permission grants |
| **Regular Member** | `user.is_org_admin = False` | **Yes** | Read + write on own household data; can create permission grants to share with other members |
| **Primary Member** | `user.is_primary_household_member = True` | First user only | Same as Org Admin; cannot be removed or demoted |

**New members always join as Regular Members.**  An admin must explicitly
promote them via `PATCH /api/v1/household/members/{user_id}/role`.

### Guest roles

A user from a different household can be invited as a **guest**.  Guests
access the host household by sending `X-Household-Id: <org-uuid>` on each
request.  Their home household is untouched.

| Guest role | Identifier | Default? | Capabilities |
|-----------|-----------|---------|-------------|
| **Viewer** | `HouseholdGuest.role = "viewer"` | **Yes** (default when inviting) | Read-only on host household.  All `POST / PUT / PATCH / DELETE` requests are rejected with 403. |
| **Advisor** | `HouseholdGuest.role = "advisor"` | No | Read + write on host household (same as a regular member, but cannot manage household membership or admin operations) |

Guests are **never** household admins of the host household, even if they are
admins in their own household.

---

## 4. Invitations

### Household member invitation

1. An org admin calls `POST /api/v1/household/invite` with the target email.
2. The invitee receives a 7-day single-use code by email.
3. The invitee (authenticated as themselves) calls
   `POST /api/v1/household/accept/{code}`.
4. They join the household as a **Regular Member**.

### Guest invitation

1. An org admin calls `POST /api/v1/guest-access/invite` with the target
   email and desired role (`viewer` or `advisor`).
2. The invitee receives a 7-day single-use code.
3. They call `POST /api/v1/guest-access/accept/{code}`.
4. They are added as an active `HouseholdGuest` for the host household.
5. From then on, any request that includes `X-Household-Id: <host-org-id>`
   is automatically scoped to the host household.

---

## 5. Default access level

| Scenario | Access level |
|----------|-------------|
| Authenticated member, own household, no header | Read + write on own household |
| Authenticated member, no invitation to a foreign household | 403 if `X-Household-Id` is set to a foreign org |
| Guest (viewer), `X-Household-Id` set | **Read-only** — write attempts get 403 |
| Guest (advisor), `X-Household-Id` set | Read + write on host household |
| No valid JWT | 401 |

**The default for any new member is read + write on their own household.**
There is no concept of "read-only by default" for household members — all
members can create and modify their own data.  Read-only semantics only apply
to guests with the `viewer` role.

---

## 6. Router-level enforcement

Guest org-scoping is activated in `app/main.py` at router registration time
using FastAPI's `dependencies=` parameter:

```python
_guest_dep = [Depends(get_organization_scoped_user)]

# Guest-eligible (financial data) routers
app.include_router(accounts.router, ..., dependencies=_guest_dep)
app.include_router(transactions.router, ..., dependencies=_guest_dep)
# ... (all financial-data routers)

# Member/admin-only routers (no guest access)
app.include_router(bank_linking.router, ...)   # no _guest_dep
app.include_router(settings_router.router, ...) # no guest_dep
app.include_router(household.router, ...)       # no _guest_dep
app.include_router(permissions.router, ...)     # no _guest_dep
app.include_router(csv_import.router, ...)      # no _guest_dep
```

**Guest-eligible routers**: accounts, contributions, holdings, transactions,
labels, rules, categories, dashboard, income-expenses, notifications, budgets,
financial-templates, savings-goals, recurring-transactions, subscriptions,
transaction-splits, transaction-merges, reports, debt-payoff, rebalancing,
retirement, education, FIRE, rental-properties, tax-lots, attachments,
bulk-operations, dividend-income, tax-advisor, enhanced-trends, smart-insights,
financial-planning.

**Member-only routers**: auth, household, bank-linking, plaid, teller,
market-data, enrichment, settings, permissions, csv-import, onboarding,
guest-access, monitoring.

If a new endpoint is added to a guest-eligible router, guest org-scoping
applies automatically.  If added to a member-only router, guests are blocked
automatically because the endpoint has no `HouseholdGuest` record lookup.
If a new router is added, explicitly choose which group it belongs to.

---

## 7. Fine-grained permission grants

Within a household, members can delegate per-resource access to other members
via `PermissionGrant` objects.  This is separate from the admin/member/guest
role system and allows, for example, member A to share read access to one
specific account with member B without granting them access to everything.

Supported resource types: `account`, `transaction`, `bill`, `holding`,
`budget`, `category`, `rule`, `savings_goal`, `contribution`,
`recurring_transaction`, `report`, `org_settings`, `retirement_scenario`,
`education_plan`, `fire_plan`.

Supported actions: `read`, `create`, `update`, `delete`.

Grants are audited — every creation and revocation is recorded in
`PermissionGrantAudit` and is never deleted.

Permission grants are **not available to guests**.  Guests access data through
the org-scoping mechanism described above, not through explicit per-resource
grants.

---

## 8. Adding a new identity provider

1. Create a class in `app/services/identity/` that inherits from
   `IdentityProvider` (see `base.py`).
2. Implement `can_handle(token: str) -> bool` — a fast pre-check that looks at
   the JWT `iss` or `alg` without full validation.
3. Implement `async validate_token(token, db) -> Optional[AuthenticatedIdentity]`
   — full cryptographic validation; return `None` to pass to the next provider,
   raise `HTTPException(401)` if the token belongs to this provider but is
   rejected.
4. Return an `AuthenticatedIdentity` with a resolved `user_id` from the app
   database.  If the user does not exist and you want to auto-provision,
   create a `User` + `Organization` as the OIDC provider does.
5. Register your provider in `build_chain()` in
   `app/services/identity/chain.py`.
6. Add the relevant config keys to `app/config.py` and document them here.

No endpoint code changes are required — the chain is called from
`get_current_user` which every endpoint already uses.

### Keycloak quick-start

```bash
IDP_KEYCLOAK_ISSUER=https://keycloak.example.com/realms/myrealm
IDP_KEYCLOAK_CLIENT_ID=nest-egg
IDP_KEYCLOAK_ADMIN_GROUP=nest-egg-admins
IDP_KEYCLOAK_GROUPS_CLAIM=groups   # default; Keycloak puts groups here
IDENTITY_PROVIDER_CHAIN=keycloak,builtin
```

In Keycloak: create a `nest-egg-admins` group, add your admin users to it, and
ensure the client is configured to include the `groups` claim in access tokens
(Client Scopes → groups → mapper type "Group Membership", full path off).

### AWS Cognito quick-start

```bash
IDP_COGNITO_ISSUER=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_POOLID
IDP_COGNITO_CLIENT_ID=your_app_client_id
IDP_COGNITO_ADMIN_GROUP=nest-egg-admins
IDENTITY_PROVIDER_CHAIN=cognito,builtin
```

In Cognito: create a User Pool Group named `nest-egg-admins`.  Cognito
automatically includes `cognito:groups` in access tokens for group members.

---

## 9. Security invariants

The following properties are enforced throughout the stack and must be
maintained in any new code:

1. **Organisation scoping on every query**: every DB query that returns
   household data must filter by `organization_id == current_user.organization_id`.
2. **Guests never write via household-only routers**: member-only routers do
   not call `get_organization_scoped_user`, so they never see a guest context.
3. **Guests are never org admins of the host household**: `get_current_admin_user`
   explicitly rejects `_is_guest = True`.
4. **Guest org override is never persisted**: `_guard_guest_org_flush` is
   registered as a SQLAlchemy `before_flush` event and raises if a guest's
   overridden `organization_id` would be written back to the database.
5. **Invitation codes are single-use and expire**: accepted/declined codes
   cannot be reused; expiry is checked at acceptance time with a row-level
   lock to prevent double-acceptance.
6. **External IdP admin status is refreshed on every login**: a user removed
   from the IdP admin group loses `is_org_admin` on their next login — no
   manual revocation step required.
