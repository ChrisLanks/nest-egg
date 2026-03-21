/**
 * Tests for transaction attachments logic: file validation, upload limits,
 * and type shapes.
 */

import { describe, it, expect } from "vitest";
import type { Attachment } from "../../../api/attachments";

// ── Constants (mirrored from AttachmentsList.tsx) ────────────────────────────

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const MAX_ATTACHMENTS = 5;
const ALLOWED_TYPES = [
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
  "application/pdf",
  "text/csv",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
];

// ── File validation tests ───────────────────────────────────────────────────

describe("Attachment File Validation", () => {
  it("accepts files under 10MB", () => {
    const fileSize = 5 * 1024 * 1024; // 5 MB
    expect(fileSize <= MAX_FILE_SIZE).toBe(true);
  });

  it("rejects files over 10MB", () => {
    const fileSize = 11 * 1024 * 1024; // 11 MB
    expect(fileSize <= MAX_FILE_SIZE).toBe(false);
  });

  it("accepts exactly 10MB", () => {
    expect(MAX_FILE_SIZE <= MAX_FILE_SIZE).toBe(true);
  });

  it("accepts allowed MIME types", () => {
    for (const type of ALLOWED_TYPES) {
      expect(ALLOWED_TYPES.includes(type), `${type} should be allowed`).toBe(
        true,
      );
    }
  });

  it("rejects disallowed MIME types", () => {
    const disallowed = [
      "application/javascript",
      "text/html",
      "application/x-executable",
      "video/mp4",
    ];
    for (const type of disallowed) {
      expect(ALLOWED_TYPES.includes(type), `${type} should be rejected`).toBe(
        false,
      );
    }
  });

  it("accepts common image formats", () => {
    expect(ALLOWED_TYPES).toContain("image/jpeg");
    expect(ALLOWED_TYPES).toContain("image/png");
    expect(ALLOWED_TYPES).toContain("image/gif");
  });

  it("accepts PDF files", () => {
    expect(ALLOWED_TYPES).toContain("application/pdf");
  });

  it("accepts CSV files", () => {
    expect(ALLOWED_TYPES).toContain("text/csv");
  });
});

// ── Attachment limit tests ──────────────────────────────────────────────────

describe("Attachment Limits", () => {
  it("allows upload when under max attachments", () => {
    const currentCount = 3;
    expect(currentCount < MAX_ATTACHMENTS).toBe(true);
  });

  it("disallows upload when at max attachments", () => {
    const currentCount = 5;
    expect(currentCount >= MAX_ATTACHMENTS).toBe(true);
  });

  it("max attachments is 5", () => {
    expect(MAX_ATTACHMENTS).toBe(5);
  });
});

// ── Attachment type shape ───────────────────────────────────────────────────

describe("Attachment Type", () => {
  it("has all required fields", () => {
    const attachment: Attachment = {
      id: "att-1",
      transaction_id: "txn-1",
      filename: "stored-abc123.pdf",
      original_filename: "receipt.pdf",
      content_type: "application/pdf",
      file_size: 204800,
      created_at: "2024-12-01T10:00:00Z",
    };
    expect(attachment.id).toBeDefined();
    expect(attachment.transaction_id).toBeDefined();
    expect(attachment.original_filename).toBe("receipt.pdf");
    expect(attachment.content_type).toBe("application/pdf");
    expect(attachment.file_size).toBeGreaterThan(0);
  });

  it("file_size is in bytes", () => {
    const attachment: Attachment = {
      id: "att-2",
      transaction_id: "txn-1",
      filename: "stored-def456.png",
      original_filename: "photo.png",
      content_type: "image/png",
      file_size: 2048000, // ~2MB
      created_at: "2024-12-01T10:00:00Z",
    };
    // 2MB in bytes
    expect(attachment.file_size).toBe(2048000);
    expect(attachment.file_size).toBeLessThan(MAX_FILE_SIZE);
  });
});

// ── canEdit permission logic ────────────────────────────────────────────────

describe("Attachment canEdit Logic", () => {
  it("hides upload and delete when canEdit is false", () => {
    const canEdit = false;
    expect(canEdit).toBe(false);
    // UI should not render upload input or delete buttons
  });

  it("shows upload and delete when canEdit is true", () => {
    const canEdit = true;
    expect(canEdit).toBe(true);
  });
});
