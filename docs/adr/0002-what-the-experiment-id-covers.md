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

A Benchmark run's id (added 2026-09-30, #11) covers the same things, with the whole subset manifest in place of the input fingerprint:

- the manifest: seed, cap, condition vocabulary version, and every frame id per condition;
- the model's name and version, the class-mapping version and the confidence floor, as above;
- a `"mode": "benchmark"` tag, so it can never equal a Synthetic id.

A Synthetic run on the subset's clear frames (added 2026-09-30, #14) covers what a Benchmark run's id does, plus:

- the clear condition whose frames it degrades (`clear-day` or `clear-night`);
- the degradation type, severity and seed, as for a Synthetic run on video;
- a `"mode": "synthetic-frames"` tag in place of `"benchmark"`.

It takes the whole manifest, not just the degraded condition's frame ids. That costs a re-run when only another condition's draw changes, but it is also what places the run beside a Benchmark run: the degraded condition is listed in a Benchmark run's condition tree only when the two share the same manifest, model and scoring settings.

**The dataset's files are not fingerprinted.** Hashing every image and label file in a subset (thousands of files, gigabytes on the real dataset) on each start would cost more than it protects against: SeeingThroughFog is a fixed, versioned download. So if the local labels or images change under the same frame ids, the cache serves the old results. The record stores each frame's ground truth as it was read, so the results always match what was actually scored. Delete `cache/` after changing the dataset.

## Why

- Content, not path: renaming or moving the sample leaves its cache valid, and replacing the file with other footage under the same name does not.
- Runtime left out: including it would throw away every cached run on each onnxruntime upgrade, and runtime-level differences in detections are small next to the degradations being measured. The stored runtime keeps it honest: a result is never shown as coming from a runtime it didn't use.
- Seed kept in for every kind: dropping it for deterministic kinds would be a per-kind rule that silently breaks if a kind later starts using randomness. A wasted re-run is the cheap failure; a stale hit is the expensive one.

## Consequences

- After an onnxruntime upgrade, identical settings reuse runs made under the old runtime. Delete `cache/` to force fresh runs.
- Changing the stored experiment format without changing the id makes old entries fail to load. They are then treated as absent and re-run, never served half-read.
