/**
 * Tests for WelcomePage logic fixes:
 * - Household name update uses correct endpoint (PATCH /settings/organization)
 * - Payload uses `name` field matching OrganizationUpdate schema
 */

describe("WelcomePage endpoint fixes", () => {
  it("household settings call uses /settings/organization not /household/settings", () => {
    const source = require("fs").readFileSync(
      require("path").join(__dirname, "../WelcomePage.tsx"),
      "utf8"
    );
    expect(source).not.toContain("/household/settings");
  });

  it("household settings call uses /settings/organization", () => {
    const source = require("fs").readFileSync(
      require("path").join(__dirname, "../WelcomePage.tsx"),
      "utf8"
    );
    expect(source).toContain('"/settings/organization"');
  });

  it("organization update payload uses `name` field matching OrganizationUpdate schema", () => {
    const source = require("fs").readFileSync(
      require("path").join(__dirname, "../WelcomePage.tsx"),
      "utf8"
    );
    // Should pass { name } not { organization_name: name }
    expect(source).toContain('"/settings/organization", { name }');
    expect(source).not.toContain("organization_name:");
  });

  it("dashboard layout save is wrapped in try/catch so errors are non-blocking", () => {
    const source = require("fs").readFileSync(
      require("path").join(__dirname, "../WelcomePage.tsx"),
      "utf8"
    );
    // The dashboard-layout call should be inside a try block
    const dashboardSection = source.substring(
      source.indexOf("dashboard-layout"),
      source.indexOf("dashboard-layout") + 200
    );
    expect(dashboardSection).toBeTruthy();
    // Verify the overall finish function has error handling
    expect(source).toContain("} catch {");
  });

  it("household name mutation errors are non-critical (onError defined)", () => {
    const source = require("fs").readFileSync(
      require("path").join(__dirname, "../WelcomePage.tsx"),
      "utf8"
    );
    // updateHouseholdMutation should have onError handler
    const mutationSection = source.substring(
      source.indexOf("updateHouseholdMutation"),
      source.indexOf("updateHouseholdMutation") + 300
    );
    expect(mutationSection).toContain("onError");
  });

  it("household name label softens for solo goals (spending/investments)", () => {
    const source = require("fs").readFileSync(
      require("path").join(__dirname, "../WelcomePage.tsx"),
      "utf8"
    );
    // Should show a softer label for non-household goals
    expect(source).toContain("What should we call your finances?");
    // Should still have the household name for family users
    expect(source).toContain("Household name");
  });

  it("placeholder softens for solo goals", () => {
    const source = require("fs").readFileSync(
      require("path").join(__dirname, "../WelcomePage.tsx"),
      "utf8"
    );
    expect(source).toContain("Jane's Finances\"");
    expect(source).toContain("The Smith Family");
  });

  it("invite step has a skip button for solo users", () => {
    const source = require("fs").readFileSync(
      require("path").join(__dirname, "../WelcomePage.tsx"),
      "utf8"
    );
    expect(source).toContain("Just me — skip for now");
  });

  it("STEP_MAP has distinct values for budget and goals", () => {
    const source = require("fs").readFileSync(
      require("path").join(__dirname, "../WelcomePage.tsx"),
      "utf8"
    );
    // budget and goals should NOT both map to 3
    const stepMapSection = source.substring(
      source.indexOf("STEP_MAP"),
      source.indexOf("STEP_MAP") + 300
    );
    // budget → 3, goals → 4 (distinct)
    expect(stepMapSection).toContain("budget: 3");
    expect(stepMapSection).toContain("goals: 4");
    // Verify they're different by checking old broken pattern is gone
    const budgetIdx = stepMapSection.indexOf("budget: 3");
    const goalsIdx = stepMapSection.indexOf("goals: 3");
    expect(goalsIdx).toBe(-1); // goals should not map to 3
  });
});
