import { describe, expect, test } from "vitest";
import { formatMs, modelLine } from "./latencyFormat";

const yolox = {
  name: "YOLOX-Nano (COCO)",
  version: "0.1.1rc0",
  runtime: "onnxruntime 1.30.0",
  provider: "CPUExecutionProvider",
  size_bytes: 3_700_000,
};

describe("modelLine", () => {
  test("names the model, its size, the runtime and the provider", () => {
    expect(modelLine(yolox)).toBe("YOLOX-Nano (COCO) · 3.7 MB · onnxruntime 1.30.0 · CPUExecutionProvider");
  });

  test("leaves out what a runner doesn't have", () => {
    const stub = { name: "Stub detector", version: "fixture-1", runtime: "none (deterministic stub)" };

    expect(modelLine(stub)).toBe("Stub detector · none (deterministic stub)");
  });
});

describe("formatMs", () => {
  test("keeps a decimal for short stages and rounds long ones", () => {
    expect(formatMs(0.04)).toBe("0.0 ms");
    expect(formatMs(12.34)).toBe("12.3 ms");
    expect(formatMs(123.6)).toBe("124 ms");
  });
});
