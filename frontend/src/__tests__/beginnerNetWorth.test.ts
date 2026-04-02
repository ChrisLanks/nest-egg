/**
 * Tests for beginner clarity on NetWorthTimelinePage (AD).
 *
 * AD — Subtitle explains the Assets − Liabilities equation and daily recording.
 *    — Empty state avoids jargon ("snapshots"), explains automatic daily recording.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const srcRoot = join(__dirname, "..");

const nwtSrc = readFileSync(join(srcRoot, "pages/NetWorthTimelinePage.tsx"), "utf-8");

describe("NetWorthTimelinePage beginner clarity (AD)", () => {
  it("subtitle defines Net Worth as Assets minus Liabilities", () => {
    expect(nwtSrc).toMatch(/Net Worth.*=.*Assets.*Liabilities|Assets.*minus.*Liabilities/i);
  });

  it("subtitle explains what Assets and Liabilities mean in plain English", () => {
    expect(nwtSrc).toMatch(/what you own|what you owe/i);
  });

  it("subtitle mentions daily recording so beginners understand data frequency", () => {
    expect(nwtSrc).toMatch(/daily.*snapshot|snapshot.*daily|recorded.*daily/i);
  });

  it("empty state does not use bare 'snapshot' jargon in heading", () => {
    const emptyIdx = nwtSrc.indexOf("No net worth");
    expect(emptyIdx).toBeGreaterThan(-1);
    const area = nwtSrc.slice(emptyIdx, emptyIdx + 50);
    expect(area).not.toMatch(/snapshot/i);
  });

  it("empty state explains recording is automatic (not manual)", () => {
    expect(nwtSrc).toMatch(/recorded.*automatically|automatically.*recorded/i);
  });

  it("empty state avoids 'Check back after tomorrow' phrasing", () => {
    expect(nwtSrc).not.toMatch(/Check back after tomorrow/);
  });

  it("empty state tells beginner when to expect data (tomorrow)", () => {
    expect(nwtSrc).toMatch(/tomorrow/i);
  });
});
