# Nest Egg Frontend

React single-page application for personal/household finance tracking.

## Tech Stack

- **React 18** with TypeScript
- **Vite** — build tooling and dev server
- **Chakra UI** — component library with dark mode support
- **React Router** — client-side routing
- **TanStack React Query** — server state management and caching
- **Zustand** — lightweight client state (auth store)
- **React Hook Form + Zod** — form handling with schema validation
- **Recharts** — charts and data visualization
- **Axios** — HTTP client with interceptors for auth token refresh
- **dnd-kit** — drag-and-drop for dashboard layout customization

## Getting Started

```bash
npm ci          # install dependencies
npm run dev     # start dev server (http://localhost:5173)
```

The dev server proxies `/api` requests to the backend at `http://localhost:8000`.

## Scripts

| Command             | Description                              |
| ------------------- | ---------------------------------------- |
| `npm run dev`       | Start Vite dev server with HMR           |
| `npm run build`     | Type-check and build for production      |
| `npm run preview`   | Preview production build locally         |
| `npm run lint`      | Run ESLint                               |
| `npm test`          | Run Vitest test suite                    |
| `npm run test:coverage` | Run tests with coverage report       |
| `npm run test:watch`    | Run tests in watch mode              |

## Project Structure

```
src/
├── components/        # Shared components (ForecastChart, Layout, ProtectedRoute, FinancialHealthWidget, FeeAnalysisPanel)
├── contexts/          # React contexts (UserViewContext for household multi-user)
├── features/          # Feature modules (domain-organized)
│   ├── auth/          #   Login, registration, MFA, password reset
│   ├── accounts/      #   Bank accounts, investment accounts, manual accounts
│   ├── budgets/       #   Budget tracking and alerts
│   ├── dashboard/     #   Dashboard widgets (net worth, cash flow, allocations)
│   ├── goals/         #   Savings goals with allocation strategies
│   ├── income-expenses/ # Income vs expenses analysis
│   ├── investments/   #   Holdings, growth projections, rebalancing, risk analysis
│   ├── notifications/ #   In-app notification center
│   ├── permissions/   #   Household member data sharing permissions
│   ├── retirement/    #   Retirement planning with Monte Carlo simulation
│   ├── rules/         #   Transaction auto-categorization rules
│   ├── transactions/  #   Transaction list, splits, merges, CSV import
│   ├── education/     #   Education planning (529 tracking, cost projections)
│   ├── rental-properties/ # Rental property P&L and Schedule E tracking
│   └── year-in-review/ #  Annual financial summary with YoY comparison
├── hooks/             # Shared hooks (useHouseholdMembers, useColorModePreference)
├── pages/             # Top-level route pages (incl. YearInReviewPage, EducationPlanningPage, RentalPropertiesPage)
├── services/          # API client (Axios instance with refresh token interceptor)
├── types/             # Shared TypeScript types
└── utils/             # Utilities (formatting, Monte Carlo simulation engine)
```

## Key Architectural Decisions

- **Feature-based organization**: Each feature owns its pages, components, API layer, and stores.
- **Auth**: Access tokens stored in memory (Zustand). Refresh tokens in httpOnly cookies. CSRF double-submit pattern via `X-CSRF-Token` header.
- **Multi-user household**: `UserViewContext` manages which household member's data is displayed. Supports combined view, single-member view, and filtered multi-member view.
- **Server state**: All API data flows through React Query with stale-time and cache invalidation on mutations.
- **Dark mode**: System preference detection with manual override via `useColorModePreference` hook, persisted to localStorage.

## Environment Variables

| Variable            | Default   | Description                       |
| ------------------- | --------- | --------------------------------- |
| `VITE_API_BASE_URL` | `/api/v1` | Backend API base URL              |

In production, nginx proxies `/api` to the backend container so the default works without changes.

## Build & Deploy

Production builds are created by the Dockerfile:

```bash
docker build -t nestegg-frontend .
```

The multi-stage build produces an nginx image serving the static assets with:
- Gzip compression
- SPA fallback routing
- Security headers (CSP, HSTS)
- Health check endpoint at `/health`
