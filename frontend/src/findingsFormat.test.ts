import { describe, expect, it } from "vitest";
import { heatmapCellText, reliabilityReason, textColorOn, worstReason } from "./findingsFormat";

const frame = (counts: { hits?: number; misses?: number; false_alarms?: number; class_confusions?: number }) => ({
  id: "f",
  hits: 0,
  misses: 0,
  false_alarms: 0,
  class_confusions: 0,
  ignored: 0,
  score: 0,
  ...counts,
});

const UNIT = { misses: 1, false_alarms: 1, class_confusions: 1 };

describe("worstReason", () => {
  it("names misses against every labelled object when they dominate", () => {
    expect(worstReason(frame({ hits: 1, misses: 3, class_confusions: 1 }), UNIT)).toBe("Missed 3 of 5 labelled objects");
  });

  it("names false alarms when they dominate", () => {
    expect(worstReason(frame({ false_alarms: 2, misses: 1, hits: 1 }), UNIT)).toBe(
      "2 detections where nothing is labelled (false alarms)",
    );
    expect(worstReason(frame({ false_alarms: 1 }), UNIT)).toBe("1 detection where nothing is labelled (a false alarm)");
  });

  it("names class confusions when they dominate", () => {
    expect(worstReason(frame({ class_confusions: 2, hits: 1 }), UNIT)).toBe("2 objects found but given the wrong class");
  });

  it("weighs each count by the score's own weights", () => {
    const heavyConfusions = { misses: 1, false_alarms: 1, class_confusions: 3 };
    expect(worstReason(frame({ misses: 2, class_confusions: 1 }), heavyConfusions)).toBe(
      "1 object found but given the wrong class",
    );
  });

  it("breaks ties toward misses, then false alarms", () => {
    expect(worstReason(frame({ misses: 1, false_alarms: 1, class_confusions: 1 }), UNIT)).toBe("Missed 1 of 2 labelled objects");
    expect(worstReason(frame({ false_alarms: 1, class_confusions: 1 }), UNIT)).toBe(
      "1 detection where nothing is labelled (a false alarm)",
    );
  });
});

const point = (counts: { dropped?: number; introduced?: number; class_changes?: number; confidence_loss?: number }) => ({
  index: 0,
  score: 0,
  retained: 0,
  dropped: 0,
  introduced: 0,
  class_changes: 0,
  confidence_loss: 0,
  ...counts,
});

const UNIT_STABILITY = { dropped: 1, introduced: 1, class_changes: 1, confidence_loss: 1 };

describe("reliabilityReason", () => {
  it("names the largest contribution to the stability score", () => {
    expect(reliabilityReason(point({ dropped: 2, introduced: 1 }), UNIT_STABILITY)).toBe("2 clean detections lost under the degradation");
    expect(reliabilityReason(point({ introduced: 1 }), UNIT_STABILITY)).toBe("1 detection appeared that the clean frame lacks");
    expect(reliabilityReason(point({ class_changes: 2, confidence_loss: 0.4 }), UNIT_STABILITY)).toBe("2 detections changed class");
    expect(reliabilityReason(point({ dropped: 1, confidence_loss: 0.6 }), { ...UNIT_STABILITY, confidence_loss: 2 })).toBe(
      "Matched detections lost 0.60 confidence in total",
    );
    expect(reliabilityReason(point({ confidence_loss: 0.42, dropped: 0 }), UNIT_STABILITY)).toBe(
      "Matched detections lost 0.42 confidence in total",
    );
  });
});

describe("heatmapCellText", () => {
  it("shows AP to two decimals, a star when low n, and a dash when there are no objects", () => {
    expect(heatmapCellText({ class_name: "x", ap: 0.5, objects: 40, frames: 9, low_n: false })).toBe("0.50");
    expect(heatmapCellText({ class_name: "x", ap: 0.5, objects: 2, frames: 1, low_n: true })).toBe("0.50*");
    expect(heatmapCellText({ class_name: "x", ap: null, objects: 0, frames: 0, low_n: true })).toBe("—");
  });
});

describe("textColorOn", () => {
  it("puts black text on light fills and white on dark ones, whichever contrasts more", () => {
    expect(textColorOn("rgb(255, 255, 255)")).toBe("#000000");
    expect(textColorOn("rgb(138, 187, 255)")).toBe("#000000"); // BLUE5
    expect(textColorOn("rgb(47, 52, 60)")).toBe("#ffffff"); // DARK_GRAY3
    expect(textColorOn("rgb(90, 110, 140)")).toBe("#ffffff");
  });
});
