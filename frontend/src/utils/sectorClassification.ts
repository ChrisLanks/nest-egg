/**
 * Heuristic sector classification for holdings.
 *
 * This is a temporary solution for Phase 1. Phase 2 will replace this
 * with real sector data from Alpha Vantage API.
 *
 * Classification strategy:
 * 1. Check ticker against known mappings
 * 2. Parse holding name for sector keywords
 * 3. Default by asset type
 */

/**
 * Known ticker-to-sector mappings for common securities.
 * Covers major stocks and popular ETFs.
 */
const TICKER_SECTOR_MAP: Record<string, string> = {
  // Technology
  'AAPL': 'Technology',
  'MSFT': 'Technology',
  'GOOGL': 'Technology',
  'GOOG': 'Technology',
  'META': 'Technology',
  'NVDA': 'Technology',
  'AMD': 'Technology',
  'INTC': 'Technology',
  'CSCO': 'Technology',
  'ORCL': 'Technology',
  'CRM': 'Technology',
  'ADBE': 'Technology',
  'NFLX': 'Technology',

  // Financials
  'JPM': 'Financials',
  'BAC': 'Financials',
  'WFC': 'Financials',
  'GS': 'Financials',
  'MS': 'Financials',
  'C': 'Financials',
  'V': 'Financials',
  'MA': 'Financials',
  'AXP': 'Financials',

  // Healthcare
  'JNJ': 'Healthcare',
  'UNH': 'Healthcare',
  'PFE': 'Healthcare',
  'ABBV': 'Healthcare',
  'TMO': 'Healthcare',
  'MRK': 'Healthcare',
  'LLY': 'Healthcare',
  'CVS': 'Healthcare',

  // Consumer Discretionary
  'AMZN': 'Consumer Discretionary',
  'TSLA': 'Consumer Discretionary',
  'HD': 'Consumer Discretionary',
  'MCD': 'Consumer Discretionary',
  'NKE': 'Consumer Discretionary',
  'SBUX': 'Consumer Discretionary',
  'TGT': 'Consumer Discretionary',

  // Consumer Staples
  'WMT': 'Consumer Staples',
  'PG': 'Consumer Staples',
  'KO': 'Consumer Staples',
  'PEP': 'Consumer Staples',
  'COST': 'Consumer Staples',

  // Energy
  'XOM': 'Energy',
  'CVX': 'Energy',
  'COP': 'Energy',
  'SLB': 'Energy',

  // Industrials
  'BA': 'Industrials',
  'CAT': 'Industrials',
  'GE': 'Industrials',
  'UPS': 'Industrials',

  // Communication Services
  'T': 'Communication Services',
  'VZ': 'Communication Services',
  'DIS': 'Communication Services',
  'CMCSA': 'Communication Services',

  // Utilities
  'NEE': 'Utilities',
  'DUK': 'Utilities',
  'SO': 'Utilities',

  // Real Estate
  'AMT': 'Real Estate',
  'PLD': 'Real Estate',
  'CCI': 'Real Estate',

  // Common ETFs
  'VTI': 'Broad Market ETF',
  'VOO': 'Broad Market ETF',
  'SPY': 'Broad Market ETF',
  'IVV': 'Broad Market ETF',
  'VT': 'Global Market ETF',
  'QQQ': 'Technology-Heavy ETF',
  'VIG': 'Dividend ETF',
  'VXUS': 'International ETF',
  'BND': 'Bond ETF',
  'AGG': 'Bond ETF',
  'VNQ': 'Real Estate ETF',

  // Common Mutual Funds
  'VTSAX': 'Broad Market Fund',
  'VTIAX': 'International Fund',
  'VBTLX': 'Bond Fund',
  'VFIAX': 'S&P 500 Fund',
  'VMFXX': 'Money Market Fund',
  'FXAIX': 'S&P 500 Fund',
};

/**
 * Sector keywords to search for in holding names.
 * Order matters - more specific terms should come first.
 */
const SECTOR_KEYWORDS: Array<{ keywords: string[]; sector: string }> = [
  { keywords: ['technology', 'tech', 'software', 'semiconductor', 'computer', 'internet'], sector: 'Technology' },
  { keywords: ['financial', 'bank', 'insurance', 'investment', 'capital'], sector: 'Financials' },
  { keywords: ['healthcare', 'health care', 'medical', 'pharmaceutical', 'biotech', 'hospital'], sector: 'Healthcare' },
  { keywords: ['consumer discretionary', 'retail', 'automobile', 'entertainment'], sector: 'Consumer Discretionary' },
  { keywords: ['consumer staples', 'food', 'beverage', 'household'], sector: 'Consumer Staples' },
  { keywords: ['energy', 'oil', 'gas', 'petroleum'], sector: 'Energy' },
  { keywords: ['industrial', 'manufacturing', 'aerospace', 'defense'], sector: 'Industrials' },
  { keywords: ['communication', 'telecom', 'media'], sector: 'Communication Services' },
  { keywords: ['utility', 'utilities', 'electric', 'water'], sector: 'Utilities' },
  { keywords: ['real estate', 'realty', 'property', 'reit'], sector: 'Real Estate' },
  { keywords: ['materials', 'chemical', 'mining', 'metal'], sector: 'Materials' },
];

/**
 * Classify a holding into a financial sector using heuristics.
 *
 * @param ticker - Stock ticker symbol (e.g., "AAPL", "VTI")
 * @param name - Full name of holding (e.g., "Apple Inc.", "Vanguard Total Stock Market ETF")
 * @param assetType - Type of asset (e.g., "stock", "etf", "mutual_fund", "bond", "cash")
 * @returns Sector classification string
 */
export function classifySector(
  ticker: string,
  name: string | null,
  assetType: string | null
): string {
  const tickerUpper = ticker.toUpperCase();

  // Strategy 1: Check ticker map
  if (TICKER_SECTOR_MAP[tickerUpper]) {
    return TICKER_SECTOR_MAP[tickerUpper];
  }

  // Strategy 2: Parse name for keywords
  if (name) {
    const nameLower = name.toLowerCase();

    for (const { keywords, sector } of SECTOR_KEYWORDS) {
      for (const keyword of keywords) {
        if (nameLower.includes(keyword)) {
          return sector;
        }
      }
    }
  }

  // Strategy 3: Default by asset type
  if (assetType) {
    switch (assetType.toLowerCase()) {
      case 'etf':
        return 'Diversified ETF';
      case 'mutual_fund':
        return 'Diversified Fund';
      case 'bond':
        return 'Fixed Income';
      case 'cash':
        return 'Cash & Equivalents';
      default:
        return 'Other';
    }
  }

  return 'Other';
}

/**
 * Sector breakdown data for visualization.
 */
export interface SectorBreakdown {
  sector: string;
  value: number;
  count: number;
  percentage: number;
}

/**
 * Aggregate holdings by sector using heuristic classification.
 *
 * @param holdings - Array of holdings with ticker, name, asset_type, and current_total_value
 * @returns Array of sector breakdowns sorted by value descending
 */
export function aggregateBySector(
  holdings: Array<{
    ticker: string;
    name: string | null;
    asset_type: string | null;
    current_total_value: number | null;
  }>
): SectorBreakdown[] {
  const sectorMap = new Map<string, { value: number; count: number }>();

  for (const holding of holdings) {
    const sector = classifySector(holding.ticker, holding.name, holding.asset_type);
    // Convert to number to handle string values from API
    const value = Number(holding.current_total_value) || 0;

    const existing = sectorMap.get(sector) || { value: 0, count: 0 };
    sectorMap.set(sector, {
      value: existing.value + value,
      count: existing.count + 1,
    });
  }

  const total = Array.from(sectorMap.values()).reduce((sum, s) => sum + s.value, 0);

  return Array.from(sectorMap.entries())
    .map(([sector, data]) => ({
      sector,
      value: data.value,
      count: data.count,
      percentage: total > 0 ? (data.value / total) * 100 : 0,
    }))
    .sort((a, b) => b.value - a.value);
}
