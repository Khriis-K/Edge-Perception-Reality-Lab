# Edge Perception Reliability Lab

## Problem Statement

Computer-vision demos often show a pretrained model working under favorable conditions but do not demonstrate whether the model remains useful when imagery is dark, blurred, foggy, noisy, compressed, or captured in genuinely adverse weather. This makes it difficult for a reviewer to judge whether the builder understands real-world perception reliability, edge-compute constraints, uncertainty, evaluation methodology, and failure analysis.

Synthetic degradations alone leave an open question: does a simulated condition affect a model the way the real condition does? Answering that requires labeled imagery captured in real adverse weather.

The user needs a polished, visual project, achievable in roughly three weekends, that demonstrates those skills without requiring custom model training, specialized hardware, cloud deployment, or redistribution of third-party data. The result should be understandable in a short recorded demo and credible to engineers working on autonomous, aerospace, or other safety-conscious systems.

## Solution

Build a locally runnable web application with two complementary evaluation modes that share one detector, one dashboard, and one reporting pipeline. A Python service runs all data processing and inference behind a small local API, and a custom React frontend presents the results, giving full control over layout, overlays, and visualization.

**Real-Weather Benchmark mode** evaluates a pretrained object detector against human-labeled ground truth from the public SeeingThroughFog dataset (Bijelic et al., CVPR 2020). The dataset contains real-world driving scenes in clear weather, fog, snow, and rain, with 2D and 3D bounding-box annotations and per-sample metadata on weather and illumination. The application reports accuracy metrics broken down by weather condition and object class.

**Synthetic Degradation mode** applies controlled degradations to a clean input and compares clean and degraded inference on the same frames. The input is either a short MP4 (the included sample or a user-provided clip) or a subset of clear-weather dataset frames. The first release supports darkness, Gaussian blur, synthetic fog, Gaussian noise, and JPEG compression. When run on unlabeled video, this mode measures consistency against the clean baseline. When run on labeled dataset frames, it also measures accuracy.

The two modes combine into the project's headline analysis: a **sim-to-real comparison** that asks whether synthetic fog applied to clear-weather frames degrades the detector in the same way, and by a similar amount, as real fog.

A separate **fog-chamber case study** uses the PixelAccurateBenchmark dataset (Gruber et al., 3DV 2019): four static scenes recorded in an indoor fog chamber, each with a clear reference and real fog at known visibilities from 20 to 100 m. Because each scene is identical across fog levels, it pairs real and synthetic fog on the same scene. The case study is not a Benchmark-mode condition and is never pooled with road fog.

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
8. As a user, I want to verify the downloaded archives against the published checksums, so that I know my copy is intact. *(Conditional: kept only if upstream publishes checksums for the per-folder split archives. Otherwise dropped, because zip's per-file CRC32 already catches corruption at extraction.)*
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
60. As a developer, I want the frontend and backend to communicate through a documented, typed local API, so that either side can change without breaking the other.
61. As a user, I want long-running experiments to report progress and remain cancellable from the browser, so that the interface never appears frozen.
62. As a portfolio reviewer, I want to run the finished app without installing a JavaScript toolchain, so that setup stays limited to Python.

### Workbench interaction

63. As a user, I want a consistent workbench layout on every screen, so that I always know where navigation, details, and job status live.
64. As a user, I want to keep several frames and views open in tabs, so that I can compare them without losing my place.
65. As a user, I want an inspector that explains whatever I select, so that I can drill into a detection or run without leaving the view.
66. As a user, I want a command palette, so that I can jump to any frame, run, or finding and start actions without hunting through menus.
67. As a user, I want keyboard shortcuts for frame navigation and overlay toggles, so that reviewing hundreds of frames is fast.
68. As a portfolio reviewer, I want the findings presented as a few headline statements backed by charts, so that I can understand the results in under a minute.
69. As a developer reviewing the project, I want to see the API request a run will send, so that the frontend–backend boundary is visible and inspectable.

### Fog-chamber case study

70. As a user, I want to see, for each object in a fog-chamber scene, the fog visibility at which the detector stops finding it under real fog and under synthetic fog, so that I can compare the two on identical scenes.
71. As a portfolio reviewer, I want the case study clearly labeled as a small case study with project-made annotations, so that I do not read it as a statistical result.

## Implementation Decisions

### Architecture and runtime

- The product will be a local web application optimized for a single-user demonstration. It will not require accounts, authentication, a remote database, or a hosted backend.
- The system will have two parts: a Python backend service and a browser frontend. They will run on the same machine and communicate only through a local HTTP API.
- The backend will use FastAPI. Request and response models will be defined with Pydantic so the API has a generated OpenAPI schema, and frontend TypeScript types will be generated from that schema rather than written by hand.
- The frontend will be a single-page application built with React, TypeScript, and Vite. It will own layout, interaction state, and visualization only. It will perform no inference, matching, or metric calculation.
- The frontend will use Blueprint, Palantir's open-source React UI toolkit, for controls, tables, trees, tabs, and dark-theme styling. Blueprint supplies components and color tokens; the layout and visual design are original to this project (see Visual design).
- Bounding-box overlays will be drawn in an SVG or canvas layer positioned over the frame image, using the normalized coordinates returned by the API, so overlays stay aligned at any display size and can be toggled or filtered without new server requests.
- Charts (timeline, heatmap, precision-recall curves, distributions, sim-to-real bars) will be built with D3 or visx. Chart inputs will be structured data from the API, not pre-rendered images.
- Experiments will run as background jobs on the backend. Starting a run returns a job identifier. The frontend reads progress through server-sent events, falling back to polling. A cancel endpoint stops the job cleanly, and a partially completed job is never written to the cache as complete.
- The API will expose resources for dataset status, subsets and manifests, sample and uploaded videos, experiments and jobs, per-frame results, frame images from the local cache, aggregate metrics, and report export. Endpoint names and payloads will be documented in the generated schema.
- Frame images will be served from the local cache by experiment and frame identifier. The API will never accept arbitrary file paths from the browser, and served paths will be restricted to the configured dataset folder and cache directory.
- For normal use, FastAPI will serve the built frontend as static files, so a single command starts the whole application on one local port. A separate Vite dev server with hot reload will be used only during frontend development.
- Release builds will include the prebuilt frontend bundle, so reviewers need only Python to run the project. Node.js is required only to modify the frontend.
- Python will own dataset loading, video decoding, degradations, inference, matching, metrics, caching, visualization data, and report creation.
- OpenCV will decode video, read dataset images, apply visual degradations, and render preview artifacts.
- A small pretrained YOLO-family object detector will provide inference. Pretrained weights will be used as-is; custom training and fine-tuning are not required.
- The default runtime will favor a small model variant that works on a typical CPU. ONNX Runtime may be used for portable inference and straightforward latency measurement.
- The detector will sit behind a model-runner boundary. The runner will accept an image and confidence threshold and return normalized detections containing class label, confidence, and bounding-box coordinates.
- The application will detect available execution providers but will always retain a CPU path.

### Dataset integration

- The dataset will not be bundled, mirrored, or redistributed. The README will link to the official download page and explain the registration step and the extraction. The download is split per folder (for example `cam_stereo_left_lut.z01`…`.zNN` plus `.zip`); there is no single combined archive. Integrity checking follows user story 8: if upstream publishes checksums for the per-folder archives, a command verifies them. Otherwise the README tells the user to check that every `.z01`…`.zNN` part is present and that extraction finishes with no CRC errors.
- The application will read only three parts of the dataset: the 8-bit tone-mapped left stereo camera images, the ground-truth label files, and the environment metadata labels (weather, road state, illumination). The README will explain how to skip extracting all other sensors.
- A dataset adapter will parse KITTI-format labels and use only the 2D bounding boxes. 3D box fields will be ignored in this release.
- The adapter will read the refined metadata (`labeltool_labels_refined`), not the original `labeltool_labels`. Data inspection is recorded in `docs/research/seeingthroughfog-data-inspection.md`. The refined files record fog (`fog.yes.denseFog`, `fog.yes.lightFog`) and precipitation (`precipitation.yes.rain`, `precipitation.yes.snow.*`) on separate axes, plus `daytime` and `twilight`. The adapter maps them to a documented, fixed set of evaluation conditions: clear, fog, snow and rain, each split into day and night.
- Samples whose condition cannot be determined will be excluded and counted in the report. This includes samples with fog plus rain or snow, and samples marked twilight. Before that exclusion rule is committed, the number of mixed fog-plus-precipitation samples will be counted. If they are a large share of all fog samples, a precedence rule will be proposed instead of exclusion. Counted: fog plus snow is 53% of fog (there is no fog plus rain), but 1,353 fog-only frames remain. Exclusion was kept, because a precedence rule would mix two effects into one condition. The cost is that the fog condition is about 81% dense fog (see the data inspection notes).
- The original and refined files disagree on day or night for 711 samples. Once images are available, about a dozen of them will be spot-checked visually, and which file is right will be recorded.
- SeeingThroughFog contains no fog-chamber samples: its labelled release is road driving only. Fog-chamber data comes from PixelAccurateBenchmark and is never a Benchmark-mode condition (see Fog-chamber case study).
- Subsets will be drawn per condition using a stored seed and a configurable cap (default: a few hundred frames per condition). The selected frame identifiers will be written to a manifest file that is part of the experiment configuration.
- Dataset load failures (missing folders, unreadable images, malformed label lines) will produce plain-language messages naming the missing part, with diagnostic details available for development.

### Fog-chamber case study

- Source: PixelAccurateBenchmark, from the same download service as SeeingThroughFog. The app reads only the 8-bit left camera images (`rgb_left_8bit`, named `scene{1-4}_{day,night}_{condition}_{0-9}.png`). Conditions are `clear`, `fog20` to `fog100` in 5 m steps of meteorological visibility, and `rain15` and `rain55`. Other parts of the archive are not needed, unless depth is chosen for the fog model (see below).
- It is evaluated in a separate sim-to-real case study. It is never pooled with road fog, never shown in the Benchmark condition table, and never part of Benchmark-mode metrics.
- Ground truth is hand-drawn 2D boxes on the 8 clear frames (4 scenes × day and night), drawn by the project author. They are not seeded from detector output, because ground truth proposed by the model under test is circular. Before boxes are reused across conditions, every scene is confirmed static (camera and objects unmoved) across fog levels, by day and by night.
- The annotations are labeled everywhere as project-made. The class mapping and ignore-region rule are the same as in Benchmark mode. Every object stays in the ground truth at every fog level, even where fog makes it physically invisible. That is intended, because the question is when the detector loses it.
- The primary metric is per-object **breakdown visibility**: the fog visibility at which the object stops being detected (class-aware IoU 0.5). It is measured under real chamber fog and under synthetic fog applied to the clear frame, paired on the same scene. Results are reported per visibility level, never as AP or a pooled row. With about four independent scenes, AP would be noise.
- The interface and report state that this is a case study, not a statistical result.
- Open decision (tracked separately): pairing "synthetic fog at visibility X" with "real fog at X" requires mapping synthetic fog severity (a normalized 0–1 value) to meteorological visibility. A physical model (Koschmieder, β = 3/V) needs per-pixel depth, which PixelAccurateBenchmark ships as depth ground truth. The alternative is an empirical severity-to-visibility calibration. This is not decided yet.

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

### Interface layout: the workbench

- The application will use a single workbench layout on every screen, modeled on analyst tools rather than a dashboard of cards. From left to right it has:
  - a top bar with breadcrumbs, command search, a local-server status indicator, and an Export report action;
  - a narrow icon rail for navigation;
  - an explorer panel on the left;
  - a central work area with tabs;
  - an inspector panel on the right.

  A bottom dock appears on screens that stream or tabulate data.
- The rail contains five sections: Setup, Benchmark, Synthetic, Findings, and Report. The active section is marked with a visible indicator, not by color alone.
- The explorer adapts to the section:
  - Setup lists runs and a New run entry.
  - Benchmark shows a tree of conditions, each with its mAP, expanding to frames sorted by error score.
  - Synthetic lists synthetic runs grouped by input.
  - Findings shows an outline of the findings and a condition list.
  - Report lists previous exports.
- The inspector shows details for whatever is selected: a detection, a frame, a run, or an export. It never holds primary content that is unavailable elsewhere.
- The work area supports multiple tabs, so a user can keep several frames or views open and switch between them without losing state.

### Screens

- **Setup.** A New run form with the mode choice, dataset folder and checks, and the subset table. The inspector shows a live preview of the exact API request the run will send, plus the class mapping. Starting a run returns immediately and hands off to the job stream.
- **Benchmark.** A frame viewer with ground-truth and prediction overlays, each marked as a hit, miss, false alarm, class confusion, or ignored region. A toolbar toggles labels, predictions, and ignore regions and sets the display threshold. The bottom dock has two tabs:
  - a Job tab showing streamed progress events, per-condition completion, latency, and warnings, with a Cancel control;
  - a Frame table tab.

  The inspector shows the selected detection (IoU, normalized box, error weight), the frame's error counts, and per-class AP for this condition compared with clear weather.
- **Synthetic.** Clean and degraded frames side by side, always synchronized, with a per-frame instability strip and a scrubber. The dock shows the current frame's match table. The inspector holds the degradation choice, severity, derived parameters, seed, stability metrics, and latency.
- **Findings.** A findings-first document rather than a grid of charts. It is organized as numbered findings, each led by a one-sentence plain-language headline, followed by the evidence:
  - Finding 01, sim-to-real: headline numbers and paired per-class drop bars.
  - Finding 02, where the detector fails: the condition-by-class AP heatmap.
  - Finding 03: precision-recall curves.
  - The worst-frame gallery.

  Headlines are written by the user from the results, not generated automatically. The inspector shows the run record, latency, and a "read this first" limitations summary. Video experiments additionally show a frame-by-frame reliability timeline. Dataset subsets are not continuous sequences, so they do not.
- **Report.** A live preview of the exported HTML report in the work area, with tabs for the JSON and CSV outputs. The inspector holds file choices, the dataset-imagery toggle (off by default, with a warning when enabled), the list of always-included sections, and the export action.

### Command palette and keyboard

- A command palette opens with Cmd/Ctrl+K from anywhere. It searches frames, runs, and conditions, and runs actions such as starting a synthetic condition, opening a finding, comparing a frame, or exporting a report. Each result shows whether it will use cached results or start a new job.
- Core navigation will be available from the keyboard:
  - arrow keys move between frames;
  - L and P toggle labels and predictions;
  - short "g" sequences jump between sections.

  Shortcuts will be listed in the palette and shown as hints under the frame viewer.
- Shortcuts will be ignored while focus is in a text input, and every shortcut action will also be reachable by mouse.

### Visual design

- The interface will use a dark, low-chrome visual style inspired by Palantir's aesthetic:
  - a pure-black top bar and rail over slate-gray panels;
  - white for primary actions, selection, and the active section;
  - tight corner radii;
  - dense, small type.
- Colors will come from Blueprint's open-source palette. Blue marks clean results and hits; orange marks degraded results and errors. The two colors also differ in lightness, and every overlay carries a text label, so meaning never depends on color alone.
- The exported report will use a light layout: a black header band, white page, and the same numbered-findings structure, so it prints and shares cleanly.
- No Palantir logos, product names, or proprietary screen designs will be used. The design takes inspiration from the palette and density, not from any specific product.
- Text will meet WCAG AA contrast. All controls will be real buttons, links, or labeled inputs, and icon-only rail buttons will carry accessible names.
- The workbench targets desktop widths of 1280 px and above. Below that, the inspector collapses into a drawer rather than squeezing the frame viewer.

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
- The backend will bind to 127.0.0.1 only. Cross-origin requests will be disabled in normal use and allowed only from the local Vite dev server during development.
- The frontend will load no third-party scripts, fonts, or analytics at runtime; all assets will be bundled locally.
- Error messages will be presented in plain language, with detailed diagnostics available for development.
- The application will explicitly state that it is an educational robustness evaluation and has not been validated for safety-critical or operational use.
- The README will lead with an animated demonstration, a one-paragraph problem statement, the headline sim-to-real finding, setup instructions for both modes, an architecture diagram, metric definitions, the class mapping, limitations, and ethical-use boundaries. It will cite the SeeingThroughFog and PixelAccurateBenchmark papers and link each dataset's terms of use.

## Testing Decisions

- The primary acceptance seam will be the complete browser-visible workflow in both modes. For Benchmark mode, the test will point the app at the fixture dataset, select conditions, run evaluation, inspect results, and export a report. For Synthetic mode, the test will select a valid video, configure one degradation, run synchronized clean/degraded inference, inspect the comparison and metrics, and export a report.
- A deterministic model-runner substitute will be used in acceptance tests. It will return fixed detections for known fixture frames, so the workflow can be exercised without downloading model weights, requiring a GPU, or depending on nondeterministic inference.
- The real dataset will never be required by the test suite. A tiny synthetic fixture will mimic the dataset's folder layout, KITTI label format, and refined metadata structure. It will include each evaluation condition, each mapped class, a fallback-labeled object, a malformed label line, and samples excluded as undeterminable (fog plus precipitation, and twilight). The fixture will be generated rather than copied from the real dataset.
- The fixture will also include a PixelAccurateBenchmark-style chamber sample: one scene with a clear frame and fog frames at a few visibilities, following the real file naming, plus its project-made boxes. It too will be generated, never copied.
- One small synthetic video will serve as the canonical video fixture.
- Acceptance tests will be written with Playwright and drive a real browser against the built frontend served by the backend, exactly as a reviewer would run it.
- Acceptance tests will verify externally observable behavior rather than React component internals or private helper functions.
- The API will have contract tests that exercise each endpoint through its HTTP interface, covering valid requests, validation errors, job progress and cancellation, and rejection of paths outside the dataset and cache folders.
- A check will fail the build if the generated TypeScript types are out of date with the backend schema.
- Frontend unit tests will be limited to logic worth isolating, such as overlay coordinate transforms and threshold filtering. Visual components will be covered by the acceptance suite rather than snapshot tests.
- The dataset adapter will have focused tests covering label parsing, condition assignment, day/night splitting, exclusion of undeterminable samples, missing-folder errors, and deterministic subset selection from a seed.
- The class mapping will have table-driven tests covering every mapped class, unmapped classes, and fallback-class ignore regions.
- The ground-truth matching and metric layer will use table-driven examples covering hits, misses, false alarms, class confusions, ignore regions, empty frames, overlapping boxes, and a small hand-computed average-precision case.
- The stability-matching layer will use table-driven examples covering retained, dropped, introduced, and class-changed detections.
- The model-runner contract will have a focused test verifying normalized coordinates, label and confidence fields, empty results, invalid input handling, and stable model metadata.
- The degradation pipeline will have behavior tests using known images, asserting unchanged dimensions, deterministic seeded output, monotonic darkness, increasing blur, and increasing compression artifacts.
- Persistence tests will verify that identical inputs reuse cached results and that a change in any result-affecting configuration, including the manifest or class mapping, creates a distinct identifier.
- Report tests will verify that exported reports contain configuration, manifest, class mapping, metric definitions with sample sizes, and limitations, and that they contain no dataset imagery by default.
- Performance checks will use generous local thresholds and will detect accidental regressions rather than claim hardware-independent real-time performance.
- Manual verification will be performed once against the real dataset subset. It will confirm label alignment on a handful of frames, sensible per-condition counts, and legible overlays at 1280 px and wider, and it will check the collapsed-inspector layout below 1280 px.
- The acceptance suite will cover the command palette (open, search, run an action), the keyboard shortcuts (frame navigation, overlay toggles, and no firing while typing in inputs), tab switching without state loss, and the inspector updating on selection.
- An automated accessibility check (for example, axe run through Playwright) will run on each screen and fail the build on contrast violations or unlabeled controls.

## Out of Scope

- Training or fine-tuning an object-detection model.
- Creating or labeling a custom dataset. The one exception is hand-drawn boxes on the 8 clear PixelAccurateBenchmark frames for the fog-chamber case study.
- Redistributing, mirroring, or bundling SeeingThroughFog or PixelAccurateBenchmark data.
- Using the dataset's lidar, radar, gated, thermal, stereo-disparity, or vehicle-bus data, or performing multi-sensor fusion.
- 3D bounding-box evaluation.
- Claims that benchmark results generalize beyond this dataset, subset, model, and class mapping.
- Facial recognition, person identification, biometric or attribute analysis, weapon classification, target selection, or engagement functionality.
- Live surveillance feeds, drone control, vehicle control, or integration with physical sensors.
- Adversarial-example generation intended to evade perception systems.
- Cloud hosting, cloud inference, user accounts, team collaboration, or remote persistence.
- A publicly deployed frontend, server-side rendering, or an API reachable from other machines.
- A production-grade security model or processing of classified, controlled, export-restricted, or otherwise sensitive data.
- Mobile application support.
- Supporting every video codec or arbitrarily long videos.
- Comparing multiple model families in the initial scope.
- Formal model certification, safety assurance, or operational suitability claims.
- Automated conclusions or recommended actions based on detections.

## Further Notes

- The most important demonstration is failure analysis grounded in real labels. The project should make it easy to answer: "Under which real conditions does the model fail, for which classes, by how much, and does synthetic degradation predict that failure?"
- A compelling demo sequence is: open the Benchmark view and show average precision dropping from clear to fog to snow; open a real-fog worst frame showing a missed vehicle; switch to Synthetic mode on clear-weather frames and raise fog severity; show the sim-to-real chart comparing the two drops; export the report.
- The sim-to-real comparison has real confounds. Real fog co-occurs with lower light, different roads, and different traffic. The limitations section must say this plainly. A mismatch between synthetic and real results is a legitimate and interesting finding, not a failure of the project.
- The fog-chamber case study removes those confounds but has its own limits, and the limitations section must state them:
  - it has about four independent scenes and roughly 15–20 objects;
  - the 10 frames per condition are near-duplicates of a static scene;
  - the scenes are staged (mannequins, parked cars) in an indoor hall and differ from open roads;
  - the boxes are project-made, not official annotations;
  - the result depends on how synthetic severity is mapped to visibility.
  It is a case study, not a statistical result.
- Dataset downloads require registration, and the maintainers note that the download service has periodic downtime. Synthetic mode on the bundled sample video must remain fully functional without the dataset, so the project is never blocked on data access.
- Build order: first build the Python pipeline and FastAPI endpoints for Synthetic mode on the bundled video, verified through API tests. Then build the React shell with the comparison view. Then add the dataset adapter and class mapping, Benchmark mode, and the sim-to-real view. The fog-chamber case study comes last; if it slips, nothing else is affected. Keeping the pipeline behind the API from the start means no frontend work is ever blocked on, or tangled with, ML code.
- If time becomes constrained, cut polish in this order: multi-tab work area (fall back to one view per section), command palette actions (keep palette navigation only), keyboard sequences beyond the arrows, L, and P, and the Setup request preview. Preserve the workbench shell, frame viewer, job dock, and Findings layout.
- Also preserve Synthetic mode end to end, per-condition average precision in Benchmark mode, the class mapping and ignore-region documentation, latency measurement, the worst-frame gallery, and the limitations statement. Defer the precision-recall curves, day/night splitting, server-sent events (polling is sufficient), and additional styling before removing those elements.
- Success means a reviewer can clone the project, run the synthetic demo with one documented command on CPU, optionally connect a local copy of the dataset and reproduce the benchmark from the committed manifest, understand the system within two minutes, and see both useful model behavior and honest failures.
- Reference: Bijelic et al., "Seeing Through Fog Without Seeing Fog: Deep Multimodal Sensor Fusion in Unseen Adverse Weather," CVPR 2020. Dataset code repository: https://github.com/princeton-computational-imaging/SeeingThroughFog
- Reference: Gruber et al., "Pixel-Accurate Depth Evaluation in Realistic Driving Scenarios," 3DV 2019 (arXiv:1906.08953). Source of the PixelAccurateBenchmark fog-chamber recordings.
- This specification is tracked in GitHub Issues for `Khriis-K/Edge-Perception-Reality-Lab`. It is broken into issues #1–#23 and #30–#33, each labeled `ready-for-agent` or `ready-for-human`, with blocking issues listed under "Blocked by".
