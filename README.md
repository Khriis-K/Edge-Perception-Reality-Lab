# Edge Perception Reliability Lab

A local workbench for evaluating a pretrained object detector under real and synthetic adverse conditions. See `docs/edge-perception-reliability-lab-spec.md`.

## Run

One command starts the backend and the built frontend on one port, bound to 127.0.0.1 only:

```
.venv/Scripts/python.exe -m backend
```

Then open http://127.0.0.1:8000. Use `--port` to change the port.

The detector is YOLOX-Nano (Apache-2.0), pretrained on COCO, run on the CPU through ONNX Runtime. Without its weights the app still starts, but runs are refused with a message saying how to fetch them. `--runner stub` swaps in a deterministic stand-in detector (the browser tests use it).

The bundled sample video is synthetic: a bright block driving across a dark road. The stub "detects" it; the real detector finds nothing in it, because it isn't a real scene. A real sample clip is still to come.

### First-time setup

Python 3.12+ and Node.js 20+.

```
py -m venv .venv
.venv/Scripts/pip.exe install -e ".[dev]"
.venv/Scripts/python.exe scripts/fetch_model.py   # detector weights into models/, SHA-256 checked
cd frontend
npm install
npm run build
```

(On macOS/Linux use `.venv/bin/python` and `.venv/bin/pip`.)

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

`models/` holds the fetched weights and `cache/` holds the frames each run decodes. Both are local only and ignored by git. Delete `cache/` whenever you like; completed runs are forgotten when the server restarts anyway.

## Test

```
.venv/Scripts/python.exe -m pytest                    # backend contract tests
.venv/Scripts/python.exe -m pytest -m model           # the same runner contract against the real weights
npm --prefix frontend exec -- playwright install chromium   # once
npm --prefix frontend run check                       # API types are current, unit tests, then browser + axe tests
```

The synthetic sample video is also the test fixture. To regenerate it:

```
.venv/Scripts/python.exe scripts/make_sample_video.py
```
