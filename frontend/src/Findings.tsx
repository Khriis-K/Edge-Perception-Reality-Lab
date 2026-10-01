import { Button } from "@blueprintjs/core";
import { useState, type FormEvent, type ReactNode } from "react";
import {
  datasetFrameUrl,
  frameImageUrl,
  type BenchmarkFindings,
  type Comparison,
  type FindingKey,
  type CurveSide,
  type PRCurves,
  type Side,
  type FrameReliability,
  type VideoFindings,
  type WorstFrame,
} from "./api/client";
import { conditionName, formatMetric } from "./benchmarkFormat";
import { ApHeatmap, CURVE_STYLES, DropBars, PrCurves, ReliabilityTimeline } from "./FindingsCharts";
import { useFindings } from "./FindingsData";
import { reliabilityReason, worstReason } from "./findingsFormat";
import { scoreParts } from "./frameReview";

// The numbered findings each kind of run has, in order. A finding's anchor is its key.
const BENCHMARK_OUTLINE: { key: FindingKey; title: string }[] = [
  { key: "sim-to-real", title: "Sim-to-real" },
  { key: "where-it-fails", title: "Where it fails" },
  { key: "precision-recall", title: "Precision–recall" },
];
const VIDEO_OUTLINE: { key: FindingKey; title: string }[] = [{ key: "reliability-timeline", title: "Reliability timeline" }];
const GALLERY_ID = "worst-frames";

/** Findings: a findings-first document for one run, each numbered finding led by the user's own headline. */
export function FindingsDocument() {
  const { runs, findings, error } = useFindings();
  if (error) return <p role="alert" className="run-error">{error}</p>;
  if (runs === null) return null;
  if (runs.length === 0) {
    return <p className="empty-state">No finished runs yet. Run a benchmark, or a synthetic run on a video.</p>;
  }
  return (
    <div className="findings">
      <RunPicker />
      {findings?.kind === "benchmark" && <BenchmarkDocument findings={findings} />}
      {findings?.kind === "video" && <VideoDocument findings={findings} />}
    </div>
  );
}

/** Which finished run is open: shared with the Report screen, which exports the same run. */
export function RunPicker() {
  const { runs, openId, open } = useFindings();
  return (
    <label className="findings-run">
      Run
      <select value={openId ?? ""} onChange={(event) => open(event.target.value)}>
        {runs?.map((run) => (
          <option key={run.id} value={run.id}>
            {run.title}
          </option>
        ))}
      </select>
    </label>
  );
}

function BenchmarkDocument({ findings }: { findings: BenchmarkFindings }) {
  const { sim_to_real: sim } = findings;
  const { weights } = findings.record;
  const [pick, setPick] = useState<string | null>(null);
  const synthetic = sim.synthetic.find((s) => s.experiment_id === pick) ?? sim.synthetic[0] ?? null;
  return (
    <article aria-label="Findings">
      <Finding number={1} outline={BENCHMARK_OUTLINE[0]} headline={findings.headlines["sim-to-real"]}>
        <p role="note" className="findings-caveat">
          Distributional, not paired: the real-fog frames are different scenes from the clear ones. Both sides are
          daytime to limit the lighting confound.
        </p>
        {sim.reference === null ? (
          <p className="field-note">This run has no Clear · day frames, so there is nothing to compare against.</p>
        ) : (
          <>
            {sim.synthetic.length > 1 && (
              <label className="findings-run">
                Synthetic run
                <select value={synthetic?.experiment_id ?? ""} onChange={(event) => setPick(event.target.value)}>
                  {sim.synthetic.map((s) => (
                    <option key={s.experiment_id} value={s.experiment_id ?? ""}>
                      {s.title}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <dl className="headline-numbers" aria-label="Headline numbers">
              <HeadlineNumber name="Clear · day" side={sim.reference} />
              {synthetic ? (
                <HeadlineNumber name={synthetic.title} side={synthetic} drop={synthetic.map_drop} />
              ) : (
                <div>
                  <dt>Synthetic fog</dt>
                  <dd>Not run yet: run synthetic fog on the Clear · day frames in Synthetic.</dd>
                </div>
              )}
              {sim.real ? (
                <HeadlineNumber name={sim.real.title} side={sim.real} drop={sim.real.map_drop} />
              ) : (
                <div>
                  <dt>Real fog · day</dt>
                  <dd>No Fog · day frames in this run.</dd>
                </div>
              )}
            </dl>
            <DropBars synthetic={synthetic} real={sim.real} />
            <DropTable synthetic={synthetic} real={sim.real} lowN={findings.record.low_n_objects} />
          </>
        )}
      </Finding>
      <Finding number={2} outline={BENCHMARK_OUTLINE[1]} headline={findings.headlines["where-it-fails"]}>
        <ApHeatmap rows={findings.conditions} lowN={findings.record.low_n_objects} />
      </Finding>
      <Finding number={3} outline={BENCHMARK_OUTLINE[2]} headline={findings.headlines["precision-recall"]}>
        <PrFinding
          curves={findings.pr_curves}
          syntheticId={synthetic?.experiment_id ?? null}
          threshold={findings.display_threshold}
        />
      </Finding>
      <Gallery
        note={`Ranked by error score at confidence ≥ ${findings.display_threshold.toFixed(2)}: misses × ${weights.misses} + false alarms × ${weights.false_alarms} + class confusions × ${weights.class_confusions}.`}
      >
        {findings.worst_frames.map((frame) => (
          <BenchmarkCard key={frame.id} frame={frame} reason={worstReason(frame, weights)} />
        ))}
      </Gallery>
    </article>
  );
}

function VideoDocument({ findings }: { findings: VideoFindings }) {
  const { record } = findings;
  const { weights } = record;
  return (
    <article aria-label="Findings">
      <Finding number={1} outline={VIDEO_OUTLINE[0]} headline={findings.headlines["reliability-timeline"]}>
        <p className="field-note">
          {record.sample_title}, {record.frames} frames: stability relative to the clean baseline, not accuracy.
        </p>
        <ReliabilityTimeline timeline={findings.timeline} worst={findings.worst_frames[0] ?? null} />
      </Finding>
      <Gallery
        note={`Ranked by stability score: dropped × ${weights.dropped} + introduced × ${weights.introduced} + class changes × ${weights.class_changes} + confidence lost × ${weights.confidence_loss}.`}
      >
        {findings.worst_frames.map((point) => (
          <VideoCard
            key={point.index}
            experimentId={findings.id}
            point={point}
            reason={reliabilityReason(point, weights)}
          />
        ))}
      </Gallery>
    </article>
  );
}

type FindingProps = {
  number: number;
  outline: { key: FindingKey; title: string };
  headline: string | undefined;
  children: ReactNode;
};

function Finding({ number, outline, headline, children }: FindingProps) {
  const label = `Finding ${String(number).padStart(2, "0")} · ${outline.title}`;
  return (
    <section id={outline.key} aria-label={label} className="finding">
      <h2 className="finding-number">{label}</h2>
      <HeadlineEditor findingKey={outline.key} label={label} saved={headline ?? ""} />
      {children}
    </section>
  );
}

/**
 * The user's one-sentence headline for a finding. Nothing writes it for them: until they do, an empty field asks for
 * it. Saved with the run, so it is there after a reload.
 */
function HeadlineEditor({ findingKey, label, saved }: { findingKey: FindingKey; label: string; saved: string }) {
  const { openId, saveHeadline } = useFindings();
  // Keyed by run and saved text, so opening another run (or a save) resets the draft.
  const [draft, setDraft] = useState({ for: `${openId}:${saved}`, text: saved });
  const [status, setStatus] = useState<string | null>(null);
  const text = draft.for === `${openId}:${saved}` ? draft.text : saved;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setStatus("Saving…");
    try {
      await saveHeadline(findingKey, text);
      setStatus(text.trim() ? "Saved with the run." : "Cleared.");
    } catch (e) {
      setStatus(`Not saved: ${(e as Error).message}`);
    }
  }

  return (
    <form className="headline-editor" onSubmit={submit}>
      <input
        aria-label={`Headline for ${label}`}
        className="headline-input"
        value={text}
        maxLength={500}
        placeholder="Write this finding's headline from the results below, in one plain sentence."
        onChange={(event) => setDraft({ for: `${openId}:${saved}`, text: event.target.value })}
      />
      <Button type="submit" size="small" disabled={text.trim() === saved}>
        Save headline
      </Button>
      {status && <span className="field-note" role="status">{status}</span>}
    </form>
  );
}

/**
 * Each class's PR curve on clear, synthetic-fog and real-fog frames, so a reader sees every threshold, not one cutoff:
 * whether fog caps recall or only lowers confidence. The synthetic side is the run picked in Finding 01. The class
 * picker only switches which of the curves already loaded is drawn.
 */
function PrFinding({ curves, syntheticId, threshold }: { curves: PRCurves; syntheticId: string | null; threshold: number }) {
  const classes = curves.reference?.classes.map((c) => c.class_name) ?? [];
  const [pickedClass, setPickedClass] = useState<string | null>(null);
  if (curves.reference === null) {
    return <p className="field-note">This run has no Clear · day frames, so there is nothing to compare against.</p>;
  }
  const className = pickedClass ?? curves.reference.classes.find((c) => c.objects > 0)?.class_name ?? classes[0];
  const synthetic = curves.synthetic.find((s) => s.experiment_id === syntheticId) ?? null;
  const classOn = (side: CurveSide | null) => side?.classes.find((c) => c.class_name === className);
  return (
    <>
      <label className="findings-run">
        Class
        <select value={className} onChange={(event) => setPickedClass(event.target.value)}>
          {classes.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>
      <PrCurves
        className={className}
        threshold={threshold}
        lines={[
          { name: curves.reference.title, ...CURVE_STYLES.reference, metrics: classOn(curves.reference), absent: "" },
          {
            name: synthetic?.title ?? "Synthetic fog",
            ...CURVE_STYLES.synthetic,
            metrics: classOn(synthetic),
            absent: "not run on the Clear · day frames yet",
          },
          {
            name: curves.real?.title ?? "Real fog · day",
            ...CURVE_STYLES.real,
            metrics: classOn(curves.real),
            absent: "no Fog · day frames in this run",
          },
        ]}
      />
    </>
  );
}

/** One side's mAP, its drop from Clear · day, and the objects and frames behind it. */
function HeadlineNumber({ name, side, drop }: { name: string; side: Side; drop?: number | null }) {
  const { map, objects, frames } = side;
  return (
    <div>
      <dt>{name}</dt>
      <dd>
        <span className="metric-value">mAP {formatMetric(map)}</span>
        {drop !== undefined && <span className="metric-value"> · drop {formatMetric(drop)}</span>}{" "}
        <span className="metric-counts">
          {objects} {objects === 1 ? "object" : "objects"}, {frames} {frames === 1 ? "frame" : "frames"}
        </span>
        {side.low_n && (
          <>
            {" "}
            <span className="low-n">low n</span>
          </>
        )}
      </dd>
    </div>
  );
}

/** The drop bars' numbers, with the objects behind each AP on both sides. */
function DropTable({ synthetic, real, lowN }: { synthetic: Comparison | null; real: Comparison | null; lowN: number }) {
  const classes = (real ?? synthetic)?.classes ?? [];
  const at = (side: Comparison | null, name: string) => side?.classes.find((c) => c.class_name === name);
  return (
    <table className="subset-table drop-table">
      <caption>
        AP drop from Clear · day; objects in brackets. <span className="low-n">low n</span>: fewer than {lowN} objects
        on either side.
      </caption>
      <thead>
        <tr>
          <th scope="col">Class</th>
          <th scope="col">Clear · day AP</th>
          <th scope="col">Synthetic drop</th>
          <th scope="col">Real drop</th>
          <th scope="col">Sample size</th>
        </tr>
      </thead>
      <tbody>
        {classes.map(({ class_name: name }) => {
          const [s, r] = [at(synthetic, name), at(real, name)];
          const reference = s ?? r!;
          return (
            <tr key={name}>
              <th scope="row">{name}</th>
              <td>
                {formatMetric(reference.reference_ap)} ({reference.reference_objects})
              </td>
              <td>{s ? `${formatMetric(s.drop)} (${s.objects})` : "not run"}</td>
              <td>{r ? `${formatMetric(r.drop)} (${r.objects})` : "—"}</td>
              <td>{(s?.low_n || r?.low_n) && <span className="low-n">low n</span>}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Gallery({ note, children }: { note: string; children: ReactNode[] }) {
  return (
    <section id={GALLERY_ID} aria-label="Worst frames" className="finding">
      <h2 className="finding-number">Worst frames</h2>
      <p className="field-note">
        {note} Images are shown here, on this machine, only; a report names dataset frames by id.
      </p>
      {children.length === 0 ? (
        <p className="field-note">No frame has an error to rank.</p>
      ) : (
        <ol className="gallery">{children}</ol>
      )}
    </section>
  );
}

function BenchmarkCard({ frame, reason }: { frame: WorstFrame; reason: string }) {
  return (
    <li className="gallery-card">
      <img src={datasetFrameUrl(frame.id)} alt={`Frame ${frame.id}`} loading="lazy" />
      <span className="gallery-title">{frame.id}</span>
      <span className="run-meta">
        {conditionName(frame.condition)} · score {frame.score}
      </span>
      <span>{reason}</span>
      <span className="run-meta">
        {scoreParts(frame)} · {frame.hits} {frame.hits === 1 ? "hit" : "hits"}
      </span>
    </li>
  );
}

function VideoCard({ experimentId, point, reason }: { experimentId: string; point: FrameReliability; reason: string }) {
  return (
    <li className="gallery-card">
      <img src={frameImageUrl(experimentId, "degraded", point.index)} alt={`Degraded frame ${point.index}`} loading="lazy" />
      <span className="gallery-title">Frame {point.index}</span>
      <span className="run-meta">score {point.score.toFixed(2)}</span>
      <span>{reason}</span>
      <span className="run-meta">
        {point.dropped} dropped · {point.introduced} introduced · {point.class_changes} class changes · confidence lost{" "}
        {point.confidence_loss.toFixed(2)} · {point.retained} retained
      </span>
    </li>
  );
}

/** Findings' explorer: an outline of the findings, then the conditions with their mAP. */
export function FindingsExplorer({ empty }: { empty: string }) {
  const { findings } = useFindings();
  if (!findings) return <p className="empty-state">{empty}</p>;
  const outline = findings.kind === "benchmark" ? BENCHMARK_OUTLINE : VIDEO_OUTLINE;
  return (
    <div className="run-explorer">
      <ol aria-label="Outline" className="run-list">
        {outline.map((item, i) => (
          <li key={item.key}>
            <a className="run-item" href={`#${item.key}`}>
              <span>
                {String(i + 1).padStart(2, "0")} · {item.title}
              </span>
              <span className="run-meta">{findings.headlines[item.key] ?? "No headline yet"}</span>
            </a>
          </li>
        ))}
        <li>
          <a className="run-item" href={`#${GALLERY_ID}`}>
            Worst frames
          </a>
        </li>
      </ol>
      {findings.kind === "benchmark" && (
        <>
          <h3 className="run-group">Conditions</h3>
          <ul aria-label="Conditions" className="run-list">
            {findings.conditions.map((row) => (
              <li key={row.condition} className="run-item">
                <span>{conditionName(row.condition)}</span>
                <span className="run-meta">
                  mAP {formatMetric(row.map)} · {row.objects} {row.objects === 1 ? "object" : "objects"}
                  {row.low_n && (
                    <>
                      {" · "}
                      <span className="low-n">low n</span>
                    </>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
