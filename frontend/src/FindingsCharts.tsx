import { scaleBand, scaleLinear } from "d3-scale";
import type { Comparison, FrameReliability, HeatmapRow } from "./api/client";
import { conditionName, formatMetric } from "./benchmarkFormat";
import { heatmapCellText, textColorOn } from "./findingsFormat";

// Blueprint tokens, as in styles.css: blue is the synthetic side, orange the real (degraded) side. They differ in
// lightness too, and every bar carries its value and series name in text.
const SYNTHETIC = "#8abbff"; // BLUE5
const REAL = "#c87619"; // ORANGE3
const AXIS = "#abb3bf"; // GRAY4
const GRID = "#2f343c"; // DARK_GRAY3

const BAR_WIDTH = 520;
const LABEL_WIDTH = 120;
const VALUE_WIDTH = 150;
const BAR_HEIGHT = 14;

/**
 * Paired per-class drop bars: each class's AP drop under synthetic fog beside its drop under real fog. Drops come from
 * the API; a drop with no AP on one side is drawn as no bar, and says why.
 */
export function DropBars({ synthetic, real }: { synthetic: Comparison | null; real: Comparison | null }) {
  const sides = [
    { key: "synthetic", name: synthetic?.title ?? "Synthetic fog", color: SYNTHETIC, comparison: synthetic },
    { key: "real", name: "Real fog · day", color: REAL, comparison: real },
  ];
  const classes = (real ?? synthetic)?.classes.map((c) => c.class_name) ?? [];
  const drops = sides.flatMap((s) => s.comparison?.classes.map((c) => c.drop) ?? []).filter((d) => d !== null);
  const x = scaleLinear()
    .domain([Math.min(0, ...drops), Math.max(0.1, ...drops)])
    .range([0, BAR_WIDTH - LABEL_WIDTH - VALUE_WIDTH])
    .nice();
  const formatTick = x.tickFormat(4);
  const groupHeight = sides.length * (BAR_HEIGHT + 4) + 12;
  const height = classes.length * groupHeight + 24;
  const zero = LABEL_WIDTH + x(0);

  return (
    <figure className="chart">
      <svg
        role="img"
        aria-label="Per-class AP drop under synthetic fog beside real fog; the same values are in the table below"
        viewBox={`0 0 ${BAR_WIDTH} ${height}`}
        width="100%"
        style={{ maxWidth: BAR_WIDTH }}
      >
        {x.ticks(4).map((tick) => (
          <g key={tick} transform={`translate(${LABEL_WIDTH + x(tick)},0)`}>
            <line y1={0} y2={height - 18} stroke={GRID} />
            <text y={height - 4} textAnchor="middle" fill={AXIS} fontSize={10}>
              {formatTick(tick)}
            </text>
          </g>
        ))}
        {classes.map((className, row) => (
          <g key={className} transform={`translate(0,${row * groupHeight + 4})`}>
            <text x={0} y={BAR_HEIGHT} fill="#f6f7f9" fontSize={11}>
              {className}
            </text>
            {sides.map((side, k) => {
              const cell = side.comparison?.classes.find((c) => c.class_name === className);
              const drop = cell?.drop ?? null;
              const y = k * (BAR_HEIGHT + 4);
              const end = drop === null ? zero : LABEL_WIDTH + x(drop);
              return (
                <g key={side.key}>
                  {drop !== null && (
                    <rect x={Math.min(zero, end)} y={y} width={Math.abs(end - zero)} height={BAR_HEIGHT} fill={side.color} />
                  )}
                  <text x={Math.max(zero, end) + 4} y={y + BAR_HEIGHT - 3} fill={AXIS} fontSize={10}>
                    {side.key === "synthetic" ? "Synthetic" : "Real"}{" "}
                    {drop === null ? (side.comparison ? "— no AP" : "— not run") : formatMetric(drop)}
                  </text>
                </g>
              );
            })}
          </g>
        ))}
        <line x1={zero} x2={zero} y1={0} y2={height - 18} stroke={AXIS} />
      </svg>
      <figcaption className="chart-legend">
        {sides.map((side) => (
          <span key={side.key}>
            <span className="swatch" style={{ background: side.color }} aria-hidden /> {side.name}
          </span>
        ))}
        <span>AP drop from Clear · day (positive: AP fell)</span>
      </figcaption>
    </figure>
  );
}

// From the panel's dark gray at AP 0 to blue at AP 1: lightness carries the value, and every cell prints it.
const apColor = scaleLinear<string>().domain([0, 1]).range(["#2f343c", "#8abbff"]).clamp(true);

/** Condition-by-class AP, with mAP per condition and the counts behind every cell. Low-n cells carry a star. */
export function ApHeatmap({ rows, lowN }: { rows: HeatmapRow[]; lowN: number }) {
  const classes = rows[0]?.cells.map((c) => c.class_name) ?? [];
  return (
    <table className="heatmap">
      <caption>
        AP by condition and class. * fewer than {lowN} objects (low n): read as noise. — no objects of that class.
      </caption>
      <thead>
        <tr>
          <th scope="col">Condition</th>
          {classes.map((name) => (
            <th scope="col" key={name}>
              {name}
            </th>
          ))}
          <th scope="col">mAP</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.condition}>
            <th scope="row">
              {conditionName(row.condition)}
              <span className="heatmap-counts">
                {row.frames} {row.frames === 1 ? "frame" : "frames"}
              </span>
            </th>
            {row.cells.map((cell) => (
              <HeatCell key={cell.class_name} text={heatmapCellText(cell)} ap={cell.ap} objects={cell.objects} />
            ))}
            <HeatCell text={`${formatMetric(row.map)}${row.low_n && row.map !== null ? "*" : ""}`} ap={row.map} objects={row.objects} />
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function HeatCell({ text, ap, objects }: { text: string; ap: number | null; objects: number }) {
  const fill = ap === null ? undefined : apColor(ap);
  return (
    <td style={fill ? { background: fill, color: textColorOn(fill) } : undefined}>
      <span className="heatmap-value">{text}</span>
      <span className="heatmap-counts">
        {objects} {objects === 1 ? "obj" : "objs"}
      </span>
    </td>
  );
}

const TIMELINE_WIDTH = 640;
const TIMELINE_HEIGHT = 140;
const MARGIN = { top: 8, right: 8, bottom: 22, left: 32 };

/** Frame-by-frame stability score on a video run, so a sudden failure shows as a spike. Video runs only. */
export function ReliabilityTimeline({ timeline }: { timeline: FrameReliability[] }) {
  const peak = timeline.reduce<FrameReliability | null>((worst, p) => (!worst || p.score > worst.score ? p : worst), null);
  const x = scaleBand<number>()
    .domain(timeline.map((p) => p.index))
    .range([MARGIN.left, TIMELINE_WIDTH - MARGIN.right])
    .padding(0.15);
  const y = scaleLinear()
    .domain([0, Math.max(1, peak?.score ?? 0)])
    .range([TIMELINE_HEIGHT - MARGIN.bottom, MARGIN.top])
    .nice();
  const every = Math.max(1, Math.ceil(timeline.length / 8));

  return (
    <figure className="chart">
      <svg
        role="img"
        aria-label={`Stability score for each of ${timeline.length} frames; highest ${peak ? `${peak.score.toFixed(2)} at frame ${peak.index}` : "none"}`}
        viewBox={`0 0 ${TIMELINE_WIDTH} ${TIMELINE_HEIGHT}`}
        width="100%"
        style={{ maxWidth: TIMELINE_WIDTH }}
      >
        {y.ticks(3).map((tick) => (
          <g key={tick}>
            <line x1={MARGIN.left} x2={TIMELINE_WIDTH - MARGIN.right} y1={y(tick)} y2={y(tick)} stroke={GRID} />
            <text x={MARGIN.left - 4} y={y(tick) + 3} textAnchor="end" fill={AXIS} fontSize={10}>
              {tick}
            </text>
          </g>
        ))}
        {timeline.map((p) => (
          <rect key={p.index} x={x(p.index)} width={x.bandwidth()} y={y(p.score)} height={y(0) - y(p.score)} fill={REAL} />
        ))}
        {timeline
          .filter((p) => p.index % every === 0)
          .map((p) => (
            <text key={p.index} x={(x(p.index) ?? 0) + x.bandwidth() / 2} y={TIMELINE_HEIGHT - 6} textAnchor="middle" fill={AXIS} fontSize={10}>
              {p.index}
            </text>
          ))}
      </svg>
      <figcaption className="chart-legend">
        <span>
          <span className="swatch" style={{ background: REAL }} aria-hidden /> Degraded vs. clean: stability score per
          frame (dropped + introduced + class changes + confidence lost)
        </span>
        <span>
          {peak && peak.score > 0
            ? `Least stable: frame ${peak.index}, score ${peak.score.toFixed(2)}`
            : "No frame changed under the degradation."}
        </span>
      </figcaption>
    </figure>
  );
}
