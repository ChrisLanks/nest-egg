/**
 * Convenience hook — returns formatCurrency from CurrencyContext.
 *
 * Usage:
 *   const formatCurrency = useCurrencyFormatter();
 *   formatCurrency(1234.56)  // "$1,234.56" (or org currency)
 */
import { useCurrency } from "../contexts/CurrencyContext";

export function useCurrencyFormatter() {
  return useCurrency().formatCurrency;
}
