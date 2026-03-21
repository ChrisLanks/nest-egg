/**
 * Shared milestone celebration logic.
 *
 * Used by MilestoneCelebration component and milestone tests.
 */

export const MILESTONE_EMOJIS: Record<string, string> = {
  "$10,000": "\u{1F3AF}",
  "$25,000": "\u{1F680}",
  "$50,000": "\u{1F4AA}",
  "$100,000": "\u{1F525}",
  "$250,000": "\u2B50",
  "$500,000": "\u{1F3C6}",
  "$1,000,000": "\u{1F451}",
  "$2,500,000": "\u{1F48E}",
  "$5,000,000": "\u{1F31F}",
  "$10,000,000": "\u{1F3F0}",
};

/**
 * Extract the dollar threshold from a milestone notification title.
 * e.g. "Milestone reached: $1,000,000!" -> 1000000
 */
export function extractThreshold(title: string): number {
  // Sort by label length descending so "$10,000,000" matches before "$10,000"
  const sorted = Object.keys(MILESTONE_EMOJIS).sort(
    (a, b) => b.length - a.length,
  );
  for (const label of sorted) {
    if (title.includes(label)) {
      return Number(label.replace(/[$,]/g, ""));
    }
  }
  return 0;
}

export function getEmoji(title: string): string {
  // Sort by key length descending so "$10,000,000" matches before "$10,000"
  const sorted = Object.entries(MILESTONE_EMOJIS).sort(
    ([a], [b]) => b.length - a.length,
  );
  for (const [threshold, emoji] of sorted) {
    if (title.includes(threshold)) return emoji;
  }
  return "\u{1F389}";
}
