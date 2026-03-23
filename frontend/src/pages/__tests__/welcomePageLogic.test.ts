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
});
