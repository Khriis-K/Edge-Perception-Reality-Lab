# 2. What the experiment id covers

Status: accepted, 2026-09-30

## Context

Finished experiments are cached on disk, and a run whose id is already cached reuses the stored results (#5). The id decides when two runs count as the same. If it leaves out something that changes the results, the cache serves stale results as if they were new, with nothing on screen to show it. If it includes something that doesn't change them, the only cost is an extra run.

## Decision

The id is the sha256 of a canonical JSON of:

- the input fingerprint: the sha256 of the video file's content, not its path or name;
- the model's name and version (for YOLOX, the version includes the weights' sha256);
- the class-mapping version;
- the confidence floor;
- the degradation type, severity and seed.

Two deliberate choices:

- **The runtime is left out.** The onnxruntime build and execution provider are not part of the id. The same weights on another build are treated as the same model. The runtime a run actually used is still stored with it and shown with the results.
- **The seed is kept in, even where it is inert.** The seed stays in the id even for kinds that don't draw from it (everything except noise). A blur run at seed 0 and at seed 1 are separate entries with identical results.

The subset manifest joins the id when Benchmark runs exist.

## Why

- Content, not path: renaming or moving the sample leaves its cache valid, and replacing the file with other footage under the same name does not.
- Runtime left out: including it would throw away every cached run on each onnxruntime upgrade, and runtime-level differences in detections are small next to the degradations being measured. The stored runtime keeps it honest: a result is never shown as coming from a runtime it didn't use.
- Seed kept in for every kind: dropping it for deterministic kinds would be a per-kind rule that silently breaks if a kind later starts using randomness. A wasted re-run is the cheap failure; a stale hit is the expensive one.

## Consequences

- After an onnxruntime upgrade, identical settings reuse runs made under the old runtime. Delete `cache/` to force fresh runs.
- Changing the stored experiment format without changing the id makes old entries fail to load. They are then treated as absent and re-run, never served half-read.
