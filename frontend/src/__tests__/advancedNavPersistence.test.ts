/**
 * Tests verifying that the Simple/Advanced toggle persists to the backend.
 *
 * The Layout toggle must call PATCH /settings/profile so the preference
 * syncs across devices (not just localStorage).
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

describe("advanced nav cross-device persistence", () => {
  it("Layout toggle persists to backend via PATCH /settings/profile", () => {
    const layoutSource = readFileSync(
      join(__dirname, "../components/Layout.tsx"),
      "utf-8",
    );
    // The onClick handler should call api.patch with show_advanced_nav
    expect(layoutSource).toContain(
      'api.patch("/settings/profile", { show_advanced_nav: next })',
    );
  });

  it("PreferencesPage toggle persists to backend via PATCH /settings/profile", () => {
    const prefsSource = readFileSync(
      join(__dirname, "../pages/PreferencesPage.tsx"),
      "utf-8",
    );
    expect(prefsSource).toContain(
      'api.patch("/settings/profile", { show_advanced_nav: next })',
    );
  });

  it("authStore seeds localStorage from user.show_advanced_nav on login", () => {
    const authSource = readFileSync(
      join(__dirname, "../features/auth/stores/authStore.ts"),
      "utf-8",
    );
    expect(authSource).toContain("user.show_advanced_nav");
    expect(authSource).toContain("nest-egg-show-advanced-nav");
  });

  it("backend User model has show_advanced_nav column", () => {
    const modelSource = readFileSync(
      join(__dirname, "../../../backend/app/models/user.py"),
      "utf-8",
    );
    expect(modelSource).toContain("show_advanced_nav");
  });

  it("backend UserUpdate schema accepts show_advanced_nav", () => {
    const schemaSource = readFileSync(
      join(__dirname, "../../../backend/app/schemas/user.py"),
      "utf-8",
    );
    expect(schemaSource).toContain("show_advanced_nav");
  });
});
