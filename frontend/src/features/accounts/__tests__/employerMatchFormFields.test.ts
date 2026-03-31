import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const SCHEMAS_PATH = resolve(
  __dirname,
  "..",
  "schemas",
  "manualAccountSchemas.ts"
);

const FORM_PATH = resolve(
  __dirname,
  "..",
  "components",
  "forms",
  "InvestmentAccountForm.tsx"
);

describe("401k employer match form fields", () => {
  it("manualAccountSchemas includes employer_match_percent", () => {
    const src = readFileSync(SCHEMAS_PATH, "utf-8");
    expect(src).toContain("employer_match_percent");
  });

  it("manualAccountSchemas includes employer_match_limit_percent", () => {
    const src = readFileSync(SCHEMAS_PATH, "utf-8");
    expect(src).toContain("employer_match_limit_percent");
  });

  it("manualAccountSchemas includes annual_salary", () => {
    const src = readFileSync(SCHEMAS_PATH, "utf-8");
    expect(src).toContain("annual_salary");
  });

  it("InvestmentAccountForm renders employer match section for 401k/403b/457b types", () => {
    const src = readFileSync(FORM_PATH, "utf-8");
    expect(src).toContain("RETIREMENT_401K");
    expect(src).toContain("RETIREMENT_403B");
    expect(src).toContain("RETIREMENT_457B");
    expect(src).toContain("Employer Match");
  });

  it("InvestmentAccountForm registers annual_salary field", () => {
    const src = readFileSync(FORM_PATH, "utf-8");
    expect(src).toContain('"annual_salary"');
  });

  it("InvestmentAccountForm registers employer_match_percent field", () => {
    const src = readFileSync(FORM_PATH, "utf-8");
    expect(src).toContain('"employer_match_percent"');
  });

  it("InvestmentAccountForm registers employer_match_limit_percent field", () => {
    const src = readFileSync(FORM_PATH, "utf-8");
    expect(src).toContain('"employer_match_limit_percent"');
  });
});
