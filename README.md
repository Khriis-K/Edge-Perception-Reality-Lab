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
