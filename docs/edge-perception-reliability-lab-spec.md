# Edge Perception Reliability Lab

## Problem Statement

Computer-vision demos often show a pretrained model working under favorable conditions but do not demonstrate whether the model remains useful when imagery is dark, blurred, foggy, noisy, compressed, or captured in genuinely adverse weather. This makes it difficult for a reviewer to judge whether the builder understands real-world perception reliability, edge-compute constraints, uncertainty, evaluation methodology, and failure analysis.

Synthetic degradations alone leave an open question: does a simulated condition affect a model the way the real condition does? Answering that requires labeled imagery captured in real adverse weather.

The user needs a polished, visual project, achievable in roughly two weekends, that demonstrates those skills without requiring custom model training, specialized hardware, cloud deployment, or redistribution of third-party data. The result should be understandable in a short recorded demo and credible to engineers working on autonomous, aerospace, or other safety-conscious systems.

## Solution

Build a locally runnable web application with two complementary evaluation modes that share one detector, one dashboard, and one reporting pipeline.

**Real-Weather Benchmark mode** evaluates a pretrained object detector against human-labeled ground truth from the public SeeingThroughFog dataset (Bijelic et al., CVPR 2020). The dataset contains real-world driving scenes in clear weather, fog, snow, and rain, plus fog-chamber recordings, with 2D and 3D bounding-box annotations and per-sample metadata on weather and illumination. The application reports accuracy metrics broken down by weather condition and object class.

**Synthetic Degradation mode** applies controlled degradations to a clean input and compares clean and degraded inference on the same frames. The input is either a short MP4 (the included sample or a user-provided clip) or a subset of clear-weather dataset frames. The first release supports darkness, Gaussian blur, synthetic fog, Gaussian noise, and JPEG compression. When run on unlabeled video, this mode measures consistency against the clean baseline. When run on labeled dataset frames, it also measures accuracy.

The two modes combine into the project's headline analysis: a **sim-to-real comparison** that asks whether synthetic fog applied to clear-weather frames degrades the detector in the same way, and by a similar amount, as real fog.

Each experiment preserves its configuration and results so the user can compare conditions without rerunning inference. The application presents results as an engineering evaluation, not as an operational decision system. It makes uncertainty and limitations visible, avoids claims of guaranteed correctness, and never redistributes dataset imagery.

## User Stories

### Orientation

1. As a portfolio reviewer, I want to understand the project's purpose immediately, so that I can evaluate it without reading the full repository.
2. As a portfolio reviewer, I want the headline sim-to-real finding shown up front, so that I can see the project's most interesting result in seconds.
3. As a user, I want to choose between Real-Weather Benchmark mode and Synthetic Degradation mode, so that I can run the evaluation that fits my question.

### Dataset setup

4. As a user, I want clear instructions for obtaining SeeingThroughFog from its official source, so that I can set up the dataset without guesswork.
5. As a user, I want to point the application at a local dataset folder, so that the dataset never needs to be copied into the repository.
6. As a user, I want the application to check which required dataset parts are present and report anything missing in plain language, so that setup failures are understandable.
7. As a user, I want to know which dataset parts are actually needed, so that I can skip the lidar, radar, gated, and thermal data and save storage.
8. As a user, I want to verify the downloaded archives against the published checksums, so that I know my copy is intact.
9. As a user, I want to select a fixed, seeded subset of frames per weather condition, so that experiments run quickly and are reproducible.
10. As a user, I want the selected subset saved as a manifest file, so that another person can reproduce exactly the same evaluation.
11. As a user, I want to see how many labeled frames and objects exist per condition and class in my subset, so that I can judge whether the sample is large enough to trust.

### Video input (Synthetic mode)

12. As a user, I want to upload a short MP4 video, so that I can evaluate my own footage without modifying source code.
13. As a user, I want the application to reject unsupported or unsafe file types clearly, so that failures are understandable.
14. As a user, I want to know the recommended video duration and size before uploading, so that I can stay within the application's limits.
15. As a user, I want to preview the uploaded video, so that I can confirm I selected the intended input.
16. As a user, I want to choose a representative sample video included with the project, so that I can run the demo immediately, even without the dataset.

### Degradation configuration

17. As a user, I want to choose a degradation type, so that I can test a specific adverse visual condition.
18. As a user, I want to adjust degradation severity, so that I can observe how model behavior changes progressively.
19. As a user, I want to test darkness, blur, synthetic fog, image noise, and JPEG compression, so that I can approximate low light, motion or focus problems, reduced visibility, a degraded sensor signal, and limited-bandwidth transmission.
20. As a user, I want to apply degradations to clear-weather dataset frames, so that I can measure their effect against real labels.
21. As a user, I want to see the exact experiment settings, so that I can reproduce a result.

### Running experiments

22. As a user, I want the detector run on both clean and degraded versions of the same frames, so that the comparison is controlled.
23. As a user, I want progress feedback while an experiment runs, so that I know the application has not stalled.
24. As a user, I want to cancel or reset an experiment, so that I can recover from an accidental configuration.
25. As a user, I want completed experiment results cached locally, so that switching between dashboard views is responsive.
26. As a user, I want the same input and configuration to produce repeatable results, so that comparisons are meaningful.

### Inspecting frames

27. As a user, I want to see predictions drawn next to ground-truth boxes, so that I can see what the model found and what it missed.
28. As a user, I want each prediction marked as a correct detection, a false alarm, or a class confusion, and each unmatched label marked as a miss, so that errors are explicit and not conveyed by color alone.
29. As a user, I want clean and degraded output shown side by side in Synthetic mode, so that changes are visually obvious.
30. As a user, I want comparison views synchronized to the same frame, so that the evidence is trustworthy.
31. As a user, I want to hide detection overlays temporarily, so that I can inspect the underlying image.
32. As a user, I want to filter displayed detections by confidence threshold, so that I can explore precision-versus-recall behavior.

### Metrics and analysis

33. As a user, I want precision, recall, and average precision per class and per weather condition, so that I can see where the detector is weakest.
34. As a user, I want precision-recall curves for each condition, so that I can see behavior across all thresholds rather than at one arbitrary setting.
35. As a user, I want day and night results separated where the metadata allows, so that illumination is not confused with weather.
36. As a user, I want the sim-to-real view to show the performance drop from synthetic fog next to the drop from real fog, so that I can judge how realistic the simulation is.
37. As a user, I want the number of evaluated objects shown beside every metric, so that small-sample results are not overinterpreted.
38. As a user, I want to see how often clean detections disappear, appear, or change class under synthetic degradation, so that failure modes are explicit even on unlabeled video.
39. As a user, I want a frame-by-frame reliability timeline for video experiments, so that I can locate sudden failures.
40. As a user, I want to see inference latency and frames per second, so that I can evaluate edge-readiness rather than accuracy alone.
41. As a user, I want to see model size and runtime information, so that I understand the compute configuration behind the results.
42. As a user, I want to inspect the worst-performing frames, so that I can understand concrete failure cases.
43. As a user, I want each worst frame to explain why it was ranked as severe, so that the ranking is interpretable.

### Reporting

44. As a user, I want to download a compact experiment report, so that I can share results without rerunning the application.
45. As a user, I want exported results to include configuration, the dataset subset manifest, class mapping, metrics, and limitations, so that screenshots are not mistaken for complete evidence.
46. As a user, I want the report to exclude dataset imagery by default, so that I do not accidentally redistribute data I am not permitted to share.

### Developer and reviewer needs

47. As a developer, I want the detector accessed through a small model-runner interface, so that the initial model can be replaced without changing the dashboard.
48. As a developer, I want dataset loading, class mapping, video decoding, degradation, inference, matching, metrics, and presentation to have clear responsibilities, so that the project remains understandable.
49. As a developer, I want corrupted videos, malformed labels, and missing dataset files to fail with actionable messages, so that debugging does not require reading a stack trace.
50. As a developer, I want deterministic test fixtures, so that the full workflow can be tested quickly without the real dataset.
51. As a developer, I want dependency versions and startup instructions documented, so that another person can reproduce the demo locally.
52. As a portfolio reviewer, I want a one-command startup path, so that evaluating the project requires minimal setup.
53. As a portfolio reviewer, I want an architecture diagram, so that I can understand the data flow quickly.
54. As a portfolio reviewer, I want an honest limitations section, so that I can see the builder understands the difference between a benchmark result and a validated system.
55. As a safety-conscious reviewer, I want the interface to describe detections as model outputs rather than facts, so that uncertainty is not hidden.
56. As a safety-conscious reviewer, I want the project to avoid person identification, facial recognition, weapon classification, and targeting workflows, so that it remains a benign reliability demonstration.
57. As a privacy-conscious user, I want processing to remain local, so that uploaded media and dataset imagery are not sent to an external service.
58. As a user without a GPU, I want a CPU-compatible configuration, so that the demo remains accessible.
59. As a user with accelerated hardware, I want the runtime to use an available supported execution provider, so that inference can run faster without changing behavior.

## Implementation Decisions

### Architecture and runtime

- The product will be a local web application optimized for a single-user demonstration. It will not require accounts, authentication, a remote database, or a hosted backend.
- The initial interface will be built with Streamlit. A separate frontend and API are intentionally deferred.
- Python will own dataset loading, video decoding, degradations, inference, matching, metrics, caching, visualization data, and report creation.
- OpenCV will decode video, read dataset images, apply visual degradations, and render preview artifacts.
- A small pretrained YOLO-family object detector will provide inference. Pretrained weights will be used as-is; custom training and fine-tuning are not required.
- The default runtime will favor a small model variant that works on a typical CPU. ONNX Runtime may be used for portable inference and straightforward latency measurement.
- The detector will sit behind a model-runner boundary. The runner will accept an image and confidence threshold and return normalized detections containing class label, confidence, and bounding-box coordinates.
- The application will detect available execution providers but will always retain a CPU path.

### Dataset integration

- The dataset will not be bundled, mirrored, or redistributed. The README will link to the official download page and explain the registration step, the checksum verification, and the two-stage extraction.
- The application will read only three parts of the dataset: the 8-bit tone-mapped left stereo camera images, the ground-truth label files, and the environment metadata labels (weather, road state, illumination). The README will explain how to skip extracting all other sensors.
- A dataset adapter will parse KITTI-format labels and use only the 2D bounding boxes. 3D box fields will be ignored in this release.
- The exact metadata vocabulary for weather and illumination will be confirmed during initial data inspection. The adapter will map it to a documented, fixed set of evaluation conditions: at minimum clear, fog, snow, and rain, each split into day and night where the metadata allows. Samples whose condition cannot be determined will be excluded and counted in the report.
- Fog-chamber samples will be evaluated as a separate condition and not pooled with real-world fog.
- Subsets will be drawn per condition using a stored seed and a configurable cap (default: a few hundred frames per condition). The selected frame identifiers will be written to a manifest file that is part of the experiment configuration.
- Dataset load failures (missing folders, unreadable images, malformed label lines) will produce plain-language messages naming the missing part, with diagnostic details available for development.

### Class mapping

- The detector's COCO classes will be mapped to the dataset's four main classes through a single documented mapping table:
  - car → PassengerCars
  - truck, bus → LargeVehicles
  - bicycle, motorcycle → RidableVehicles
  - person → Pedestrians
- COCO classes with no counterpart will be excluded from benchmark metrics but kept in raw detection output.
- Objects labeled with the dataset's fallback classes (Vehicle when the vehicle type is ambiguous, Obstacle when vehicle and pedestrian cannot be distinguished) will be treated as ignore regions. They will count as neither hits nor misses, and a prediction that overlaps one will not count as a false alarm.
- Pedestrian evaluation is generic category detection only. No identity, attribute, facial, or biometric analysis will be performed.
- The mapping table and the ignore-region rule will appear in every exported report, because they materially affect the metrics.

### Degradations

- Version one will support exactly five degradations: darkness, Gaussian blur, synthetic fog, Gaussian noise, and JPEG compression.
- Each degradation will have a normalized severity control from zero to one. Transform-specific parameters will be derived from that value and recorded in experiment metadata.
- One degradation will be active per experiment. This keeps attribution clear and prevents a combinatorial configuration problem.
- Randomized degradations will use an explicit seed stored with the experiment so results can be reproduced.
- Degradations will be implemented in this project. The dataset repository's own fog-simulation tooling may be consulted as a reference, and any reuse will be attributed and license-checked.

### Matching and metrics

- Benchmark mode will match predictions to ground truth using class-aware intersection-over-union at a documented threshold (default 0.5). Average precision will be computed per class and condition, and mean average precision will be reported as their mean.
- Benchmark mode will also report precision and recall at the user's selected display threshold, and precision-recall curves for each condition.
- Raw detections will be retained above a low confidence floor before any UI filtering, so that changing the displayed threshold or computing curves never requires rerunning inference.
- Synthetic mode on unlabeled video will match clean and degraded detections with the same class-aware IoU rule. An unmatched clean detection counts as dropped, an unmatched degraded detection counts as newly introduced, and a spatially matched detection with a different label counts as a class change. These metrics will be labeled as stability relative to the clean baseline, never as accuracy, precision, recall, or mAP.
- Synthetic mode on labeled dataset frames will report both the stability metrics and the ground-truth accuracy metrics for clean and degraded versions.
- The sim-to-real comparison will show, for each class, the change in average precision from clear to synthetic fog next to the change from clear to real fog, both evaluated on the same metric definitions. Because the real-fog frames are different scenes from the clear frames, this comparison is distributional rather than paired, and the interface will say so.
- Every metric will display the number of evaluated objects and frames. Metrics based on fewer objects than a documented minimum will be visually flagged as low-confidence.
- Primary metrics will include per-class and per-condition average precision, precision and recall at the display threshold, median inference latency, effective frames per second, median confidence shift, and, for Synthetic mode, detection retention rate, newly introduced detection rate, and class-change count.

### Worst-frame ranking

- In Benchmark mode, the worst-frame score will combine misses, false alarms, and class confusions against ground truth using documented weights.
- In Synthetic mode, the score will combine dropped detections, newly introduced detections, class changes, and aggregate confidence loss using documented weights.
- The dashboard and report will expose each contributing value, not only the combined score.

### Views

- The main view will show the current frame with overlays. In Benchmark mode, predictions and ground truth are drawn together. In Synthetic mode, clean and degraded frames are shown side by side and kept synchronized.
- The analysis view will contain a condition-by-class results table, precision-recall curves, the sim-to-real comparison, confidence distributions, a latency summary, and a worst-frame gallery. Video experiments will additionally show a frame-by-frame reliability timeline. Dataset subsets are not continuous sequences, so they will not show a timeline.

### Caching, timing, and reports

- Completed experiment results will be cached on local disk using an identifier derived from the input fingerprint or subset manifest, model version, class mapping version, confidence floor, degradation type, and severity.
- Cached artifacts will contain derived frames and structured results for local use only. The README will explain how to remove them.
- Timing measurements will distinguish model inference from decoding, degradation, and rendering. Warm-up runs will be excluded, and the measurement method will be documented.
- Reports will be exportable as a self-contained HTML document, with JSON or CSV metric data as an optional supporting artifact.
- Reports will include the input fingerprint or subset manifest, model and runtime versions, class mapping, ignore-region rule, degradation settings, metrics with sample sizes, worst frames, and limitations.
- Dataset imagery will be excluded from reports by default. Worst frames from the dataset will be referenced by frame identifier. Imagery from the user's own video or the bundled sample may be included.
- The README and repository will not publish dataset images, crops, or derived frames unless the dataset's terms of use have been reviewed and permit it. Charts and aggregate metrics will be the default public artifacts.

### Privacy and messaging

- User-provided media and dataset imagery will remain on the local machine. No telemetry or cloud inference will be introduced.
- Error messages will be presented in plain language, with detailed diagnostics available for development.
- The application will explicitly state that it is an educational robustness evaluation and has not been validated for safety-critical or operational use.
- The README will lead with an animated demonstration, a one-paragraph problem statement, the headline sim-to-real finding, setup instructions for both modes, an architecture diagram, metric definitions, the class mapping, limitations, and ethical-use boundaries. It will cite the SeeingThroughFog paper.

## Testing Decisions

- The primary acceptance seam will be the complete browser-visible workflow in both modes. For Benchmark mode, the test will point the app at the fixture dataset, select conditions, run evaluation, inspect results, and export a report. For Synthetic mode, the test will select a valid video, configure one degradation, run synchronized clean/degraded inference, inspect the comparison and metrics, and export a report.
- A deterministic model-runner substitute will be used in acceptance tests. It will return fixed detections for known fixture frames, so the workflow can be exercised without downloading model weights, requiring a GPU, or depending on nondeterministic inference.
- The real dataset will never be required by the test suite. A tiny synthetic fixture will mimic the dataset's folder layout, KITTI label format, and metadata structure. It will include each evaluation condition, each mapped class, a fallback-labeled object, and a malformed label line. The fixture will be generated rather than copied from the real dataset.
- One small synthetic video will serve as the canonical video fixture.
- Acceptance tests will verify externally observable behavior rather than Streamlit internals or private helper functions.
- The dataset adapter will have focused tests covering label parsing, condition assignment, day/night splitting, exclusion of undeterminable samples, missing-folder errors, and deterministic subset selection from a seed.
- The class mapping will have table-driven tests covering every mapped class, unmapped classes, and fallback-class ignore regions.
- The ground-truth matching and metric layer will use table-driven examples covering hits, misses, false alarms, class confusions, ignore regions, empty frames, overlapping boxes, and a small hand-computed average-precision case.
- The stability-matching layer will use table-driven examples covering retained, dropped, introduced, and class-changed detections.
- The model-runner contract will have a focused test verifying normalized coordinates, label and confidence fields, empty results, invalid input handling, and stable model metadata.
- The degradation pipeline will have behavior tests using known images, asserting unchanged dimensions, deterministic seeded output, monotonic darkness, increasing blur, and increasing compression artifacts.
- Persistence tests will verify that identical inputs reuse cached results and that a change in any result-affecting configuration, including the manifest or class mapping, creates a distinct identifier.
- Report tests will verify that exported reports contain configuration, manifest, class mapping, metric definitions with sample sizes, and limitations, and that they contain no dataset imagery by default.
- Performance checks will use generous local thresholds and will detect accidental regressions rather than claim hardware-independent real-time performance.
- Manual verification will be performed once against the real dataset subset, confirming label alignment on a handful of frames, sensible per-condition counts, and legible overlays at narrow and wide browser widths.

## Out of Scope

- Training or fine-tuning an object-detection model.
- Creating or labeling a custom dataset.
- Redistributing, mirroring, or bundling SeeingThroughFog data.
- Using the dataset's lidar, radar, gated, thermal, stereo-disparity, or vehicle-bus data, or performing multi-sensor fusion.
- 3D bounding-box evaluation.
- Claims that benchmark results generalize beyond this dataset, subset, model, and class mapping.
- Facial recognition, person identification, biometric or attribute analysis, weapon classification, target selection, or engagement functionality.
- Live surveillance feeds, drone control, vehicle control, or integration with physical sensors.
- Adversarial-example generation intended to evade perception systems.
- Cloud hosting, cloud inference, user accounts, team collaboration, or remote persistence.
- A production-grade security model or processing of classified, controlled, export-restricted, or otherwise sensitive data.
- Mobile application support.
- Supporting every video codec or arbitrarily long videos.
- Comparing multiple model families in the initial scope.
- Formal model certification, safety assurance, or operational suitability claims.
- Automated conclusions or recommended actions based on detections.

## Further Notes

- The most important demonstration is failure analysis grounded in real labels. The project should make it easy to answer: "Under which real conditions does the model fail, for which classes, by how much, and does synthetic degradation predict that failure?"
- A compelling demo sequence is: open the Benchmark view and show average precision dropping from clear to fog to snow; open a real-fog worst frame showing a missed vehicle; switch to Synthetic mode on clear-weather frames and raise fog severity; show the sim-to-real chart comparing the two drops; export the report.
- The sim-to-real comparison has real confounds. Real fog co-occurs with lower light, different roads, and different traffic, and fog-chamber scenes differ from open-road scenes. The limitations section must say this plainly. A mismatch between synthetic and real results is a legitimate and interesting finding, not a failure of the project.
- Dataset downloads require registration, and the maintainers note that the download service has periodic downtime. Synthetic mode on the bundled sample video must remain fully functional without the dataset, so the project is never blocked on data access.
- Build order: ship Synthetic mode on the bundled video first (the original weekend scope), then add the dataset adapter and class mapping, then Benchmark mode, then the sim-to-real view.
- If time becomes constrained, preserve Synthetic mode end to end, per-condition average precision in Benchmark mode, the class mapping and ignore-region documentation, latency measurement, the worst-frame gallery, and the limitations statement. Defer the precision-recall curves, day/night splitting, and additional styling before removing those elements.
- Success means a reviewer can clone the project, run the synthetic demo with one documented command on CPU, optionally connect a local copy of the dataset and reproduce the benchmark from the committed manifest, understand the system within two minutes, and see both useful model behavior and honest failures.
- Reference: Bijelic et al., "Seeing Through Fog Without Seeing Fog: Deep Multimodal Sensor Fusion in Unseen Adverse Weather," CVPR 2020. Dataset code repository: https://github.com/princeton-computational-imaging/SeeingThroughFog
- No issue tracker is configured in the current workspace, so this specification is saved locally and has not been published or labeled `ready-for-agent`.
