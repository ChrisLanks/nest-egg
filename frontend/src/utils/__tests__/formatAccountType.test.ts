/**
 * Tests for formatAccountType utility.
 *
 * Validates display name overrides, tax treatment labels, Roth variants,
 * Traditional suffixes, and the default snake_case → Title Case fallback.
 */

import { describe, it, expect } from "vitest";
import { formatAccountType } from "../formatAccountType";

describe("formatAccountType — overrides", () => {
  it.each([
    ["retirement_401k", "401(k)"],
    ["retirement_403b", "403(b)"],
    ["retirement_457b", "457(b)"],
    ["retirement_ira", "IRA"],
    ["retirement_roth", "Roth IRA"],
    ["retirement_sep_ira", "SEP IRA"],
    ["retirement_simple_ira", "SIMPLE IRA"],
    ["retirement_529", "529 Plan"],
    ["hsa", "HSA"],
    ["cd", "CD"],
    ["trump_account", "Trump Account"],
    ["custodial_ugma", "UGMA/UTMA"],
    ["trust", "Trust"],
  ])("formats %s as %s", (input, expected) => {
    expect(formatAccountType(input)).toBe(expected);
  });
});

describe("formatAccountType — Roth tax treatment", () => {
  it.each([
    ["retirement_401k", "Roth 401(k)"],
    ["retirement_403b", "Roth 403(b)"],
    ["retirement_457b", "Roth 457(b)"],
    ["retirement_ira", "Roth IRA"],
  ])("formats %s with roth treatment as %s", (input, expected) => {
    expect(formatAccountType(input, "roth")).toBe(expected);
  });

  it("does not apply Roth prefix to non-retirement types", () => {
    expect(formatAccountType("hsa", "roth")).toBe("HSA");
    expect(formatAccountType("trump_account", "roth")).toBe("Trump Account");
  });
});

describe("formatAccountType — Traditional (pre_tax) suffix", () => {
  it.each([
    ["retirement_401k", "401(k) (Traditional)"],
    ["retirement_403b", "403(b) (Traditional)"],
    ["retirement_457b", "457(b) (Traditional)"],
    ["retirement_ira", "IRA (Traditional)"],
  ])("formats %s with pre_tax treatment as %s", (input, expected) => {
    expect(formatAccountType(input, "pre_tax")).toBe(expected);
  });

  it("does not apply Traditional suffix to non-employer plan overrides", () => {
    expect(formatAccountType("hsa", "pre_tax")).toBe("HSA");
    expect(formatAccountType("retirement_sep_ira", "pre_tax")).toBe("SEP IRA");
    expect(formatAccountType("trump_account", "pre_tax")).toBe("Trump Account");
  });
});

describe("formatAccountType — default snake_case to Title Case", () => {
  it("converts unknown types to Title Case", () => {
    expect(formatAccountType("checking")).toBe("Checking");
    expect(formatAccountType("savings")).toBe("Savings");
    expect(formatAccountType("money_market")).toBe("Money Market");
    expect(formatAccountType("credit_card")).toBe("Credit Card");
    expect(formatAccountType("student_loan")).toBe("Student Loan");
  });
});

describe("formatAccountType — null/undefined tax treatment", () => {
  it("treats null tax treatment same as no treatment", () => {
    expect(formatAccountType("retirement_401k", null)).toBe("401(k)");
    expect(formatAccountType("retirement_ira", undefined)).toBe("IRA");
  });
});
