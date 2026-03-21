/**
 * Tests for RegisterPage password schema and form validation logic.
 *
 * Mirrors the Zod schema from RegisterPage to catch regressions on
 * password rules without rendering Chakra components.
 *
 * @vitest-environment jsdom
 */

import { describe, it, expect } from "vitest";
import { z } from "zod";

// ── Schema mirroring RegisterPage ────────────────────────────────────────────

const currentYear = new Date().getFullYear();

const registerSchema = z
  .object({
    email: z.string().email("Invalid email address"),
    password: z
      .string()
      .min(12, "Password must be at least 12 characters")
      .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
      .regex(/[a-z]/, "Password must contain at least one lowercase letter")
      .regex(/\d/, "Password must contain at least one number")
      .regex(
        /[!@#$%^&*(),.?":{}|<>_\-+=[\]\\;\/`~]/,
        "Password must contain at least one special character",
      ),
    display_name: z.string().min(1, "Name is required"),
    birth_day: z.number().int().min(1).max(31).optional(),
    birth_month: z.number().int().min(1).max(12).optional(),
    birth_year: z
      .number()
      .int()
      .min(1900, "Enter a valid year")
      .max(currentYear, "Enter a valid year")
      .optional(),
  })
  .refine(
    (data) => {
      const set = [data.birth_day, data.birth_month, data.birth_year].filter(
        Boolean,
      ).length;
      return set === 0 || set === 3;
    },
    {
      message: "Provide day, month, and year — or leave all blank",
      path: ["birth_year"],
    },
  );

type FormData = z.infer<typeof registerSchema>;

const valid = (overrides: Partial<FormData> = {}): FormData => ({
  email: "user@example.com",
  password: "BlueSky!2024x",
  display_name: "Jane",
  ...overrides,
});

const parseErrors = (data: unknown): string[] => {
  const result = registerSchema.safeParse(data);
  if (result.success) return [];
  return result.error.errors.map((e) => e.message);
};

// ── Password validation ───────────────────────────────────────────────────────

describe("RegisterPage: password validation", () => {
  it("example password BlueSky!2024x passes", () => {
    expect(parseErrors(valid())).toHaveLength(0);
  });

  it("rejects passwords shorter than 12 characters", () => {
    const errors = parseErrors(valid({ password: "Short1!" }));
    expect(errors.some((e) => e.includes("12 characters"))).toBe(true);
  });

  it("rejects passwords without uppercase", () => {
    const errors = parseErrors(valid({ password: "bluesky!2024x" }));
    expect(errors.some((e) => e.includes("uppercase"))).toBe(true);
  });

  it("rejects passwords without lowercase", () => {
    const errors = parseErrors(valid({ password: "BLUESKY!2024X" }));
    expect(errors.some((e) => e.includes("lowercase"))).toBe(true);
  });

  it("rejects passwords without a number", () => {
    const errors = parseErrors(valid({ password: "BlueSky!Abcdef" }));
    expect(errors.some((e) => e.includes("number"))).toBe(true);
  });

  it("rejects passwords without a special character", () => {
    const errors = parseErrors(valid({ password: "BlueSky12345xyz" }));
    expect(errors.some((e) => e.includes("special character"))).toBe(true);
  });

  it("accepts other valid password patterns", () => {
    const passwords = [
      "Correct#Horse9",
      "MyP@ssw0rd123!",
      "SecurePass1_long",
      "Hello.World99xx",
    ];
    for (const password of passwords) {
      expect(parseErrors(valid({ password }))).toHaveLength(0);
    }
  });
});

// ── Email validation ──────────────────────────────────────────────────────────

describe("RegisterPage: email validation", () => {
  it("valid email passes", () => {
    expect(parseErrors(valid({ email: "test@example.com" }))).toHaveLength(0);
  });

  it("rejects email without @", () => {
    const errors = parseErrors(valid({ email: "notanemail" }));
    expect(errors.some((e) => e.includes("email"))).toBe(true);
  });

  it("rejects empty email", () => {
    const errors = parseErrors(valid({ email: "" }));
    expect(errors.length).toBeGreaterThan(0);
  });
});

// ── Birthday validation ───────────────────────────────────────────────────────

describe("RegisterPage: birthday partial-fill validation", () => {
  it("no birthday fields is valid", () => {
    expect(
      parseErrors(valid({ birth_day: undefined, birth_month: undefined, birth_year: undefined })),
    ).toHaveLength(0);
  });

  it("all three birthday fields set is valid", () => {
    expect(
      parseErrors(valid({ birth_day: 15, birth_month: 6, birth_year: 1990 })),
    ).toHaveLength(0);
  });

  it("only day set is invalid (partial)", () => {
    const errors = parseErrors(
      valid({ birth_day: 15, birth_month: undefined, birth_year: undefined }),
    );
    expect(errors.some((e) => e.includes("day, month, and year"))).toBe(true);
  });

  it("only month and day set is invalid (missing year)", () => {
    const errors = parseErrors(
      valid({ birth_day: 15, birth_month: 6, birth_year: undefined }),
    );
    expect(errors.some((e) => e.includes("day, month, and year"))).toBe(true);
  });

  it("rejects birth_year before 1900", () => {
    const errors = parseErrors(
      valid({ birth_day: 1, birth_month: 1, birth_year: 1899 }),
    );
    expect(errors.some((e) => e.includes("valid year"))).toBe(true);
  });

  it("rejects birth_year in the future", () => {
    const errors = parseErrors(
      valid({ birth_day: 1, birth_month: 1, birth_year: currentYear + 1 }),
    );
    expect(errors.some((e) => e.includes("valid year"))).toBe(true);
  });
});

// ── Display name ──────────────────────────────────────────────────────────────

describe("RegisterPage: display name validation", () => {
  it("non-empty name passes", () => {
    expect(parseErrors(valid({ display_name: "Jane" }))).toHaveLength(0);
  });

  it("empty name fails", () => {
    const errors = parseErrors(valid({ display_name: "" }));
    expect(errors.some((e) => e.includes("Name is required"))).toBe(true);
  });
});
