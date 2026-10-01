"""report.html: a run's report as one self-contained page, rendered from its report document (backend/report.py).

The page loads nothing: its style is inline, it has no script, no image and no link to fetch, so it opens offline and
prints as it shows. It follows Findings' structure: what to read first, the numbered findings in the run's own order,
each led by the user's headline when one is written (none is ever generated), the worst frames by id, then the record
of the run. Findings are tables, not charts. The heatmap's cells are shaded inline; the one drawing is Finding 03's
precision-recall curves, a small inline SVG per class with every curve labelled in text.

Every finding a run has must have a renderer below: the report looks each one up, so a finding without one fails the
export rather than silently going missing.
"""

from collections.abc import Callable
from html import escape
from typing import NamedTuple

from backend.benchmark import ClassMetrics
from backend.benchmark_run import ConditionResult
from backend.class_mapping import CLASS_MAPPING
from backend.conditions import condition_name
from backend.degradations import TITLES
from backend.experiment import AppliedDegradation
from backend.findings import (
    BENCHMARK_FINDINGS,
    REAL_FOG,
    REAL_FOG_TITLE,
    REFERENCE,
    VIDEO_FINDINGS,
    Comparison,
    CurveSide,
    FrameReliability,
    FindingKey,
)
from backend.latency import LatencySummary
from backend.report import BenchmarkReport, Report, VideoReport
from backend.stability import Count

CITATION = (
    'Bijelic et al., "Seeing Through Fog Without Seeing Fog: Deep Multimodal Sensor Fusion in Unseen Adverse '
    'Weather," CVPR 2020.'
)
FINDING_TITLES: dict[FindingKey, str] = {
    "sim-to-real": "Sim-to-real",
    "where-it-fails": "Where it fails",
    "precision-recall": "Precision–recall",
    "reliability-timeline": "Reliability timeline",
}

# Light layout: a black header band on a white page. Heatmap cells shade from pale blue (AP 0) to blue (AP 1), so an AP of
# 0 never looks like an empty cell (no objects).
_LOW, _HIGH = (226, 234, 246), (45, 114, 210)
_CURVES = {"reference": ("#1c2127", None), "synthetic": ("#2d72d2", "6 3"), "real": ("#c87619", "2 3")}
_SYNTHETIC_DASHES = ["6 3", "10 3 2 3", "4 4 1 4"]  # more than one synthetic run: each its own line style
_PR_SIZE, _PR_MARGIN = 220, 30

_STYLE = """
* { box-sizing: border-box; }
body { margin: 0; background: #ffffff; color: #1c2127; font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
.band { background: #000000; color: #ffffff; padding: 24px 32px; }
.band p { margin: 4px 0 0; color: #d3d8de; }
.band .eyebrow { margin: 0; text-transform: uppercase; letter-spacing: 0.08em; font-size: 12px; color: #abb3bf; }
.band h1 { margin: 6px 0 0; font-size: 24px; }
main { max-width: 960px; margin: 0 auto; padding: 8px 32px 48px; }
section { margin-top: 32px; }
h2 { font-size: 18px; border-bottom: 2px solid #1c2127; padding-bottom: 4px; }
h3 { font-size: 15px; margin: 20px 0 6px; }
.callout { border-left: 4px solid #c87619; padding: 4px 16px; background: #fbf3ea; }
.headline { font-size: 17px; font-weight: 600; }
.headline.none { font-weight: 400; color: #5f6b7c; font-style: italic; }
.note, caption { color: #5f6b7c; font-size: 13px; }
caption { caption-side: bottom; text-align: left; padding-top: 4px; }
table { border-collapse: collapse; margin: 8px 0; }
th, td { border: 1px solid #d3d8de; padding: 3px 8px; text-align: left; vertical-align: top; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
thead th { background: #f6f7f9; }
code, .ids { font-family: ui-monospace, Consolas, monospace; font-size: 12px; }
.ids { word-break: break-all; }
.n { color: #5f6b7c; }
.curves { display: flex; flex-wrap: wrap; gap: 16px; }
figure.pr { margin: 0; width: 300px; }
figure.pr h3 { margin-top: 8px; }
figure.pr ul { padding-left: 18px; margin: 4px 0; font-size: 12px; }
@media print {
  .band, td { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  table, figure, li { break-inside: avoid; }
  h2, h3 { break-after: avoid; }
}
"""


def report_html(report: Report) -> str:
    header = report.export
    kind = "Benchmark run" if isinstance(report, BenchmarkReport) else "Synthetic run on video"
    facts = [kind, f"exported {header.created_at:%Y-%m-%d %H:%M} UTC"]
    if header.display_threshold is not None:
        facts.append(f"display threshold {header.display_threshold:.2f}")
    facts.append(f"run {header.experiment_id}")
    if isinstance(report, BenchmarkReport):
        body = _findings(report, BENCHMARK_FINDINGS, BENCHMARK_RENDERERS) + _benchmark_worst(report) + _benchmark_record(report)
    else:
        body = _findings(report, VIDEO_FINDINGS, VIDEO_RENDERERS) + _video_worst(report) + _video_record(report)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Report · {escape(header.title)}</title>
<style>{_STYLE}</style>
</head>
<body>
<header class="band">
<p class="eyebrow">Edge Perception Reliability Lab · Report</p>
<h1>{escape(header.title)}</h1>
<p>{escape(" · ".join(facts))}</p>
</header>
<main>
<section id="read-this-first" class="callout">
<h2>Read this first</h2>
{_list(report.findings.limitations)}
</section>
{body}
<section id="citation">
<h2>Citation</h2>
<p>Benchmark mode scores the detector against the SeeingThroughFog dataset: {escape(CITATION)}</p>
</section>
</main>
</body>
</html>
"""


def _findings[R: Report](report: R, keys: tuple[FindingKey, ...], renderers: dict[FindingKey, Callable[[R], str]]) -> str:
    sections = []
    for number, key in enumerate(keys, start=1):
        headline = report.findings.headlines.get(key)
        lead = (
            f'<p class="headline">{escape(headline)}</p>'
            if headline
            else '<p class="headline none">No headline written.</p>'
        )
        sections.append(
            f'<section id="{key}">\n<h2>Finding {number:02d} · {FINDING_TITLES[key]}</h2>\n{lead}\n{renderers[key](report)}\n</section>'
        )
    return "\n".join(sections)


# --- Finding 01 · Sim-to-real ------------------------------------------------------------------------------


def _sim_to_real(report: BenchmarkReport) -> str:
    sim = report.findings.sim_to_real
    if sim.reference is None:
        return _note(f"This run has no {condition_name(REFERENCE)} frames, so there is nothing to compare against.")
    comparisons = [*sim.synthetic, *([sim.real] if sim.real else [])]
    sides = [
        f'<tr><th scope="row">{condition_name(REFERENCE)}</th>{_num(_metric(sim.reference.map))}'
        f"{_num(sim.reference.objects)}{_num(sim.reference.frames)}<td>reference</td></tr>"
    ] + [
        f'<tr><th scope="row">{escape(c.title)}</th>{_num(_metric(c.map))}{_num(c.objects)}{_num(c.frames)}'
        f"{_num(_metric(c.map_drop))}</tr>"
        for c in comparisons
    ]
    missing = []
    if not sim.synthetic:
        missing.append(f"No synthetic fog run on the {condition_name(REFERENCE)} frames yet.")
    if sim.real is None:
        missing.append(f"No {condition_name(REAL_FOG)} frames in this run.")
    head = "".join(f'<th scope="col" class="num">{escape(c.title)}</th><th scope="col" class="num">Drop</th>' for c in comparisons)
    rows = []
    for i, reference in enumerate(comparisons[0].classes if comparisons else []):
        cells = "".join(_drop_cells(c, i) for c in comparisons)
        rows.append(
            f'<tr><th scope="row">{reference.class_name}</th>'
            f"{_num(_ap(reference.reference_ap, reference.reference_objects))}{cells}</tr>"
        )
    per_class = (
        f'<table><caption>AP per class, objects in brackets. Drop: {condition_name(REFERENCE)} AP minus the other '
        f"side's. * either side has fewer than {report.findings.record.low_n_objects} objects (low n): read as noise. "
        f"— undefined: no objects of that class on one side.</caption><thead><tr><th scope=\"col\">Class</th>"
        f'<th scope="col" class="num">{condition_name(REFERENCE)}</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        if comparisons
        else ""
    )
    return (
        f"<table><caption>mAP per side, with the objects and frames behind it. The real-fog frames are other scenes "
        f"than the clear ones: the comparison is distributional, not paired.</caption><thead><tr>"
        f'<th scope="col">Side</th><th scope="col" class="num">mAP</th><th scope="col" class="num">Objects</th>'
        f'<th scope="col" class="num">Frames</th><th scope="col" class="num">Drop</th></tr></thead>'
        f"<tbody>{''.join(sides)}</tbody></table>{''.join(_note(m) for m in missing)}{per_class}"
    )


def _drop_cells(comparison: Comparison, index: int) -> str:
    row = comparison.classes[index]
    drop = _metric(row.drop) + ("*" if row.drop is not None and row.low_n else "")
    return f"{_num(_ap(row.ap, row.objects))}{_num(drop)}"


# --- Finding 02 · Where it fails ---------------------------------------------------------------------------


def _where_it_fails(report: BenchmarkReport) -> str:
    rows = report.findings.conditions
    low_n = report.findings.record.low_n_objects
    classes = [c.class_name for c in rows[0].cells] if rows else []
    body = []
    for row in rows:
        cells = "".join(
            '<td class="num">—</td>'
            if cell.ap is None
            else f'<td style="{_shade(cell.ap)}">{_metric(cell.ap)}{"*" if cell.low_n else ""}</td>'
            for cell in row.cells
        )
        mean = _metric(row.map) + ("*" if row.low_n and row.map is not None else "")
        frames = f"{row.frames} {'frame' if row.frames == 1 else 'frames'}"
        body.append(
            f'<tr><th scope="row">{condition_name(row.condition)} <span class="n">{frames}</span></th>{cells}{_num(mean)}</tr>'
        )
    head = "".join(f'<th scope="col">{name}</th>' for name in classes)
    return (
        f"<table><caption>AP by condition and class. * fewer than {low_n} objects (low n): read as noise. — no "
        f'objects of that class.</caption><thead><tr><th scope="col">Condition</th>{head}<th scope="col">mAP</th>'
        f"</tr></thead><tbody>{''.join(body)}</tbody></table>"
    )


def _shade(ap: float) -> str:
    t = min(max(ap, 0.0), 1.0)
    rgb = [round(low + (high - low) * t) for low, high in zip(_LOW, _HIGH)]
    linear = [c / 255 / 12.92 if c / 255 <= 0.04045 else ((c / 255 + 0.055) / 1.055) ** 2.4 for c in rgb]
    luminance = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    return f"background:rgb({rgb[0]}, {rgb[1]}, {rgb[2]});color:{'#000000' if luminance > 0.179 else '#ffffff'}"


# --- Finding 03 · Precision-recall -------------------------------------------------------------------------


def _precision_recall(report: BenchmarkReport) -> str:
    curves = report.findings.pr_curves
    threshold = report.findings.display_threshold
    if curves.reference is None:
        return _note(f"This run has no {condition_name(REFERENCE)} frames, so there is nothing to compare against.")
    lines = [
        _CurveLine(curves.reference.title, curves.reference, *_CURVES["reference"], ""),
        *[
            _CurveLine(side.title, side, _CURVES["synthetic"][0], _SYNTHETIC_DASHES[i % len(_SYNTHETIC_DASHES)], "")
            for i, side in enumerate(curves.synthetic)
        ],
    ]
    if not curves.synthetic:
        lines.append(
            _CurveLine("Synthetic fog", None, *_CURVES["synthetic"], f"not run on the {condition_name(REFERENCE)} frames yet")
        )
    lines.append(
        _CurveLine(REAL_FOG_TITLE, curves.real, *_CURVES["real"], f"no {condition_name(REAL_FOG)} frames in this run")
    )
    figures = [_pr_figure(i, metrics.class_name, lines, threshold) for i, metrics in enumerate(curves.reference.classes)]
    return (
        f'<div class="curves">{"".join(figures)}</div>'
        + _note(
            f"Each curve is the Benchmark's own, the one its AP is computed from. A ring marks a curve's point at the "
            f"display threshold {threshold:.2f} (confidence ≥ {threshold:.2f}); a dot, its lowest confidence. Curves are "
            "drawn as measured; AP takes the area under them with precision interpolated, the best at any higher recall."
        )
    )


class _CurveLine(NamedTuple):
    name: str
    side: CurveSide | None  # None: the side isn't in this run, and `absent` says why
    color: str
    dash: str | None  # every side has its own line style, so no curve is told apart by color alone
    absent: str


def _pr_figure(index: int, class_name: str, lines: list[_CurveLine], threshold: float) -> str:
    """The class at `index` of every side: its curves, each side's point at the display threshold ringed, and every
    curve labelled in text below."""
    size, margin = _PR_SIZE, _PR_MARGIN

    def x(recall: float) -> float:
        return round(margin + recall * (size - 2 * margin + 10), 1)

    def y(precision: float) -> float:
        return round(size - margin - precision * (size - 2 * margin), 1)

    marks = []
    for tick in (0, 0.25, 0.5, 0.75, 1):
        marks.append(f'<line x1="{x(0)}" x2="{x(1)}" y1="{y(tick)}" y2="{y(tick)}" stroke="#e5e8eb"/>')
        marks.append(f'<line x1="{x(tick)}" x2="{x(tick)}" y1="{y(0)}" y2="{y(1)}" stroke="#e5e8eb"/>')
        marks.append(f'<text x="{x(0) - 4}" y="{y(tick) + 3}" text-anchor="end" font-size="9" fill="#5f6b7c">{tick}</text>')
        marks.append(f'<text x="{x(tick)}" y="{y(0) + 12}" text-anchor="middle" font-size="9" fill="#5f6b7c">{tick}</text>')
    marks.append(f'<text x="{(x(0) + x(1)) / 2}" y="{size - 2}" text-anchor="middle" font-size="10" fill="#5f6b7c">Recall</text>')
    marks.append(
        f'<text transform="translate(9,{(y(0) + y(1)) / 2}) rotate(-90)" text-anchor="middle" font-size="10" '
        f'fill="#5f6b7c">Precision</text>'
    )
    labels = []
    for line in lines:
        dashes = f' stroke-dasharray="{line.dash}"' if line.dash else ""
        swatch = (
            f'<svg width="24" height="10" aria-hidden="true"><line x1="0" x2="24" y1="5" y2="5" stroke="{line.color}" '
            f'stroke-width="2"{dashes}/></svg>'
        )
        metrics = line.side.classes[index] if line.side else None
        label = _curve_summary(line.name, metrics, threshold) if metrics else f"{line.name}: {line.absent}"
        labels.append(f"<li>{swatch} {escape(label)}</li>")
        if metrics is None or metrics.objects == 0 or not metrics.pr_curve:
            continue
        points = [(x(p.recall or 0), y(p.precision)) for p in metrics.pr_curve]
        marks.append(
            f'<path d="M{"L".join(f"{px},{py}" for px, py in points)}" fill="none" stroke="{line.color}" '
            f'stroke-width="2"{dashes}/>'
        )
        marks.append(f'<circle cx="{points[-1][0]}" cy="{points[-1][1]}" r="2.5" fill="{line.color}"/>')
        if metrics.precision is not None:
            marks.append(
                f'<circle class="threshold" cx="{x(metrics.recall or 0)}" cy="{y(metrics.precision)}" r="6" fill="none" '
                f'stroke="{line.color}" stroke-width="2"/>'
            )
    names = ", ".join(line.name for line in lines)
    return (
        f'<figure class="pr"><h3>{class_name}</h3><svg role="img" viewBox="0 0 {size} {size}" width="{size}" '
        f'height="{size}" aria-label="Precision-recall curves for {class_name}: {escape(names)}; each is described '
        f'below">{"".join(marks)}</svg><figcaption><ul>{"".join(labels)}</ul></figcaption></figure>'
    )


def _curve_summary(name: str, metrics: ClassMetrics, threshold: float) -> str:
    """As the Findings screen labels a curve: its AP over its objects, and its point at the display threshold."""
    if metrics.objects == 0:
        return f"{name}: no objects of this class, so no curve"
    objects = f"{metrics.objects} {'object' if metrics.objects == 1 else 'objects'}{' (low n)' if metrics.low_n else ''}"
    head = f"{name}: AP {_metric(metrics.ap)} over {objects}"
    if not metrics.pr_curve:
        return f"{head}; nothing predicted, so no curve"
    if metrics.precision is None:
        return f"{head}; nothing shown at ≥ {threshold:.2f}"
    return f"{head}; at ≥ {threshold:.2f}, precision {_metric(metrics.precision)} and recall {_metric(metrics.recall)}"


# --- Finding 01 (video) · Reliability timeline -------------------------------------------------------------


def _reliability_timeline(report: VideoReport) -> str:
    results = report.results
    shift = results.median_confidence_shift
    summary = (
        "<table><caption>Over the whole clip, at the stability threshold. Low n: counted over fewer than "
        f"{results.low_n_objects} detections.</caption><thead><tr><th scope=\"col\">Measure</th>"
        '<th scope="col" class="num">Rate</th><th scope="col" class="num">Count</th><th scope="col">Low n</th></tr>'
        f"</thead><tbody>{_count_row('Retained, of clean detections', results.retention)}"
        f"{_count_row('Introduced, of degraded detections', results.introduced)}"
        f"{_count_row('Class changes, of clean detections', results.class_changes)}"
        f'<tr><th scope="row">Median confidence shift, retained pairs</th>{_num(_metric(shift.value))}'
        f"{_num(f'{shift.pairs} pairs')}<td>{'low n' if shift.low_n else ''}</td></tr></tbody></table>"
    )
    timeline = report.findings.timeline
    changed = [p for p in timeline if p.score > 0]
    frames = (
        _video_frames(
            changed,
            f"The {len(changed)} of {len(timeline)} frames whose detections changed, in order; the rest score 0. "
            "frames.csv holds every frame.",
        )
        if changed
        else _note(f"None of the {len(timeline)} frames' detections changed under the degradation.")
    )
    return summary + frames


def _video_frames(points: list[FrameReliability], caption: str = "") -> str:
    head = "".join(
        f'<th scope="col" class="num">{h}</th>'
        for h in ("Frame", "Score", "Dropped", "Introduced", "Class changes", "Confidence lost", "Retained")
    )
    rows = "".join(
        f'<tr>{_num(p.index)}{_num(f"{p.score:.2f}")}{_num(p.dropped)}{_num(p.introduced)}{_num(p.class_changes)}'
        f'{_num(f"{p.confidence_loss:.2f}")}{_num(p.retained)}</tr>'
        for p in points
    )
    caption = f"<caption>{escape(caption)}</caption>" if caption else ""
    return f"<table>{caption}<thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"


def _count_row(name: str, count: Count) -> str:
    return (
        f'<tr><th scope="row">{name}</th>{_num(_metric(count.rate))}{_num(f"{count.count} of {count.total}")}'
        f"<td>{'low n' if count.low_n else ''}</td></tr>"
    )


BENCHMARK_RENDERERS: dict[FindingKey, Callable[[BenchmarkReport], str]] = {
    "sim-to-real": _sim_to_real,
    "where-it-fails": _where_it_fails,
    "precision-recall": _precision_recall,
}
VIDEO_RENDERERS: dict[FindingKey, Callable[[VideoReport], str]] = {"reliability-timeline": _reliability_timeline}


# --- worst frames --------------------------------------------------------------------------------------------


def _benchmark_worst(report: BenchmarkReport) -> str:
    worst = report.findings.worst_frames
    weights = report.findings.record.weights
    rows = "".join(
        f'<tr><td><code>{escape(f.id)}</code></td>{_num(f"{f.score:.2f}")}<td>{condition_name(f.condition)}</td>'
        f"{_num(f.misses)}{_num(f.false_alarms)}{_num(f.class_confusions)}{_num(f.hits)}</tr>"
        for f in worst
    )
    head = "".join(
        f'<th scope="col"{"" if h in ("Frame", "Condition") else " class=\"num\""}>{h}</th>'
        for h in ("Frame", "Score", "Condition", "Misses", "False alarms", "Class confusions", "Hits")
    )
    return _worst_section(
        f"The highest error scores at the display threshold over every condition: misses × {weights.misses:g} + "
        f"false alarms × {weights.false_alarms:g} + class confusions × {weights.class_confusions:g}. Dataset frames are "
        "named by id only; the report holds no imagery.",
        f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"
        if worst
        else _note("No frame has an error to rank."),
    )


def _video_worst(report: VideoReport) -> str:
    worst = report.findings.worst_frames
    return _worst_section(
        "The least stable frames of the clip, by stability score. Frames are named by index; the report holds no imagery.",
        _video_frames(worst) if worst else _note("No frame's detections changed, so none ranks as least stable."),
    )


def _worst_section(note: str, body: str) -> str:
    return f'<section id="worst-frames">\n<h2>Worst frames</h2>\n{_note(note)}\n{body}\n</section>'


# --- the run record ------------------------------------------------------------------------------------------


def _benchmark_record(report: BenchmarkReport) -> str:
    record = report.findings.record
    manifest = record.manifest
    threshold = report.findings.display_threshold
    weights = record.weights
    sizes = [(condition_name(row.condition), row) for row in report.results.conditions] + [
        (f"{row.title} on {condition_name(row.condition)}", row) for row in report.results.synthetic
    ]
    degradations = [
        f"{escape(row.title)} on the {condition_name(row.condition)} frames: {_degradation(row.degradation)}; run "
        f"<code>{row.experiment_id}</code>"
        for row in report.results.synthetic
    ]
    definitions = [
        f"Match: class-aware, IoU ≥ {record.match_iou:g}, greedy in confidence order. Predictions are kept down to the "
        f"confidence floor {record.confidence_floor:g}.",
        "Average precision (AP): the all-point interpolated area under the precision-recall curve, per class and "
        "condition. mAP: the mean AP over the classes with objects; a class with none has no AP, never a 0.",
        f"Precision and recall: at the display threshold {threshold:.2f}, counting predictions at or above it.",
        f"Low n: a class with fewer than {record.low_n_objects} objects; a condition is low n when a class in its mAP "
        "is.",
        f"Worst-frame score: misses × {weights.misses:g} + false alarms × {weights.false_alarms:g} + class confusions × "
        f"{weights.class_confusions:g}, at the display threshold.",
    ]
    ids = "".join(
        f"<h3>{condition_name(condition)} · {len(frame_ids)} frames</h3><p class=\"ids\">{escape(' '.join(frame_ids))}</p>"
        for condition, frame_ids in manifest.frames.items()
    )
    return f"""<section id="run-record">
<h2>Run record</h2>
<h3>Input: the subset manifest</h3>
<p>Seeded subset: seed {manifest.seed}, cap {manifest.cap} frames per condition, condition vocabulary version
{manifest.vocabulary_version}. {record.frames} frames and {record.objects} main-class objects in all. Every frame id is
listed at the end.</p>
{_model(report)}
<h3>Degradation settings</h3>
<p>The real conditions are the dataset's own weather: nothing is degraded. Synthetic runs on this run's frames, with
the same model and scoring settings:</p>
{_list(degradations, raw=True) if degradations else _note("None yet.")}
{_class_mapping(report)}
<h3>Metric definitions</h3>
{_list(definitions)}
<table><caption>Sample sizes: the frames and main-class objects behind each condition's metrics.</caption><thead><tr>
<th scope="col">Condition</th><th scope="col" class="num">Frames</th><th scope="col" class="num">Objects</th>
<th scope="col">Low n</th></tr></thead><tbody>{"".join(_size_row(name, row) for name, row in sizes)}</tbody></table>
{_latency(report.findings.latency)}
</section>
<section id="manifest">
<h2>Appendix: subset manifest</h2>
{ids}
</section>"""


def _video_record(report: VideoReport) -> str:
    record = report.findings.record
    weights = record.weights
    fingerprint = (
        f"sha256 <code>{report.input_fingerprint}</code>, the file the run read."
        if report.input_fingerprint
        else "can't be confirmed: the clip is missing or has changed since the run."
    )
    definitions = [
        "Stability, not accuracy: the clip has no labels, so the clean frame's detections are the baseline.",
        f"Detections at or above the stability threshold {record.stability_threshold:g} are matched clean to degraded: "
        f"the same label at IoU ≥ {record.match_iou:g} is retained, a different label at that IoU is a class change, "
        "a clean detection left over is dropped, and a degraded one left over is introduced.",
        f"Stability score per frame: dropped × {weights.dropped:g} + introduced × {weights.introduced:g} + class "
        f"changes × {weights.class_changes:g} + confidence lost × {weights.confidence_loss:g}.",
        f"Low n: a rate over fewer than {record.low_n_objects} detections.",
        f"Sample size: {record.frames} frames at {record.frame_width}×{record.frame_height}, detections kept down to the "
        f"confidence floor {record.confidence_floor:g}.",
    ]
    return f"""<section id="run-record">
<h2>Run record</h2>
<h3>Input</h3>
<p>{escape(record.sample_title)} (<code>{escape(record.sample_id)}</code>). Input fingerprint: {fingerprint}</p>
{_model(report)}
<h3>Degradation settings</h3>
<p>{_degradation(record.degradation)}</p>
{_class_mapping(report)}
<h3>Metric definitions</h3>
{_list(definitions)}
{_latency(report.findings.latency)}
</section>"""


def _model(report: Report) -> str:
    model = report.findings.record.model
    provider = f", execution provider {escape(model.provider)}" if model.provider else ""
    size = f", weights {model.size_bytes:,} bytes" if model.size_bytes is not None else ""
    return (
        f"<h3>Model and runtime</h3><p>{escape(model.name)} version {escape(model.version)}, runtime "
        f"{escape(model.runtime)}{provider}{size}.</p>"
    )


def _degradation(degradation: AppliedDegradation) -> str:
    parameters = ", ".join(f"{name} = {value:g}" for name, value in degradation.parameters.items())
    return (
        f"{TITLES[degradation.kind]} — severity {degradation.severity:.2f}, seed {degradation.seed}"
        + (f"; parameters: {escape(parameters)}" if parameters else "")
    )


def _class_mapping(report: Report) -> str:
    # A video run's record doesn't carry the mapping (stability compares raw COCO labels), so it is shown as it stands.
    mapping = report.findings.record.class_mapping if isinstance(report, BenchmarkReport) else CLASS_MAPPING
    rows = [f"{row.coco} → {row.dataset_class}" for row in mapping.mapping]
    video = (
        _note(
            "This run has no labels: its stability compares the detector's own COCO classes, so the mapping and the "
            "ignore rule apply only to Benchmark scoring."
        )
        if isinstance(report, VideoReport)
        else ""
    )
    return (
        f"<h3>Class mapping (version {mapping.version}) and ignore regions</h3>{video}{_list(rows)}"
        f"<p>{escape(mapping.ignore_rule)}</p><p>{escape(mapping.unmapped_rule)}</p>"
    )


def _size_row(name: str, row: ConditionResult) -> str:
    return (
        f'<tr><th scope="row">{escape(name)}</th>{_num(row.frames)}{_num(row.objects)}'
        f"<td>{'low n' if row.low_n else ''}</td></tr>"
    )


def _latency(latency: LatencySummary | None) -> str:
    if latency is None:
        return ""
    stages = [
        ("Read", latency.read),
        ("Degrade", latency.degrade),
        ("Inference", latency.inference),
        ("Processing", latency.processing),
        ("Render", latency.render),
    ]
    rows = "".join(
        f'<tr><th scope="row">{name}</th>{_num(f"{stage.p50_ms:.1f}")}{_num(f"{stage.p90_ms:.1f}")}</tr>'
        for name, stage in stages
        if stage is not None
    )
    fps = f"{latency.effective_fps:.1f}" if latency.effective_fps is not None else "—"
    return (
        f"<h3>Latency on this machine</h3><table><caption>Over {latency.frames} frames and {latency.inference_runs} "
        f"detector calls, the first {latency.warmup_frames} frames left out as warm-up. Effective fps: {fps}."
        f'</caption><thead><tr><th scope="col">Stage</th><th scope="col" class="num">p50 ms</th>'
        f'<th scope="col" class="num">p90 ms</th></tr></thead><tbody>{rows}</tbody></table>'
    )


# --- small pieces ----------------------------------------------------------------------------------------------


def _metric(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def _ap(ap: float | None, objects: int) -> str:
    return f'{_metric(ap)} <span class="n">({objects})</span>'


def _num(value: object) -> str:
    return f'<td class="num">{value}</td>'


def _note(text: str) -> str:
    return f'<p class="note">{escape(text)}</p>'


def _list(items: list[str], raw: bool = False) -> str:
    return "<ul>" + "".join(f"<li>{item if raw else escape(item)}</li>" for item in items) + "</ul>"
