/**
 * Tests for the centralized member filter API interceptor.
 *
 * The interceptor auto-appends user_id to every GET request based on
 * the member filter state, so individual pages don't need to do it.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const ROOT = resolve(__dirname, "..", "..", "..");

function readSource(relPath: string): string {
  return readFileSync(resolve(ROOT, relPath), "utf-8");
}

describe("Centralized member filter API interceptor", () => {
  const apiSource = readSource("src/services/api.ts");
  const contextSource = readSource("src/contexts/UserViewContext.tsx");

  it("api.ts exports registerMemberFilterGetter", () => {
    expect(apiSource).toContain("export const registerMemberFilterGetter");
  });

  it("api.ts interceptor reads _getMemberFilterUserId on GET requests", () => {
    expect(apiSource).toContain("_getMemberFilterUserId");
    expect(apiSource).toContain('config.method?.toUpperCase() === "GET"');
  });

  it("api.ts interceptor does not overwrite explicit user_id params", () => {
    expect(apiSource).toContain("!config.params.user_id");
  });

  it("UserViewContext imports registerMemberFilterGetter", () => {
    expect(contextSource).toContain("registerMemberFilterGetter");
  });

  it("MemberFilterApiInjector component is defined and rendered", () => {
    expect(contextSource).toContain("const MemberFilterApiInjector");
    expect(contextSource).toContain("<MemberFilterApiInjector");
  });

  it("MemberFilterApiInjector registers getter using effectiveUserId logic", () => {
    expect(contextSource).toContain(
      "viewContext?.selectedUserId ?? memberFilter.memberEffectiveUserId ?? null"
    );
  });

  it("MemberFilterApiInjector cleans up on unmount", () => {
    // Should deregister by returning a cleanup function
    expect(contextSource).toContain("return () => registerMemberFilterGetter");
  });
});
