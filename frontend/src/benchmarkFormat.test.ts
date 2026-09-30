import { describe, expect, test } from "vitest";
import { conditionName, formatMetric, parseThreshold } from "./benchmarkFormat";

describe("conditionName", () => {
  test("splits weather and light", () => {
    expect(conditionName("fog-night")).toBe("Fog · night");
    expect(conditionName("clear-day")).toBe("Clear · day");
  });
});

describe("formatMetric", () => {
  test("two decimals", () => {
    expect(formatMetric(0.5)).toBe("0.50");
    expect(formatMetric(0)).toBe("0.00");
    expect(formatMetric(1)).toBe("1.00");
  });

  test("an undefined metric is a dash, never zero", () => {
    expect(formatMetric(null)).toBe("—");
  });
});

describe("parseThreshold", () => {
  test("accepts values from 0 to 1", () => {
    expect(parseThreshold("0.5")).toBe(0.5);
    expect(parseThreshold("0")).toBe(0);
    expect(parseThreshold("1")).toBe(1);
  });

  test("clamps values outside 0 to 1", () => {
    expect(parseThreshold("1.7")).toBe(1);
    expect(parseThreshold("-0.2")).toBe(0);
  });

  test("gives null for text that isn't a number, so the last good threshold stays", () => {
    expect(parseThreshold("")).toBeNull();
    expect(parseThreshold("abc")).toBeNull();
  });
});
