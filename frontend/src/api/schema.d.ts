// Generated from the backend OpenAPI schema by `npm run gen:api`. Do not edit.

export interface paths {
    "/api/benchmark/class-mapping": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Class Mapping
         * @description Which COCO classes count as which dataset class, and which labels are ignore regions. Both change the metrics,
         *     so Setup, Findings and the report show them.
         */
        get: operations["class_mapping_api_benchmark_class_mapping_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/benchmark/experiments/{experiment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Benchmark Results
         * @description Per condition and class: AP, precision and recall at the display threshold, and object and frame counts.
         *     Scored from the stored detections, so a new threshold never re-runs inference.
         */
        get: operations["get_benchmark_results_api_benchmark_experiments__experiment_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/benchmark/experiments/{experiment_id}/frames/{frame_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Benchmark Frame
         * @description One frame's predictions and labels, matched at every display threshold, so the frame viewer can change
         *     threshold or toggle overlays without asking again. Its image is /api/dataset/frames/{frame_id}.
         */
        get: operations["get_benchmark_frame_api_benchmark_experiments__experiment_id__frames__frame_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/benchmark/jobs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start Benchmark
         * @description Run the detector over every frame of the manifest and score it, or reuse the cached results. Poll and cancel
         *     it like any job. A manifest from another condition vocabulary, or listing frames the local dataset doesn't have
         *     under that condition, is refused (422) with the reason.
         */
        post: operations["start_benchmark_api_benchmark_jobs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/cache": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Cache Info
         * @description The cache folder and how much it holds. Shown so it can be found and deleted; it is never set from here.
         */
        get: operations["cache_info_api_cache_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/dataset/frames/{sample_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Dataset Frame
         * @description A dataset sample's tone-mapped camera image, looked up by sample id only.
         */
        get: operations["dataset_frame_api_dataset_frames__sample_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/dataset/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Dataset Status
         * @description Re-check the dataset folder set at startup. The folder itself can't be changed from here.
         */
        get: operations["dataset_status_api_dataset_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/dataset/subset": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Dataset Subset
         * @description The seeded per-condition subset: its manifest and the counts for the Subset table. With no seed or cap,
         *     the defaults are used, and the manifest says which.
         */
        get: operations["dataset_subset_api_dataset_subset_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/degradations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Degradations */
        get: operations["list_degradations_api_degradations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/degradations/{kind}/parameters": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Degradation Parameters
         * @description The transform parameters a severity gives, exactly as a run would record them.
         */
        get: operations["degradation_parameters_api_degradations__kind__parameters_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/experiments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * List Experiments
         * @description Every cached Synthetic run, on video or on dataset frames, newest first, read from the cache folder.
         */
        get: operations["list_experiments_api_experiments_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/experiments/{experiment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Experiment */
        get: operations["get_experiment_api_experiments__experiment_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/experiments/{experiment_id}/frames/{variant}/{frame_index}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Frame Image
         * @description One cached clean or degraded frame of a completed experiment. Only known ids, never a file path.
         */
        get: operations["get_frame_image_api_experiments__experiment_id__frames__variant___frame_index__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/experiments/{experiment_id}/stability": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Stability
         * @description How much the degraded detections differ from the clean ones, frame by frame and over the clip.
         *     Stability relative to the clean baseline: the clip has no labels, so this is not accuracy.
         */
        get: operations["get_stability_api_experiments__experiment_id__stability_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_api_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/jobs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start Run
         * @description Start a run, or reuse its cached results ("cached, results reused") if identical settings already ran.
         */
        post: operations["start_run_api_jobs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/jobs/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Preview Run
         * @description Whether this exact run request would reuse cached results or start a new job. Starts nothing.
         */
        post: operations["preview_run_api_jobs_preview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/jobs/{job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Job */
        get: operations["get_job_api_jobs__job_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/jobs/{job_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel Job */
        post: operations["cancel_job_api_jobs__job_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/samples": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Samples */
        get: operations["list_samples_api_samples_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/synthetic-frames/experiments/{experiment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Get Synthetic Frames Results
         * @description Stability against the clean detections, and per-class AP, precision and recall for both the clean and the
         *     degraded frames against the ground truth, with the Benchmark's definitions. Scored from the stored detections.
         */
        get: operations["get_synthetic_frames_results_api_synthetic_frames_experiments__experiment_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/synthetic-frames/jobs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start Synthetic Frames
         * @description Degrade the manifest's frames of one clear condition and run the detector on both variants, or reuse the
         *     cached results. The manifest is checked as for a Benchmark run, and must list frames under the condition.
         */
        post: operations["start_synthetic_frames_api_synthetic_frames_jobs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /**
         * AppliedDegradation
         * @description The settings plus the transform parameters derived from the severity.
         */
        AppliedDegradation: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "darkness" | "blur" | "fog" | "noise" | "jpeg";
            /** Parameters */
            parameters: {
                [key: string]: number;
            };
            /** Seed */
            seed: number;
            /** Severity */
            severity: number;
        };
        /** BenchmarkResults */
        BenchmarkResults: {
            /** Class Mapping Version */
            class_mapping_version: number;
            /** Conditions */
            conditions: components["schemas"]["ConditionResult"][];
            /** Confidence Floor */
            confidence_floor: number;
            /** Display Threshold */
            display_threshold: number;
            /** Id */
            id: string;
            /** Iou Threshold */
            iou_threshold: number;
            /** Low N Objects */
            low_n_objects: number;
            manifest: components["schemas"]["Manifest"];
            model: components["schemas"]["ModelInfo"];
            /** Synthetic */
            synthetic: components["schemas"]["SyntheticConditionResult"][];
            /** Warnings */
            warnings: string[];
        };
        /** BenchmarkWeights */
        BenchmarkWeights: {
            /** Class Confusions */
            class_confusions: number;
            /** False Alarms */
            false_alarms: number;
            /** Misses */
            misses: number;
        };
        /**
         * Box
         * @description Corners in 0-1 image coordinates: (x1, y1) top-left, (x2, y2) bottom-right.
         */
        Box: {
            /** X1 */
            x1: number;
            /** X2 */
            x2: number;
            /** Y1 */
            y1: number;
            /** Y2 */
            y2: number;
        };
        /** CacheInfo */
        CacheInfo: {
            /** Folder */
            folder: string;
            /** Size Bytes */
            size_bytes: number;
        };
        /** ClassMapping */
        ClassMapping: {
            /** Ignore Labels */
            ignore_labels: string[];
            /** Ignore Rule */
            ignore_rule: string;
            /** Mapping */
            mapping: components["schemas"]["MappingRow"][];
            /** Unmapped Rule */
            unmapped_rule: string;
            /** Version */
            version: number;
        };
        /** ClassMetrics */
        ClassMetrics: {
            /** Ap */
            ap: number | null;
            /** Class Name */
            class_name: string;
            /** Frames */
            frames: number;
            /** Hits */
            hits: number;
            /** Low N */
            low_n: boolean;
            /** Objects */
            objects: number;
            /** Pr Curve */
            pr_curve: components["schemas"]["PRPoint"][];
            /** Precision */
            precision: number | null;
            /** Predictions */
            predictions: number;
            /** Recall */
            recall: number | null;
        };
        /** ConditionResult */
        ConditionResult: {
            /** Classes */
            classes: components["schemas"]["ClassMetrics"][];
            /** Condition */
            condition: string;
            /** Frame Scores */
            frame_scores: components["schemas"]["FrameScore"][];
            /** Frames */
            frames: number;
            /** Low N */
            low_n: boolean;
            /** Map */
            map: number | null;
            /** Objects */
            objects: number;
        };
        /** ConditionSummary */
        ConditionSummary: {
            /** Condition */
            condition: string;
            /** Frames */
            frames: number;
            /** Low N */
            low_n: boolean;
            /** Objects */
            objects: number;
            /** Smallest Class */
            smallest_class: string;
            /** Smallest Class Count */
            smallest_class_count: number;
        };
        /** ConfidenceShift */
        ConfidenceShift: {
            /** Low N */
            low_n: boolean;
            /** Pairs */
            pairs: number;
            /** Value */
            value: number | null;
        };
        /** Count */
        Count: {
            /** Count */
            count: number;
            /** Low N */
            low_n: boolean;
            /** Rate */
            rate: number | null;
            /** Total */
            total: number;
        };
        /** DatasetPartStatus */
        DatasetPartStatus: {
            /** Checked */
            checked: boolean;
            /** Detail */
            detail: string;
            /** Folder */
            folder: string;
            /**
             * Key
             * @enum {string}
             */
            key: "camera" | "labels" | "metadata";
            /** Message */
            message: string;
            /** Name */
            name: string;
            /** Present */
            present: boolean;
        };
        /** DatasetStatusResponse */
        DatasetStatusResponse: {
            /** Configured */
            configured: boolean;
            /** Message */
            message: string;
            /** Not Needed */
            not_needed: string[];
            /** Parts */
            parts: components["schemas"]["DatasetPartStatus"][];
            /** Ready */
            ready: boolean;
            /** Root */
            root: string | null;
        };
        /** Degradation */
        Degradation: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "darkness" | "blur" | "fog" | "noise" | "jpeg";
            /** Randomized */
            randomized: boolean;
            /** Title */
            title: string;
        };
        /**
         * DegradationSettings
         * @description The one degradation an experiment applies. Extra fields are refused, so a second can't sneak in.
         */
        DegradationSettings: {
            /**
             * Kind
             * @enum {string}
             */
            kind: "darkness" | "blur" | "fog" | "noise" | "jpeg";
            /** Seed */
            seed: number;
            /** Severity */
            severity: number;
        };
        /** Detection */
        Detection: {
            box: components["schemas"]["Box"];
            /** Confidence */
            confidence: number;
            /** Label */
            label: string;
        };
        /** Experiment */
        Experiment: {
            /** Confidence Floor */
            confidence_floor: number;
            degradation: components["schemas"]["AppliedDegradation"];
            /** Frame Height */
            frame_height: number;
            /** Frame Width */
            frame_width: number;
            /** Frames */
            frames: components["schemas"]["FrameResult"][];
            /** Id */
            id: string;
            latency?: components["schemas"]["LatencySummary"] | null;
            model: components["schemas"]["ModelInfo"];
            /** Sample Id */
            sample_id: string;
        };
        /**
         * ExperimentSummary
         * @description A cached Synthetic run, for the run history. The frames themselves come from the experiment.
         */
        ExperimentSummary: {
            degradation: components["schemas"]["AppliedDegradation"];
            /** Frame Count */
            frame_count: number;
            /** Id */
            id: string;
            /**
             * Input
             * @enum {string}
             */
            input: "video" | "dataset";
            model: components["schemas"]["ModelInfo"];
            /** Sample Id */
            sample_id: string;
            /** Sample Title */
            sample_title: string;
            /**
             * Saved At
             * Format: date-time
             */
            saved_at: string;
        };
        /**
         * FrameDetail
         * @description One frame, for the frame viewer: its overlays at every display threshold.
         */
        FrameDetail: {
            /** Condition */
            condition: string;
            /** Id */
            id: string;
            /** Levels */
            levels: components["schemas"]["FrameLevel"][];
            /** Predictions */
            predictions: components["schemas"]["Detection"][];
            /** Truths */
            truths: components["schemas"]["FrameTruth"][];
            /** Unmapped */
            unmapped: components["schemas"]["Detection"][];
            weights: components["schemas"]["BenchmarkWeights"];
        };
        /** FrameLevel */
        FrameLevel: {
            /** Matches */
            matches: components["schemas"]["IndexedMatch"][];
            /** Min Confidence */
            min_confidence: number | null;
            score: components["schemas"]["FrameScore"];
        };
        /** FrameResult */
        FrameResult: {
            /** Clean */
            clean: components["schemas"]["Detection"][];
            /** Degraded */
            degraded: components["schemas"]["Detection"][];
            /** Index */
            index: number;
        };
        /** FrameScore */
        FrameScore: {
            /** Class Confusions */
            class_confusions: number;
            /** False Alarms */
            false_alarms: number;
            /** Hits */
            hits: number;
            /** Id */
            id: string;
            /** Ignored */
            ignored: number;
            /** Misses */
            misses: number;
            /** Score */
            score: number;
        };
        /** FrameStability */
        FrameStability: {
            /** Class Changes */
            class_changes: number;
            /** Confidence Loss */
            confidence_loss: number;
            /** Dropped */
            dropped: number;
            /** Index */
            index: number;
            /** Introduced */
            introduced: number;
            /** Matches */
            matches: components["schemas"]["Match"][];
            /** Retained */
            retained: number;
            /** Score */
            score: number;
        };
        /** FrameTruth */
        FrameTruth: {
            box: components["schemas"]["Box"];
            /** Label */
            label: string;
            /**
             * Role
             * @enum {string}
             */
            role: "object" | "ignore" | "excluded";
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** HealthResponse */
        HealthResponse: {
            /**
             * Status
             * @constant
             */
            status: "ok";
        };
        /**
         * IndexedMatch
         * @description A match by position: `prediction` indexes the predictions matched, `truth` the frame's truths.
         */
        IndexedMatch: {
            /** Iou */
            iou?: number | null;
            /**
             * Outcome
             * @enum {string}
             */
            outcome: "hit" | "miss" | "false_alarm" | "class_confusion" | "ignored";
            /** Prediction */
            prediction: number | null;
            /** Truth */
            truth: number | null;
        };
        /** JobResponse */
        JobResponse: {
            /** Cached */
            cached: boolean;
            /** Error */
            error: string | null;
            /** Experiment Id */
            experiment_id: string;
            /** Frames Done */
            frames_done: number;
            /** Frames Total */
            frames_total: number;
            /** Id */
            id: string;
            /**
             * Mode
             * @enum {string}
             */
            mode: "synthetic" | "benchmark" | "synthetic-frames";
            /** Progress */
            progress: number;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "completed" | "cancelled" | "failed";
        };
        /** LatencySummary */
        LatencySummary: {
            degrade: components["schemas"]["StageLatency"];
            /** Effective Fps */
            effective_fps: number | null;
            /** Frames */
            frames: number;
            inference: components["schemas"]["StageLatency"];
            /** Inference Runs */
            inference_runs: number;
            processing: components["schemas"]["StageLatency"];
            read: components["schemas"]["StageLatency"];
            render: components["schemas"]["StageLatency"];
            /** Warmup Frames */
            warmup_frames: number;
        };
        /** Manifest */
        Manifest: {
            /** Cap */
            cap: number;
            /** Frames */
            frames: {
                [key: string]: string[];
            };
            /** Seed */
            seed: number;
            /** Vocabulary Version */
            vocabulary_version: number;
        };
        /** MappingRow */
        MappingRow: {
            /** Coco */
            coco: string;
            /** Dataset Class */
            dataset_class: string;
        };
        /** Match */
        Match: {
            clean: components["schemas"]["Detection"] | null;
            /** Confidence Change */
            confidence_change?: number | null;
            degraded: components["schemas"]["Detection"] | null;
            /** Iou */
            iou?: number | null;
            /**
             * Outcome
             * @enum {string}
             */
            outcome: "retained" | "dropped" | "introduced" | "class_change";
        };
        /** ModelInfo */
        ModelInfo: {
            /** Name */
            name: string;
            /** Provider */
            provider?: string | null;
            /** Runtime */
            runtime: string;
            /** Size Bytes */
            size_bytes?: number | null;
            /** Version */
            version: string;
        };
        /** PRPoint */
        PRPoint: {
            /** Precision */
            precision: number;
            /** Recall */
            recall: number | null;
            /** Threshold */
            threshold: number;
        };
        /**
         * RunPreview
         * @description What starting this run would do: reuse cached results, or start a new job.
         */
        RunPreview: {
            /** Cached */
            cached: boolean;
            /** Experiment Id */
            experiment_id: string;
        };
        /** SampleVideo */
        SampleVideo: {
            /** Id */
            id: string;
            /** Title */
            title: string;
        };
        /** ScoreWeights */
        ScoreWeights: {
            /** Class Changes */
            class_changes: number;
            /** Confidence Loss */
            confidence_loss: number;
            /** Dropped */
            dropped: number;
            /** Introduced */
            introduced: number;
        };
        /** StabilityReport */
        StabilityReport: {
            class_changes: components["schemas"]["Count"];
            /** Confidence Threshold */
            confidence_threshold: number;
            /** Frames */
            frames: components["schemas"]["FrameStability"][];
            /** Frames Evaluated */
            frames_evaluated: number;
            introduced: components["schemas"]["Count"];
            /** Iou Threshold */
            iou_threshold: number;
            /** Low N Objects */
            low_n_objects: number;
            median_confidence_shift: components["schemas"]["ConfidenceShift"];
            retention: components["schemas"]["Count"];
            weights: components["schemas"]["ScoreWeights"];
        };
        /** StageLatency */
        StageLatency: {
            /** P50 Ms */
            p50_ms: number;
            /** P90 Ms */
            p90_ms: number;
        };
        /** StartBenchmarkRequest */
        StartBenchmarkRequest: {
            manifest: components["schemas"]["Manifest"];
        };
        /** StartRunRequest */
        StartRunRequest: {
            degradation: components["schemas"]["DegradationSettings"];
            /** Sample Id */
            sample_id: string;
        };
        /** StartSyntheticFramesRequest */
        StartSyntheticFramesRequest: {
            /**
             * Condition
             * @enum {string}
             */
            condition: "clear-day" | "clear-night";
            degradation: components["schemas"]["DegradationSettings"];
            manifest: components["schemas"]["Manifest"];
        };
        /** SubsetResponse */
        SubsetResponse: {
            /** Conditions */
            conditions: components["schemas"]["ConditionSummary"][];
            /** Excluded */
            excluded: {
                [key: string]: number;
            };
            /** Excluded Total */
            excluded_total: number;
            /** Low N Objects */
            low_n_objects: number;
            manifest: components["schemas"]["Manifest"];
            /** Max Cap */
            max_cap: number;
            /** Problems */
            problems: string[];
        };
        /**
         * SyntheticConditionResult
         * @description A synthetic degradation of one of the run's clear conditions, on the same frames, beside the real ones.
         */
        SyntheticConditionResult: {
            /** Classes */
            classes: components["schemas"]["ClassMetrics"][];
            /** Condition */
            condition: string;
            degradation: components["schemas"]["AppliedDegradation"];
            /** Experiment Id */
            experiment_id: string;
            /** Frame Scores */
            frame_scores: components["schemas"]["FrameScore"][];
            /** Frames */
            frames: number;
            /** Low N */
            low_n: boolean;
            /** Map */
            map: number | null;
            /** Objects */
            objects: number;
            /** Title */
            title: string;
        };
        /** SyntheticFramesResults */
        SyntheticFramesResults: {
            /** Class Mapping Version */
            class_mapping_version: number;
            clean: components["schemas"]["ConditionResult"];
            /**
             * Condition
             * @enum {string}
             */
            condition: "clear-day" | "clear-night";
            /** Confidence Floor */
            confidence_floor: number;
            degradation: components["schemas"]["AppliedDegradation"];
            degraded: components["schemas"]["ConditionResult"];
            /** Display Threshold */
            display_threshold: number;
            /** Id */
            id: string;
            /** Iou Threshold */
            iou_threshold: number;
            /** Low N Objects */
            low_n_objects: number;
            manifest: components["schemas"]["Manifest"];
            model: components["schemas"]["ModelInfo"];
            stability: components["schemas"]["StabilityReport"];
            /** Title */
            title: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Context */
            ctx?: Record<string, never>;
            /** Input */
            input?: unknown;
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    class_mapping_api_benchmark_class_mapping_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ClassMapping"];
                };
            };
        };
    };
    get_benchmark_results_api_benchmark_experiments__experiment_id__get: {
        parameters: {
            query: {
                display_threshold: number;
            };
            header?: never;
            path: {
                experiment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BenchmarkResults"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_benchmark_frame_api_benchmark_experiments__experiment_id__frames__frame_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                experiment_id: string;
                frame_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FrameDetail"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    start_benchmark_api_benchmark_jobs_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StartBenchmarkRequest"];
            };
        };
        responses: {
            /** @description Cached: the results were reused */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobResponse"];
                };
            };
            /** @description The dataset is not configured or not ready */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cache_info_api_cache_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CacheInfo"];
                };
            };
        };
    };
    dataset_frame_api_dataset_frames__sample_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sample_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "image/png": unknown;
                };
            };
            /** @description No such frame */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    dataset_status_api_dataset_status_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DatasetStatusResponse"];
                };
            };
        };
    };
    dataset_subset_api_dataset_subset_get: {
        parameters: {
            query?: {
                seed?: number;
                cap?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SubsetResponse"];
                };
            };
            /** @description The dataset is not configured or not ready */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_degradations_api_degradations_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Degradation"][];
                };
            };
        };
    };
    degradation_parameters_api_degradations__kind__parameters_get: {
        parameters: {
            query: {
                severity: number;
            };
            header?: never;
            path: {
                kind: "darkness" | "blur" | "fog" | "noise" | "jpeg";
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: number;
                    };
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_experiments_api_experiments_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ExperimentSummary"][];
                };
            };
        };
    };
    get_experiment_api_experiments__experiment_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                experiment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Experiment"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_frame_image_api_experiments__experiment_id__frames__variant___frame_index__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                experiment_id: string;
                variant: "clean" | "degraded";
                frame_index: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "image/jpeg": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_stability_api_experiments__experiment_id__stability_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                experiment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StabilityReport"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    health_api_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
        };
    };
    start_run_api_jobs_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StartRunRequest"];
            };
        };
        responses: {
            /** @description Cached: the results were reused */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    preview_run_api_jobs_preview_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StartRunRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunPreview"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_job_api_jobs__job_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cancel_job_api_jobs__job_id__cancel_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_samples_api_samples_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SampleVideo"][];
                };
            };
        };
    };
    get_synthetic_frames_results_api_synthetic_frames_experiments__experiment_id__get: {
        parameters: {
            query: {
                display_threshold: number;
            };
            header?: never;
            path: {
                experiment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SyntheticFramesResults"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    start_synthetic_frames_api_synthetic_frames_jobs_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StartSyntheticFramesRequest"];
            };
        };
        responses: {
            /** @description Cached: the results were reused */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobResponse"];
                };
            };
            /** @description The dataset is not configured or not ready */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
