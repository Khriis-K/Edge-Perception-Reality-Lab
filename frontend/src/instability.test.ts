import { describe, expect, test } from "vitest";
import { instabilityLevels } from "./instability";

describe("instabilityLevels", () => {
  test("gives one level per frame, scaled so the clip's worst frame is 1", () => {
    expect(instabilityLevels([0, 1, 4, 2])).toEqual([0, 0.25, 1, 0.5]);
  });

  test("a clip where nothing changed is all 0, not NaN from dividing by zero", () => {
    expect(instabilityLevels([0, 0, 0])).toEqual([0, 0, 0]);
  });

  test("an empty clip has no marks", () => {
    expect(instabilityLevels([])).toEqual([]);
  });

  test("a clip with a single unstable frame marks only that frame", () => {
    expect(instabilityLevels([0, 0.3, 0])).toEqual([0, 1, 0]);
  });
});
