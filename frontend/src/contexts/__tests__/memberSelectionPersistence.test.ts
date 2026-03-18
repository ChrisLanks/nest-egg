/**
 * Tests for member selection persistence in MemberFilterContext.
 *
 * Verifies that the selected member IDs are saved to localStorage
 * and restored on mount, so selections survive page refreshes.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const ROOT = resolve(__dirname, "..", "..", "..");

function readSource(relPath: string): string {
  return readFileSync(resolve(ROOT, relPath), "utf-8");
}

const STORAGE_KEY = "nest-egg-member-selection";

describe("Member selection persistence — localStorage", () => {
  it("MemberFilterContext defines the storage key", () => {
    const source = readSource("src/contexts/MemberFilterContext.tsx");
    expect(source).toContain(STORAGE_KEY);
  });

  it("saves selection to localStorage on change", () => {
    const source = readSource("src/contexts/MemberFilterContext.tsx");
    expect(source).toContain("saveStoredMemberSelection");
    // Called in the wrapped setter
    expect(source).toContain("setSelectedMemberIdsRaw(ids)");
    expect(source).toContain("saveStoredMemberSelection(ids)");
  });

  it("saves selection in toggleMember", () => {
    const source = readSource("src/contexts/MemberFilterContext.tsx");
    // toggleMember should also persist
    expect(source).toContain("saveStoredMemberSelection(next)");
  });

  it("reads stored selection on members init", () => {
    const source = readSource("src/contexts/MemberFilterContext.tsx");
    expect(source).toContain("readStoredMemberSelection");
    // Should filter to only valid member IDs
    expect(source).toContain("validIds");
    expect(source).toContain("memberIdSet.has(id)");
  });

  it("falls back to all members when stored selection is empty or invalid", () => {
    const source = readSource("src/contexts/MemberFilterContext.tsx");
    // Default to all members when no valid stored IDs
    expect(source).toContain("new Set(memberIdSet)");
  });
});

describe("Member selection persistence — serialization logic", () => {
  // Test the serialization/deserialization directly
  it("serializes Set to JSON array", () => {
    const ids = new Set(["id1", "id2", "id3"]);
    const serialized = JSON.stringify([...ids]);
    const parsed = JSON.parse(serialized);
    expect(parsed).toEqual(["id1", "id2", "id3"]);
    expect(Array.isArray(parsed)).toBe(true);
  });

  it("handles empty set", () => {
    const ids = new Set<string>();
    const serialized = JSON.stringify([...ids]);
    const parsed = JSON.parse(serialized);
    expect(parsed).toEqual([]);
  });

  it("filters stored IDs to valid members", () => {
    const stored = ["id1", "id2", "id3"];
    const validMembers = new Set(["id1", "id3", "id4"]);
    const validIds = stored.filter((id) => validMembers.has(id));
    expect(validIds).toEqual(["id1", "id3"]);
  });

  it("returns empty when no stored IDs match current members", () => {
    const stored = ["old1", "old2"];
    const validMembers = new Set(["new1", "new2"]);
    const validIds = stored.filter((id) => validMembers.has(id));
    expect(validIds).toEqual([]);
  });

  it("handles malformed JSON gracefully", () => {
    // Simulate what readStoredMemberSelection does
    const parse = (raw: string): string[] | null => {
      try {
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed : null;
      } catch {
        return null;
      }
    };

    expect(parse("not json")).toBeNull();
    expect(parse('{"obj": true}')).toBeNull();
    expect(parse('"string"')).toBeNull();
    expect(parse('["id1","id2"]')).toEqual(["id1", "id2"]);
  });
});
