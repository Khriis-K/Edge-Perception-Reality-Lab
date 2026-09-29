// Generated from the backend OpenAPI schema by `npm run gen:api`. Do not edit.

export interface paths {
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
        /** Start Run */
        post: operations["start_run_api_jobs_post"];
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
            model: components["schemas"]["ModelInfo"];
            /** Sample Id */
            sample_id: string;
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
        /** JobResponse */
        JobResponse: {
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
             * @constant
             */
            mode: "synthetic";
            /** Progress */
            progress: number;
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "running" | "completed" | "cancelled" | "failed";
        };
        /** ModelInfo */
        ModelInfo: {
            /** Name */
            name: string;
            /** Runtime */
            runtime: string;
            /** Version */
            version: string;
        };
        /** SampleVideo */
        SampleVideo: {
            /** Id */
            id: string;
            /** Title */
            title: string;
        };
        /** StartRunRequest */
        StartRunRequest: {
            degradation: components["schemas"]["DegradationSettings"];
            /** Sample Id */
            sample_id: string;
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
}
