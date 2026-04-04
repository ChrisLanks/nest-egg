/**
 * Tests that attachment API paths match the backend routes.
 *
 * Backend mounts attachments at /api/v1 (no extra prefix):
 *   POST /transactions/{id}/attachments
 *   GET  /transactions/{id}/attachments
 *   GET  /attachments/{id}/download
 *   DELETE /attachments/{id}
 *
 * Frontend must NOT add an extra /attachments/ prefix.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const ROOT = resolve(__dirname, "..", "..", "..", "..");

function readSource(relPath: string): string {
  return readFileSync(resolve(ROOT, relPath), "utf-8");
}

describe("Attachment API paths — no double prefix", () => {
  const source = readSource("src/api/attachments.ts");

  it("list uses /transactions/{id}/attachments (no /attachments/ prefix)", () => {
    expect(source).toContain("`/transactions/${transactionId}/attachments`");
    expect(source).not.toContain("/attachments/transactions/");
  });

  it("upload uses /transactions/{id}/attachments", () => {
    // POST path should match list path
    expect(source).toContain("`/transactions/${transactionId}/attachments`");
  });

  it("download uses /attachments/{id}/download (single prefix)", () => {
    expect(source).toContain("/attachments/${attachmentId}/download");
    expect(source).not.toContain("/attachments/attachments/");
  });

  it("delete uses /attachments/{id} (single prefix)", () => {
    expect(source).toContain("`/attachments/${attachmentId}`");
    expect(source).not.toContain("/attachments/attachments/");
  });
});
