import { describe, expect, test } from "vitest";
import { formatBytes, groupByInput } from "./runHistoryFormat";

const run = (id: string, sample_id: string, sample_title = sample_id) => ({ id, sample_id, sample_title });

describe("groupByInput", () => {
  test("groups runs by their input, keeping the newest-first order inside each group", () => {
    const runs = [run("c", "clip"), run("b", "traffic"), run("a", "clip")];

    expect(groupByInput(runs)).toEqual([
      { sampleId: "clip", title: "clip", runs: [runs[0], runs[2]] },
      { sampleId: "traffic", title: "traffic", runs: [runs[1]] },
    ]);
  });

  test("orders the groups by their newest run", () => {
    const runs = [run("b", "traffic", "Synthetic traffic"), run("a", "clip", "City clip")];

    expect(groupByInput(runs).map((group) => group.title)).toEqual(["Synthetic traffic", "City clip"]);
  });

  test("no runs, no groups", () => {
    expect(groupByInput([])).toEqual([]);
  });
});

describe("formatBytes", () => {
  test.each([
    [0, "0 B"],
    [999, "999 B"],
    [1_000, "1.0 kB"],
    [15_400, "15.4 kB"],
    [2_500_000, "2.5 MB"],
    [3_210_000_000, "3.2 GB"],
  ])("%d bytes is %s", (bytes, text) => {
    expect(formatBytes(bytes)).toBe(text);
  });
});
