/**
 * Each frame's worst-frame score as 0-1, relative to the clip's worst frame, for the instability strip.
 * Relative, so a mark's shade compares frames within one run, not across runs.
 */
export function instabilityLevels(scores: number[]): number[] {
  const worst = Math.max(0, ...scores);
  return scores.map((score) => (worst > 0 ? score / worst : 0));
}
