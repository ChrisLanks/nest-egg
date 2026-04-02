/**
 * Tests for:
 * 1. Rental Properties page showing investment-type property accounts
 * 2. AccountDetailPage pre-populating property address/zip from account data
 * 3. Tax Center gated behind advanced mode
 * 4. ADVANCED_PATHS in Preferences matches Layout advanced items
 * 5. Nav item descriptions are substantive
 * 6. useNavDefaults detects investment-type property for Rental Properties nav
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const RENTAL_SVC = resolve(
  __dirname,
  "../../../../backend/app/services/rental_property_service.py"
);
const ACCOUNT_DETAIL = resolve(__dirname, "../../pages/AccountDetailPage.tsx");
const NAV_DEFAULTS = resolve(__dirname, "../../hooks/useNavDefaults.ts");
const PREFERENCES = resolve(__dirname, "../../pages/PreferencesPage.tsx");
const LAYOUT = resolve(__dirname, "../../components/Layout.tsx");
const RENTAL_PAGE = resolve(__dirname, "../../pages/RentalPropertiesPage.tsx");

const rentalSvc = readFileSync(RENTAL_SVC, "utf-8");
const accountDetail = readFileSync(ACCOUNT_DETAIL, "utf-8");
const navDefaults = readFileSync(NAV_DEFAULTS, "utf-8");
const preferences = readFileSync(PREFERENCES, "utf-8");
const layout = readFileSync(LAYOUT, "utf-8");
const rentalPage = readFileSync(RENTAL_PAGE, "utf-8");

// ---------------------------------------------------------------------------
// Backend: rental property service filter
// ---------------------------------------------------------------------------

it("rental_property_service imports PropertyType", () => {
  expect(rentalSvc).toContain("from app.models.account import Account, PropertyType, RentalType");
});

it("rental_property_service imports sqlalchemy or_ for compound filter", () => {
  expect(rentalSvc).toContain("from sqlalchemy import or_");
});

it("rental_property_service includes PropertyType.INVESTMENT in query filter", () => {
  expect(rentalSvc).toContain("Account.property_type == PropertyType.INVESTMENT");
});

it("rental_property_service uses or_ to combine is_rental_property and property_type", () => {
  expect(rentalSvc).toContain("or_(");
  expect(rentalSvc).toContain("Account.is_rental_property.is_(True)");
});

it("rental_property_service has _display_address helper method", () => {
  expect(rentalSvc).toContain("def _display_address(");
});

it("rental_property_service falls back to property_address + property_zip", () => {
  expect(rentalSvc).toContain("property_address");
  expect(rentalSvc).toContain("property_zip");
});

it("rental_property_service uses _display_address in get_property_pnl", () => {
  expect(rentalSvc).toContain('self._display_address(account)');
});

// ---------------------------------------------------------------------------
// Frontend: AccountDetailPage pre-populates address from account data
// ---------------------------------------------------------------------------

it("AccountDetailPage seeds propertyAddress from account.property_address", () => {
  expect(accountDetail).toContain("if (account.property_address) setPropertyAddress(account.property_address)");
});

it("AccountDetailPage seeds propertyZip from account.property_zip", () => {
  expect(accountDetail).toContain("if (account.property_zip) setPropertyZip(account.property_zip)");
});

it("AccountDetailPage address seeding useEffect depends on account.property_address", () => {
  expect(accountDetail).toContain("account?.property_address");
});

it("AccountDetailPage address seeding useEffect depends on account.property_zip", () => {
  expect(accountDetail).toContain("account?.property_zip");
});

// ---------------------------------------------------------------------------
// Nav: Tax Center is advanced-gated
// ---------------------------------------------------------------------------

it("useNavDefaults marks Tax Center as advanced", () => {
  // Should have advanced: true near the Tax Center entry
  const taxCenterIdx = navDefaults.indexOf('path: "/tax-center"');
  expect(taxCenterIdx).toBeGreaterThan(-1);
  const surrounding = navDefaults.slice(taxCenterIdx - 50, taxCenterIdx + 200);
  expect(surrounding).toContain("advanced: true");
});

it("useNavDefaults does NOT include tax-center in buildConditionalDefaults", () => {
  const buildFnIdx = navDefaults.indexOf("buildConditionalDefaults");
  const buildFnBody = navDefaults.slice(buildFnIdx, buildFnIdx + 1500);
  expect(buildFnBody).not.toContain('"/tax-center"');
});

it("useNavDefaults Tax Center reason describes its content", () => {
  expect(navDefaults).toContain("Roth conversion");
  expect(navDefaults).toContain("IRMAA");
});

it("Layout marks Tax Center as advanced", () => {
  const taxCenterIdx = layout.indexOf('path: "/tax-center"');
  expect(taxCenterIdx).toBeGreaterThan(-1);
  const surrounding = layout.slice(taxCenterIdx - 10, taxCenterIdx + 200);
  expect(surrounding).toContain("advanced: true");
});

it("Layout marks Planning Tools as advanced", () => {
  const idx = layout.indexOf('path: "/investment-tools"');
  expect(idx).toBeGreaterThan(-1);
  const surrounding = layout.slice(idx - 10, idx + 200);
  expect(surrounding).toContain("advanced: true");
});

it("Layout does NOT mark PE Performance as advanced (account-gated, not mode-gated)", () => {
  const idx = layout.indexOf('path: "/pe-performance"');
  expect(idx).toBeGreaterThan(-1);
  // Check there's no advanced: true between this path and the next item
  const nextBrace = layout.indexOf("}", idx);
  const segment = layout.slice(idx, nextBrace + 1);
  expect(segment).not.toContain("advanced: true");
});

it("Layout does NOT mark Rental Properties as advanced (account-gated)", () => {
  const idx = layout.indexOf('path: "/rental-properties"');
  expect(idx).toBeGreaterThan(-1);
  const nextBrace = layout.indexOf("}", idx);
  const segment = layout.slice(idx, nextBrace + 1);
  expect(segment).not.toContain("advanced: true");
});

// ---------------------------------------------------------------------------
// Preferences: ADVANCED_PATHS matches Layout
// ---------------------------------------------------------------------------

it("Preferences ADVANCED_PATHS includes /investment-tools", () => {
  expect(preferences).toContain('"/investment-tools"');
});

it("Preferences ADVANCED_PATHS includes /tax-center", () => {
  const advancedPathsIdx = preferences.indexOf("ADVANCED_PATHS");
  const block = preferences.slice(advancedPathsIdx, advancedPathsIdx + 200);
  expect(block).toContain('"/tax-center"');
});

it("Preferences show-advanced description mentions Tax Center", () => {
  expect(preferences).toContain("Tax Center");
});

it("Preferences show-advanced description mentions Planning Tools", () => {
  expect(preferences).toContain("Planning Tools");
});

// ---------------------------------------------------------------------------
// useNavDefaults: rental properties nav detects investment property_type
// ---------------------------------------------------------------------------

it("useNavDefaults Account interface includes property_type field", () => {
  expect(navDefaults).toContain("property_type?: string | null");
});

it("useNavDefaults hasRental checks property_type === investment", () => {
  expect(navDefaults).toContain('a.property_type === "investment"');
});

// ---------------------------------------------------------------------------
// Nav item descriptions are substantive
// ---------------------------------------------------------------------------

it("useNavDefaults Transactions reason describes what it does", () => {
  expect(navDefaults).toContain("search, filter, and categorize");
});

it("useNavDefaults Budgets reason describes what it does", () => {
  expect(navDefaults).toContain("monthly spending limits");
});

it("useNavDefaults Rental Properties reason describes Schedule E", () => {
  expect(navDefaults).toContain("Schedule E");
});

it("useNavDefaults Retirement reason describes Social Security", () => {
  expect(navDefaults).toContain("Social Security");
});

// ---------------------------------------------------------------------------
// Rental page empty state message
// ---------------------------------------------------------------------------

it("RentalPropertiesPage empty state no longer says 'set its classification'", () => {
  // Updated to say "classify it as"
  expect(rentalPage).toContain('classify it as "Investment Property"');
});
