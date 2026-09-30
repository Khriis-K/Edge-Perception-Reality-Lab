# 1. Count detections, not objects, on video; defer object tracking

Status: accepted, 2026-09-29

## Context

The spec says every metric shows its number of evaluated objects, and that metrics based on fewer objects than a documented minimum are flagged low n. On labelled dataset frames, each frame is a separate scene, so counting detections is counting objects.

On unlabelled video (the synthetic stability metrics, #4 and #37), they come apart. One car visible for 30 frames is 30 detections but close to one piece of evidence. Counting detections against `LOW_N_OBJECTS = 30` therefore under-warns: in the stub e2e run, retention over 96 detections is not flagged, though they are 2 objects across 48 frames.

Counting distinct objects needs object tracking: linking each frame's boxes to the next frame's so that one car becomes one track.

## Decision

On video, the low-n flag counts detections across frames against the same `LOW_N_OBJECTS` minimum. The inspector states the limit next to the metrics: "Counts are detections across frames; consecutive frames of the same object are not independent evidence."

Object tracking is deferred until after this project. It is not tracked as an open issue.

## Why

- The spec's central question (Further Notes) is failure under real, labelled conditions and whether synthetic degradation predicts it. That runs on dataset frames, where the problem does not arise. Unlabelled video is a secondary mode.
- Tracking fixes only part of the problem. It turns 30 frames of one car into one object, but separate objects in the same street and lighting are still correlated. The note would stay either way.
- Even the minimal version (greedy IoU linking across frames) is an estimated half day of work (not measured), and it has its own failure mode: fast motion drops IoU below the link threshold and splits one object into many tracks, which over-counts just as detections do.

## Consequences

- An unflagged stability metric on video means "enough detections", not "enough evidence". The inspector note is the safeguard.
- If tracking is picked up later, start by measuring box motion between frames on the real sample clip, to see whether IoU linking holds, before choosing between IoU linking and a Kalman tracker such as SORT. Keep track IDs anonymous: the spec excludes person identification.
