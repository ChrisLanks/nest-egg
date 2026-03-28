/**
 * Tests for CalendarPage logic: calendar cell generation, event filtering,
 * event grouping by date, balance mapping, and date key formatting.
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach } from "vitest";

// ── Types (mirrored from CalendarPage.tsx) ───────────────────────────────────

interface FinancialCalendarEvent {
  date: string;
  name: string;
  amount: number;
  type: "bill" | "subscription" | "income";
  account?: string;
  frequency?: string;
}

interface DailyProjectedBalance {
  date: string;
  balance: number;
}

// ── Logic helpers (mirrored from CalendarPage.tsx) ───────────────────────────

const formatCurrencyShort = (amount: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

const eventTypeColor = (type: string) => {
  if (type === "income") return "green";
  if (type === "subscription") return "orange";
  return "red";
};

const eventTypeLabel = (type: string) => {
  if (type === "income") return "Income";
  if (type === "subscription") return "Subscription";
  return "Bill";
};

function filterEvents(
  events: FinancialCalendarEvent[],
  showBills: boolean,
  showSubscriptions: boolean,
  showIncome: boolean,
): FinancialCalendarEvent[] {
  return events.filter((ev) => {
    if (ev.type === "bill" && !showBills) return false;
    if (ev.type === "subscription" && !showSubscriptions) return false;
    if (ev.type === "income" && !showIncome) return false;
    return true;
  });
}

function groupEventsByDate(
  events: FinancialCalendarEvent[],
): Map<string, FinancialCalendarEvent[]> {
  const map = new Map<string, FinancialCalendarEvent[]>();
  for (const ev of events) {
    if (!map.has(ev.date)) map.set(ev.date, []);
    map.get(ev.date)!.push(ev);
  }
  return map;
}

function buildBalanceMap(
  dailyBalances: DailyProjectedBalance[],
): Map<string, number> {
  const map = new Map<string, number>();
  for (const dp of dailyBalances) {
    map.set(dp.date, dp.balance);
  }
  return map;
}

function buildCalendarCells(year: number, month: number): (number | null)[] {
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

function buildDateKey(year: number, month: number, day: number): string {
  return `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

// ── Month navigation helpers ─────────────────────────────────────────────────

function prevMonth(
  year: number,
  month: number,
): { year: number; month: number } {
  if (month === 0) return { year: year - 1, month: 11 };
  return { year, month: month - 1 };
}

function nextMonth(
  year: number,
  month: number,
): { year: number; month: number } {
  if (month === 11) return { year: year + 1, month: 0 };
  return { year, month: month + 1 };
}

// ── Fixtures ─────────────────────────────────────────────────────────────────

const EVENTS: FinancialCalendarEvent[] = [
  { date: "2025-03-01", name: "Rent", amount: -1500, type: "bill" },
  { date: "2025-03-01", name: "Netflix", amount: -15, type: "subscription" },
  { date: "2025-03-15", name: "Salary", amount: 5000, type: "income" },
  { date: "2025-03-20", name: "Electric", amount: -100, type: "bill" },
];

// ── Tests ────────────────────────────────────────────────────────────────────

describe("eventTypeColor", () => {
  it("returns green for income", () => {
    expect(eventTypeColor("income")).toBe("green");
  });

  it("returns orange for subscription", () => {
    expect(eventTypeColor("subscription")).toBe("orange");
  });

  it("returns red for bill (default)", () => {
    expect(eventTypeColor("bill")).toBe("red");
    expect(eventTypeColor("unknown")).toBe("red");
  });
});

describe("eventTypeLabel", () => {
  it("returns correct labels", () => {
    expect(eventTypeLabel("income")).toBe("Income");
    expect(eventTypeLabel("subscription")).toBe("Subscription");
    expect(eventTypeLabel("bill")).toBe("Bill");
  });
});

describe("filterEvents", () => {
  it("shows all events when all toggles are on", () => {
    const result = filterEvents(EVENTS, true, true, true);
    expect(result).toHaveLength(4);
  });

  it("hides bills when showBills is false", () => {
    const result = filterEvents(EVENTS, false, true, true);
    expect(result).toHaveLength(2); // Netflix + Salary
    expect(result.every((e) => e.type !== "bill")).toBe(true);
  });

  it("hides subscriptions when showSubscriptions is false", () => {
    const result = filterEvents(EVENTS, true, false, true);
    expect(result).toHaveLength(3);
    expect(result.every((e) => e.type !== "subscription")).toBe(true);
  });

  it("hides income when showIncome is false", () => {
    const result = filterEvents(EVENTS, true, true, false);
    expect(result).toHaveLength(3);
    expect(result.every((e) => e.type !== "income")).toBe(true);
  });

  it("returns empty when all toggles are off", () => {
    const result = filterEvents(EVENTS, false, false, false);
    expect(result).toHaveLength(0);
  });
});

describe("groupEventsByDate", () => {
  it("groups events by their date", () => {
    const grouped = groupEventsByDate(EVENTS);
    expect(grouped.size).toBe(3);
    expect(grouped.get("2025-03-01")).toHaveLength(2);
    expect(grouped.get("2025-03-15")).toHaveLength(1);
    expect(grouped.get("2025-03-20")).toHaveLength(1);
  });

  it("returns empty map for no events", () => {
    const grouped = groupEventsByDate([]);
    expect(grouped.size).toBe(0);
  });
});

describe("buildBalanceMap", () => {
  it("creates a date-to-balance mapping", () => {
    const balances: DailyProjectedBalance[] = [
      { date: "2025-03-01", balance: 10000 },
      { date: "2025-03-15", balance: 8500 },
    ];
    const map = buildBalanceMap(balances);
    expect(map.get("2025-03-01")).toBe(10000);
    expect(map.get("2025-03-15")).toBe(8500);
    expect(map.get("2025-03-10")).toBeUndefined();
  });
});

describe("buildCalendarCells", () => {
  it("starts with correct number of null padding cells", () => {
    // March 2025 starts on Saturday (day index 6)
    const cells = buildCalendarCells(2025, 2); // month 2 = March
    const leadingNulls = cells.filter((c, i) => c === null && i < 7).length;
    expect(leadingNulls).toBe(new Date(2025, 2, 1).getDay());
  });

  it("contains the correct number of day cells", () => {
    const cells = buildCalendarCells(2025, 2);
    const dayCells = cells.filter((c) => c !== null);
    expect(dayCells).toHaveLength(31); // March has 31 days
  });

  it("total cells is a multiple of 7", () => {
    const cells = buildCalendarCells(2025, 1); // February
    expect(cells.length % 7).toBe(0);
  });

  it("handles February in a leap year", () => {
    const cells = buildCalendarCells(2024, 1); // Feb 2024 is leap
    const dayCells = cells.filter((c) => c !== null);
    expect(dayCells).toHaveLength(29);
  });
});

describe("buildDateKey", () => {
  it("pads month and day with leading zeros", () => {
    expect(buildDateKey(2025, 0, 5)).toBe("2025-01-05");
    expect(buildDateKey(2025, 11, 25)).toBe("2025-12-25");
  });
});

describe("Month navigation", () => {
  it("wraps from January backward to December of previous year", () => {
    expect(prevMonth(2025, 0)).toEqual({ year: 2024, month: 11 });
  });

  it("goes back one month normally", () => {
    expect(prevMonth(2025, 6)).toEqual({ year: 2025, month: 5 });
  });

  it("wraps from December forward to January of next year", () => {
    expect(nextMonth(2025, 11)).toEqual({ year: 2026, month: 0 });
  });

  it("goes forward one month normally", () => {
    expect(nextMonth(2025, 5)).toEqual({ year: 2025, month: 6 });
  });
});

describe("Day total calculation", () => {
  it("sums event amounts for a given day", () => {
    const dayEvents = EVENTS.filter((e) => e.date === "2025-03-01");
    const dayTotal = dayEvents.reduce((sum, e) => sum + e.amount, 0);
    expect(dayTotal).toBe(-1515);
  });

  it("returns 0 for a day with no events", () => {
    const dayEvents = EVENTS.filter((e) => e.date === "2025-03-05");
    const dayTotal = dayEvents.reduce((sum, e) => sum + e.amount, 0);
    expect(dayTotal).toBe(0);
  });
});

describe("formatCurrencyShort", () => {
  it("formats positive amounts", () => {
    expect(formatCurrencyShort(5000)).toBe("$5,000");
  });

  it("formats negative amounts", () => {
    expect(formatCurrencyShort(-1500)).toBe("-$1,500");
  });
});

// ── Persisted toggle preferences ────────────────────────────────────────────

const CALENDAR_PREFS_KEY = "nest-egg-calendar-prefs";

interface CalendarPrefs {
  showBills: boolean;
  showSubscriptions: boolean;
  showIncome: boolean;
  showProjectedBalance: boolean;
}

const DEFAULT_PREFS: CalendarPrefs = {
  showBills: true,
  showSubscriptions: true,
  showIncome: true,
  showProjectedBalance: false,
};

function loadCalendarPrefs(): CalendarPrefs {
  try {
    const raw = localStorage.getItem(CALENDAR_PREFS_KEY);
    if (raw) return { ...DEFAULT_PREFS, ...JSON.parse(raw) };
  } catch {
    /* ignore */
  }
  return DEFAULT_PREFS;
}

function saveCalendarPrefs(prefs: CalendarPrefs): void {
  try {
    localStorage.setItem(CALENDAR_PREFS_KEY, JSON.stringify(prefs));
  } catch {
    /* ignore */
  }
}

describe("Calendar toggle persistence", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns default prefs when nothing is stored", () => {
    const prefs = loadCalendarPrefs();
    expect(prefs).toEqual(DEFAULT_PREFS);
  });

  it("persists and restores toggle changes", () => {
    const updated: CalendarPrefs = {
      showBills: false,
      showSubscriptions: true,
      showIncome: false,
      showProjectedBalance: true,
    };
    saveCalendarPrefs(updated);
    expect(loadCalendarPrefs()).toEqual(updated);
  });

  it("merges partial stored prefs with defaults", () => {
    localStorage.setItem(
      CALENDAR_PREFS_KEY,
      JSON.stringify({ showBills: false }),
    );
    const prefs = loadCalendarPrefs();
    expect(prefs.showBills).toBe(false);
    expect(prefs.showSubscriptions).toBe(true);
    expect(prefs.showIncome).toBe(true);
    expect(prefs.showProjectedBalance).toBe(false);
  });

  it("returns defaults for corrupt localStorage data", () => {
    localStorage.setItem(CALENDAR_PREFS_KEY, "not-json");
    const prefs = loadCalendarPrefs();
    expect(prefs).toEqual(DEFAULT_PREFS);
  });
});

// ── User view filtering (source-level verification) ─────────────────────────

describe("Calendar user view filtering", () => {
  it("CalendarPage imports useUserView", async () => {
    const fs = await import("fs");
    const source = fs.readFileSync("src/pages/CalendarPage.tsx", "utf-8");
    expect(source).toContain("useUserView");
    expect(source).toContain("selectedUserId");
  });

  it("query key includes selectedUserId for cache separation", async () => {
    const fs = await import("fs");
    const source = fs.readFileSync("src/pages/CalendarPage.tsx", "utf-8");
    // The query key should include selectedUserId so switching users refetches
    expect(source).toMatch(
      /queryKey:.*\[.*"financial-calendar".*selectedUserId.*\]/,
    );
  });

  it("API client passes userId to financial-calendar endpoint", async () => {
    const fs = await import("fs");
    const source = fs.readFileSync(
      "src/api/recurring-transactions.ts",
      "utf-8",
    );
    expect(source).toContain("user_id");
    expect(source).toMatch(/getMonth[\s\S]*userId/);
  });
});

// ── computeDefaultYears (household averaging) ───────────────────────────────

function computeDefaultYears(
  birthYears: (number | null | undefined)[],
): number {
  const valid = birthYears.filter((y): y is number => typeof y === "number");
  if (valid.length === 0) return 10;
  const avgBirthYear = Math.round(
    valid.reduce((sum, y) => sum + y, 0) / valid.length,
  );
  const currentYear = new Date().getFullYear();
  const avgAge = currentYear - avgBirthYear;
  const yearsUntilRetirement = Math.round(65 - avgAge);
  return Math.max(1, yearsUntilRetirement);
}

describe("computeDefaultYears", () => {
  const currentYear = new Date().getFullYear();

  it("returns 10 when no birth years available", () => {
    expect(computeDefaultYears([])).toBe(10);
    expect(computeDefaultYears([null, undefined])).toBe(10);
  });

  it("computes years for a single person", () => {
    const birthYear = currentYear - 30; // age 30 → 65-30 = 35
    expect(computeDefaultYears([birthYear])).toBe(35);
  });

  it("averages multiple birth years", () => {
    const person1 = currentYear - 30; // age 30
    const person2 = currentYear - 40; // age 40
    // avg age = 35 → 65-35 = 30
    expect(computeDefaultYears([person1, person2])).toBe(30);
  });

  it("ignores null/undefined in a mixed array", () => {
    const birthYear = currentYear - 50; // age 50 → 65-50 = 15
    expect(computeDefaultYears([null, birthYear, undefined])).toBe(15);
  });

  it("returns minimum of 1 for someone past 65", () => {
    const birthYear = currentYear - 70; // age 70 → 65-70 = -5 → clamped to 1
    expect(computeDefaultYears([birthYear])).toBe(1);
  });
});

// ── HouseholdMember birth_year field ────────────────────────────────────────

describe("HouseholdMember type includes birth_year", () => {
  it("useHouseholdMembers interface includes birth_year", async () => {
    const fs = await import("fs");
    const source = fs.readFileSync("src/hooks/useHouseholdMembers.ts", "utf-8");
    expect(source).toContain("birth_year");
  });
});

// ── CalendarPage error state rendering decision ──────────────────────────────
//
// Mirrors the render-branch logic added to CalendarPage:
//   financialCalendarLoading → spinner
//   financialCalendarError   → error state with retry button
//   otherwise                → calendar grid

type CalendarPageState = "loading" | "error" | "calendar";

const resolveCalendarPageState = (
  isLoading: boolean,
  isError: boolean,
): CalendarPageState => {
  if (isLoading) return "loading";
  if (isError) return "error";
  return "calendar";
};

const calendarErrorMessageText = "Failed to load calendar. Please try again.";
const calendarRetryButtonLabel = "Retry";

describe("CalendarPage error state", () => {
  it("resolves to 'loading' when isLoading is true", () => {
    expect(resolveCalendarPageState(true, false)).toBe("loading");
  });

  it("loading takes priority over error", () => {
    expect(resolveCalendarPageState(true, true)).toBe("loading");
  });

  it("resolves to 'error' when isError is true", () => {
    expect(resolveCalendarPageState(false, true)).toBe("error");
  });

  it("resolves to 'calendar' when not loading and no error", () => {
    expect(resolveCalendarPageState(false, false)).toBe("calendar");
  });

  it("error message text mentions calendar", () => {
    expect(calendarErrorMessageText.toLowerCase()).toContain("calendar");
  });

  it("retry button label is defined", () => {
    expect(calendarRetryButtonLabel).toBe("Retry");
  });
});

// ── Dividend event filtering (round-70 fix) ──────────────────────────────────
//
// Before the fix, dividendEvents were pre-filtered to calMonthStr inside the
// filteredEvents memo. This meant the weekly view never received dividends from
// other months.  After the fix, NO calMonthStr filter is applied in the memo —
// each view is responsible for scoping events to its own date range.

type CalendarEventWithDividend = FinancialCalendarEvent & {
  account?: string;
};

interface DividendMonthEvent {
  pay_date?: string;
  ex_date?: string;
  ticker?: string;
  income_type?: string;
  amount: number;
  account_name?: string;
}

interface DividendCalendar {
  months: { events: DividendMonthEvent[] }[];
}

/** Mirrors the FIXED filteredEvents dividend merge (no calMonthStr filter). */
function mergeDividendEvents(
  base: CalendarEventWithDividend[],
  dividendCalendar: DividendCalendar | null,
  showDividends: boolean,
): CalendarEventWithDividend[] {
  if (!showDividends || !dividendCalendar) return base;

  const dividendEvents: CalendarEventWithDividend[] = [];
  for (const month of dividendCalendar.months) {
    for (const ev of month.events) {
      const date = ev.pay_date ?? ev.ex_date;
      if (!date) continue;
      // NO calMonthStr filter — include all dividend dates
      dividendEvents.push({
        date,
        type: "income" as const,
        name: ev.ticker ?? ev.income_type ?? "Dividend",
        amount: ev.amount,
        account: ev.account_name,
      });
    }
  }
  return [...base, ...dividendEvents];
}

/** Mirrors the FIXED weekly date range filter (local midnight, not UTC). */
function filterEventsForWeek(
  events: CalendarEventWithDividend[],
  weekStart: Date,
): CalendarEventWithDividend[] {
  const weekEnd = new Date(weekStart.getTime() + 7 * 86400000);
  return events.filter((ev) => {
    const [y, m, d] = ev.date.split("-").map(Number);
    const evDate = new Date(y, m - 1, d); // local midnight — no UTC shift
    return evDate >= weekStart && evDate < weekEnd;
  });
}

describe("Dividend toggle: no calMonthStr pre-filter in memo", () => {
  const base: CalendarEventWithDividend[] = [
    { date: "2026-03-15", name: "Salary", amount: 5000, type: "income" },
  ];

  const dividendCalendar: DividendCalendar = {
    months: [
      {
        events: [
          { pay_date: "2026-03-10", ticker: "AAPL", amount: 120, account_name: "Brokerage" },
          { pay_date: "2026-04-05", ticker: "MSFT", amount: 80, account_name: "Brokerage" },
          { pay_date: "2026-02-20", ticker: "VTI",  amount: 60, account_name: "IRA" },
        ],
      },
    ],
  };

  it("includes dividends from ALL months when showDividends is true", () => {
    const result = mergeDividendEvents(base, dividendCalendar, true);
    const dividends = result.filter((e) => e.name !== "Salary");
    expect(dividends).toHaveLength(3); // AAPL (Mar), MSFT (Apr), VTI (Feb)
  });

  it("includes dividends from months other than calMonth (Feb + Apr)", () => {
    const result = mergeDividendEvents(base, dividendCalendar, true);
    const dates = result.map((e) => e.date);
    expect(dates).toContain("2026-04-05"); // next month dividend visible
    expect(dates).toContain("2026-02-20"); // previous month dividend visible
  });

  it("returns only base events when showDividends is false", () => {
    const result = mergeDividendEvents(base, dividendCalendar, false);
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("Salary");
  });

  it("returns only base events when dividendCalendar is null", () => {
    const result = mergeDividendEvents(base, null, true);
    expect(result).toHaveLength(1);
  });

  it("skips dividend events with no date", () => {
    const cal: DividendCalendar = {
      months: [{ events: [{ amount: 50 }] }], // no pay_date or ex_date
    };
    const result = mergeDividendEvents(base, cal, true);
    expect(result).toHaveLength(1); // only base, no dividend added
  });

  it("uses ex_date when pay_date is absent", () => {
    const cal: DividendCalendar = {
      months: [{ events: [{ ex_date: "2026-03-08", ticker: "BND", amount: 30 }] }],
    };
    const result = mergeDividendEvents(base, cal, true);
    expect(result.find((e) => e.date === "2026-03-08")).toBeDefined();
  });
});

describe("Weekly view: local-midnight date parsing prevents UTC offset shift", () => {
  // Week starting Sunday 2026-03-22 (local)
  const weekStart = new Date(2026, 2, 22, 0, 0, 0, 0); // local midnight

  const events: CalendarEventWithDividend[] = [
    { date: "2026-03-22", name: "Sunday Bill",  amount: -50,  type: "bill" },
    { date: "2026-03-25", name: "Mid-week",     amount: -100, type: "subscription" },
    { date: "2026-03-28", name: "Saturday Pay", amount: 200,  type: "income" },
    { date: "2026-03-29", name: "Next Sunday",  amount: -30,  type: "bill" }, // outside week
    { date: "2026-03-21", name: "Last Saturday",amount: -20,  type: "bill" }, // outside week
  ];

  it("includes all 7 days of the week", () => {
    const result = filterEventsForWeek(events, weekStart);
    expect(result).toHaveLength(3);
  });

  it("includes the first day of the week (Sunday)", () => {
    const result = filterEventsForWeek(events, weekStart);
    expect(result.find((e) => e.date === "2026-03-22")).toBeDefined();
  });

  it("includes the last day of the week (Saturday)", () => {
    const result = filterEventsForWeek(events, weekStart);
    expect(result.find((e) => e.date === "2026-03-28")).toBeDefined();
  });

  it("excludes the day after the week ends (next Sunday)", () => {
    const result = filterEventsForWeek(events, weekStart);
    expect(result.find((e) => e.date === "2026-03-29")).toBeUndefined();
  });

  it("excludes the day before the week starts (prior Saturday)", () => {
    const result = filterEventsForWeek(events, weekStart);
    expect(result.find((e) => e.date === "2026-03-21")).toBeUndefined();
  });

  it("returns empty for a week with no matching events", () => {
    const nextWeekStart = new Date(2026, 3, 5, 0, 0, 0, 0); // April 5
    const result = filterEventsForWeek(events, nextWeekStart);
    expect(result).toHaveLength(0);
  });
});

describe("Source: calMonthStr filter removed from dividend memo", () => {
  it("CalendarPage source does not filter dividends by calMonthStr", async () => {
    const fs = await import("fs");
    const source = fs.readFileSync("src/pages/CalendarPage.tsx", "utf-8");
    // The old buggy line was: if (!date.startsWith(calMonthStr)) continue;
    expect(source).not.toContain("date.startsWith(calMonthStr)");
  });

  it("CalendarPage weekly range filter uses local date parsing", async () => {
    const fs = await import("fs");
    const source = fs.readFileSync("src/pages/CalendarPage.tsx", "utf-8");
    // The fix parses dates as local midnight via split("-")
    expect(source).toContain('ev.date.split("-").map(Number)');
  });
});
