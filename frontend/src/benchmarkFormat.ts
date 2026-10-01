/** "fog-night" → "Fog · night". */
export function conditionName(condition: string): string {
  const [weather, light] = condition.split("-");
  return `${weather.charAt(0).toUpperCase()}${weather.slice(1)} · ${light}`;
}

/** A 0-1 metric to two decimals. Undefined (no objects, or nothing predicted) is a dash: it is not zero. */
export function formatMetric(value: number | null): string {
  return value === null ? "—" : value.toFixed(2);
}

/** A display threshold typed by the user, clamped to 0-1; null while the text isn't a number. */
export function parseThreshold(text: string): number | null {
  if (text.trim() === "") return null;
  const value = Number(text);
  return Number.isFinite(value) ? Math.min(Math.max(value, 0), 1) : null;
}
