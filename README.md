# Edge Perception Reliability Lab

A local workbench for evaluating a pretrained object detector under real and synthetic adverse conditions. See `docs/edge-perception-reliability-lab-spec.md`.

## Run

One command starts the backend and the built frontend on one port, bound to 127.0.0.1 only:

```
.venv/Scripts/python.exe -m backend
```

Then open http://127.0.0.1:8000. Use `--port` to change the port.

### First-time setup

Python 3.12+ and Node.js 20+.

```
py -m venv .venv
.venv/Scripts/pip.exe install -e ".[dev]"
cd frontend
npm install
npm run build
```

(On macOS/Linux use `.venv/bin/python` and `.venv/bin/pip`.)

## Connect the SeeingThroughFog dataset (optional)

Synthetic mode works without it. For Benchmark mode, download SeeingThroughFog from its official source ([repository](https://github.com/princeton-computational-imaging/SeeingThroughFog); registration required) and keep it outside this repo.

1. Verify the downloaded archives against the published checksums:

   ```
   .venv/Scripts/python.exe -m backend.checksums PATH/TO/ARCHIVES
   ```

   It prints PASS, FAIL or MISSING per archive and exits non-zero unless all pass.

2. Extract only the three parts the app reads. Everything else (lidar, radar, gated, thermal, raw camera, road friction, weather station) can be skipped:

   | Part | Folder |
   | --- | --- |
   | 8-bit tone-mapped left camera images | `cam_stereo_left_lut` |
   | Ground-truth labels (KITTI format) | `gt_labels/cam_left_labels_TMP` |
   | Environment metadata (weather, road, illumination) | `labeltool_labels` (ships as a zip; extract it) |

3. Start the app with the folder. It is set only at startup, never from the browser:

   ```
   .venv/Scripts/python.exe -m backend --dataset D:/data/SeeingThroughFog
   ```

   or set `EDGE_LAB_DATASET` (the flag wins if both are set). Setup shows each part as present or missing; use Re-check after extracting more.

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

## Test

```
.venv/Scripts/python.exe -m pytest                    # backend contract tests
npm --prefix frontend exec -- playwright install chromium   # once
npm --prefix frontend run check                       # API types are current, then browser + axe tests
```

Tests never use the real dataset. They generate a small stand-in with `scripts/make_fixture_dataset.py` (the e2e run writes it to `frontend/.e2e-dataset/`).
