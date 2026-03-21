/**
 * Currency Context
 *
 * Provides the org's default currency and formatting helpers to the entire app.
 * Currency is read from /settings/profile (org.default_currency), falling back
 * to "USD" if not set or while loading.
 *
 * This is display-only formatting — no FX conversion. See backend/app/services/fx_service.py
 * for the stub that will power future conversion once an FX API is integrated.
 *
 * Usage:
 *   const { formatCurrency, formatCurrencyCompact, currency, symbol } = useCurrency();
 */

import {
  createContext,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "../features/auth/stores/authStore";
import api from "../services/api";

interface CurrencyContextType {
  /** ISO 4217 currency code, e.g. "USD", "EUR", "GBP" */
  currency: string;
  /** Format a number as a currency string using the org's currency */
  formatCurrency: (amount: number, options?: Intl.NumberFormatOptions) => string;
  /** Compact format: "$1.2M", "€500K", etc. */
  formatCurrencyCompact: (amount: number) => string;
  /** Currency symbol derived from the currency code, e.g. "$", "€", "£" */
  symbol: string;
}

const CurrencyContext = createContext<CurrencyContextType | undefined>(
  undefined
);

function getCurrencySymbol(currency: string): string {
  try {
    return (
      new Intl.NumberFormat("en-US", { style: "currency", currency })
        .formatToParts(0)
        .find((p) => p.type === "currency")?.value ?? currency
    );
  } catch {
    return currency;
  }
}

export const CurrencyProvider = ({ children }: { children: ReactNode }) => {
  const { isAuthenticated } = useAuthStore();

  // Re-uses the ["userProfile"] cache key — same as PreferencesPage and useNavDefaults,
  // so this never causes an extra network request.
  const { data: profile } = useQuery({
    queryKey: ["userProfile"],
    queryFn: async () => {
      const res = await api.get("/settings/profile");
      return res.data as { default_currency?: string | null };
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });

  const currency = profile?.default_currency?.toUpperCase() || "USD";

  const value = useMemo<CurrencyContextType>(() => {
    const symbol = getCurrencySymbol(currency);

    const formatCurrency = (
      amount: number,
      options?: Intl.NumberFormatOptions
    ): string =>
      new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
        ...options,
      }).format(amount);

    const formatCurrencyCompact = (amount: number): string =>
      new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
        notation: "compact",
        maximumFractionDigits: 1,
      }).format(amount);

    return { currency, formatCurrency, formatCurrencyCompact, symbol };
  }, [currency]);

  return (
    <CurrencyContext.Provider value={value}>
      {children}
    </CurrencyContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export function useCurrency(): CurrencyContextType {
  const ctx = useContext(CurrencyContext);
  if (!ctx) {
    throw new Error("useCurrency must be used within CurrencyProvider");
  }
  return ctx;
}
