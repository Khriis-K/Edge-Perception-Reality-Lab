import { describe, expect, it } from "vitest";
import type { ExportSummary } from "./api/client";
import { alwaysIncluded, byteSize, exportMeta } from "./reportFormat";

describe("alwaysIncluded", () => {
  it("names a Benchmark run's input by its subset manifest", () => {
    const sections = alwaysIncluded("benchmark");
    expect(sections[0]).toBe("Subset manifest");
    expect(sections).toContain("Worst frames, by frame id");
  });

  it("names a video run's input by its fingerprint and its worst frames by number", () => {
    const sections = alwaysIncluded("video");
    expect(sections[0]).toBe("Input fingerprint");
    expect(sections).toContain("Worst frames, by frame number");
    expect(sections).not.toContain("Subset manifest");
  });

  it("always lists the record every report carries, ending with the citation", () => {
    for (const kind of ["benchmark", "video"] as const) {
      expect(alwaysIncluded(kind)).toEqual(
        expect.arrayContaining([
          "Model and runtime versions",
          "Class mapping and ignore-region rule",
          "Degradation settings",
          "Metric definitions with sample sizes",
          "Limitations",
        ]),
      );
      expect(alwaysIncluded(kind).at(-1)).toBe("Citation: Bijelic et al., CVPR 2020");
    }
  });
});

describe("byteSize", () => {
  it("counts UTF-8 bytes, as the file on disk has them", () => {
    expect(byteSize("abc")).toBe(3);
    expect(byteSize("Clear · day")).toBe(12); // the middle dot is two bytes
    expect(byteSize("")).toBe(0);
  });
});

describe("exportMeta", () => {
  const summary: ExportSummary = {
    id: "20261001-154612-0123456789ab",
    experiment_id: "0123456789ab".padEnd(64, "0"),
    kind: "benchmark",
    title: "Benchmark: seed 0, up to 300 frames per condition",
    display_threshold: 0.25,
    created_at: "2026-10-01T15:46:12Z",
    files: [
      { name: "report.html", size_bytes: 1500 },
      { name: "frames.csv", size_bytes: 600 },
    ],
  };

  it("gives the threshold, how many files and their total size", () => {
    expect(exportMeta(summary)).toBe("threshold 0.25 · 2 files · 2.1 kB");
  });

  it("leaves out the threshold for a video run, which has none", () => {
    const video = { ...summary, kind: "video" as const, display_threshold: null, files: [summary.files[0]] };
    expect(exportMeta(video)).toBe("1 file · 1.5 kB");
  });
});
