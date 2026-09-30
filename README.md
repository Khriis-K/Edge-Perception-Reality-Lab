# Edge Perception Reliability Lab

A local workbench for evaluating a pretrained object detector under real and synthetic adverse conditions. See `docs/edge-perception-reliability-lab-spec.md`.

## Run

One command starts the backend and the built frontend on one port, bound to 127.0.0.1 only:

```
.venv/Scripts/python.exe -m backend
```

Then open http://127.0.0.1:8000. Use `--port` to change the port.

The detector is YOLOX-Nano (Apache-2.0), pretrained on COCO, run on the CPU through ONNX Runtime. Without its weights the app still starts, but runs are refused with a message saying how to fetch them. `--runner stub` swaps in a deterministic stand-in detector (the browser tests use it).

Two sample videos are bundled:

- **City driving, Kraków** (the default): 20 seconds of real dashcam footage with cars and pedestrians. It's an excerpt of a video by Relaxing Roads 4K, under CC BY 3.0 (see [samples/CREDITS.md](samples/CREDITS.md)).
- **Synthetic traffic**: a bright block driving across a dark road. The stub "detects" it; the real detector finds nothing in it, because it isn't a real scene. It exists as the test fixture.

### First-time setup

Python 3.12+ and Node.js 20+.

```
py -m venv .venv
.venv/Scripts/pip.exe install -e ".[dev,cpu]"
.venv/Scripts/python.exe scripts/fetch_model.py   # detector weights into models/, SHA-256 checked
cd frontend
npm install
npm run build
```

(On macOS/Linux use `.venv/bin/python` and `.venv/bin/pip`.)

**NVIDIA GPU:** install `".[dev,gpu]"` instead of `".[dev,cpu]"`. The detector then runs on CUDA, and the Latency panel shows `CUDAExecutionProvider`. Choose one: both builds install the same `onnxruntime` package. To switch an existing venv, first run `pip uninstall -y onnxruntime onnxruntime-gpu`.

## Connect the SeeingThroughFog dataset (optional)

Synthetic mode works without it. For Benchmark mode, download SeeingThroughFog from its official source ([repository](https://github.com/princeton-computational-imaging/SeeingThroughFog); registration required) and keep it outside this repo.

1. Download only the three parts the app reads. Everything else (lidar, radar, gated, thermal, raw camera, road friction, weather station) can be skipped. Each part is its own archive. The camera images are split: `cam_stereo_left_lut/cam_stereo_left_lut.z01`…`.z23` plus `cam_stereo_left_lut.zip`. The labels and metadata are single zips: `gt_labels/cam_left_labels_TMP.zip` and `labeltool_labels/labeltool_labels_refined.zip`.

2. Check the download. Upstream publishes no checksums for these per-folder archives (their `SeeingThroughFog_sha256sum.txt` covers a combined archive the download doesn't contain). Zip stores a CRC32 for every file, so a corrupt download fails at extraction:

   - Make sure every split part, `.z01`…`.zNN`, sits next to its `.zip`. A missing part stops extraction partway.
   - Extraction must finish with no CRC errors. If 7-Zip reports one, download that archive again.

3. Extract each archive with `7z x ARCHIVE.zip -oDEST`, for example `7z x cam_stereo_left_lut/cam_stereo_left_lut.zip -oD:/data/SeeingThroughFog`. 7-Zip reads the `.z01`…`.zNN` parts automatically. The app expects the folders below under the dataset root. List an archive with `7z l` first, and pick `DEST` so its contents land at that path. Setup reports any part it can't find.

   | Part | Folder |
   | --- | --- |
   | 8-bit tone-mapped left camera images | `cam_stereo_left_lut` |
   | Ground-truth labels (KITTI format) | `gt_labels/cam_left_labels_TMP` |
   | Refined environment metadata (fog, precipitation, daytime) | `labeltool_labels_refined` |

   The original `labeltool_labels` isn't needed; the app reads the refined metadata.

4. Start the app with the folder. It is set only at startup, never from the browser:

   ```
   .venv/Scripts/python.exe -m backend --dataset D:/data/SeeingThroughFog
   ```

   or set `EDGE_LAB_DATASET` (the flag wins if both are set). Setup shows each part as present or missing; use Re-check after extracting more.

### Conditions and the subset

Each sample is assigned one of eight evaluation conditions: clear, fog, snow and rain, each split into day and night. Samples whose condition can't be determined are excluded and counted. That covers fog with rain or snow, twilight, and frames with a malformed label line. The full mapping, and why each exclusion exists, is in [`backend/conditions.py`](backend/conditions.py). The data behind it is in [`docs/research/seeingthroughfog-data-inspection.md`](docs/research/seeingthroughfog-data-inspection.md).

Setup's Subset table draws up to a cap of frames per condition (default 300) with a seed (default 0). It shows frames, objects and the rarest class per condition, and tags a condition **low n** when its rarest class has fewer than 30 objects. The same seed, cap and dataset always give the same subset. **Download manifest** saves the seed, cap, condition vocabulary version and frame ids as JSON, which you can commit so others can reproduce the subset.

The first time the table loads, the app reads every label and metadata file. That can take a few minutes on the full dataset; after that it is cached until the app restarts.

## Develop

Frontend with hot reload, in two terminals:

```
.venv/Scripts/python.exe -m backend --dev   # allows cross-origin calls from the Vite dev server
npm --prefix frontend run dev               # http://127.0.0.1:5173
```

`--dev` is the only mode that enables CORS, and only for the Vite dev server's origin.

The frontend's API types are generated from the backend's OpenAPI schema. After changing a Pydantic model:

```
npm --prefix frontend run gen:api
```

### Local files

`models/` holds the fetched weights, and `cache/` holds finished runs: the decoded clean and degraded frames plus the results. Both are local only and ignored by git.

A run is cached under an id built from everything that affects its results: the input video's content, the model version, the class-mapping version, the confidence floor, and the degradation type, severity and seed. Starting a run with the same settings reuses the cached results instead of running inference again, including after a restart. Setup and Synthetic list the cached runs, and Setup shows the cache folder and its size. A cancelled or failed run is never cached.

A Benchmark run is cached the same way, with the subset manifest (seed, cap, condition vocabulary version and every frame id) in place of the video's content. It stores the detections and each frame's ground truth, not the images. The dataset's files are not fingerprinted, so delete `cache/` if you change the dataset itself (see `docs/adr/0002-what-the-experiment-id-covers.md`).

To remove cached artifacts, delete `cache/`, or one run's folder inside it, whenever you like; a run in progress at that moment fails and can be started again. `python -m backend --cache-dir <folder>` keeps the cache somewhere else.

## Test

```
.venv/Scripts/python.exe -m pytest                    # backend contract tests
.venv/Scripts/python.exe -m pytest -m model           # runner contract and max-severity darkness/fog, on the real weights
npm --prefix frontend exec -- playwright install chromium   # once
npm --prefix frontend run check                       # API types are current, unit tests, then browser + axe tests
```

The synthetic sample video is also the test fixture. To regenerate it:

```
.venv/Scripts/python.exe scripts/make_sample_video.py
```

Tests never use the real dataset. They generate a small stand-in with `scripts/make_fixture_dataset.py` (the e2e run writes it to `frontend/.e2e-dataset/`).
