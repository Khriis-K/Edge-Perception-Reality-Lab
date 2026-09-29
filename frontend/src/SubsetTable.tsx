import { useEffect, useId, useMemo, useState } from "react";
import { fetchSubset, type ConditionSummary, type Manifest, type Subset } from "./api/client";

const DEFAULT_SEED = 0;
const DEFAULT_CAP = 300;
const MAX_CAP = 100_000; // the server's limit

/**
 * The seeded subset: up to `cap` frames per condition, drawn with `seed`. Shows per condition how many frames and
 * objects it holds and its rarest class, flags conditions too small to trust, and offers the manifest to save.
 */
export function SubsetTable({ ready }: { ready: boolean }) {
  const [seed, setSeed] = useState(DEFAULT_SEED);
  const [cap, setCap] = useState(DEFAULT_CAP);
  const { subset, error, loading } = useSubset(ready, seed, cap);
  const ids = { seed: useId(), cap: useId() };

  return (
    <section aria-labelledby="subset-heading" className="subset">
      <h2 id="subset-heading">Subset</h2>
      {!ready ? (
        <p className="dataset-message">The subset needs a ready dataset.</p>
      ) : (
        <>
          <div className="subset-controls">
            <div className="field">
              <label htmlFor={ids.seed}>Seed</label>
              <input
                id={ids.seed}
                className="bp6-input"
                type="number"
                min={0}
                step={1}
                value={seed}
                onChange={(e) => setSeed(toWhole(e.target.value, 0, Number.MAX_SAFE_INTEGER))}
              />
            </div>
            <div className="field">
              <label htmlFor={ids.cap}>Frames per condition</label>
              <input
                id={ids.cap}
                className="bp6-input"
                type="number"
                min={1}
                max={MAX_CAP}
                step={1}
                value={cap}
                onChange={(e) => setCap(toWhole(e.target.value, 1, MAX_CAP))}
              />
            </div>
          </div>

          <p aria-live="polite" className="dataset-message">
            {error
              ? `Couldn't draw the subset: ${error}`
              : loading
                ? "Reading the dataset… The first time, this takes a few minutes on the full dataset."
                : null}
          </p>

          {subset && <SubsetBody subset={subset} />}
        </>
      )}
    </section>
  );
}

function SubsetBody({ subset }: { subset: Subset }) {
  const { manifest } = subset;
  return (
    <>
      <p>
        Seed {manifest.seed}, up to {manifest.cap} frames per condition · {subset.excluded_total} samples excluded
      </p>
      <Excluded subset={subset} />
      <table className="subset-table">
        <caption>
          <span className="low-n">low n</span>: the condition's rarest class has fewer than {subset.low_n_objects}{" "}
          objects, too few to trust its AP.
        </caption>
        <thead>
          <tr>
            <th scope="col">Condition</th>
            <th scope="col">Frames</th>
            <th scope="col">Objects</th>
            <th scope="col">Smallest class</th>
            <th scope="col">Sample size</th>
          </tr>
        </thead>
        <tbody>
          {subset.conditions.map((row) => (
            <ConditionRow key={row.condition} row={row} />
          ))}
        </tbody>
      </table>
      <ManifestLink manifest={manifest} />
    </>
  );
}

function ConditionRow({ row }: { row: ConditionSummary }) {
  return (
    <tr>
      <th scope="row">{conditionName(row.condition)}</th>
      <td>{row.frames}</td>
      <td>{row.objects}</td>
      <td>
        {row.smallest_class} {row.smallest_class_count}
      </td>
      {/* The words carry the flag; the colour only reinforces it. */}
      <td>{row.low_n && <span className="low-n">low n</span>}</td>
    </tr>
  );
}

function Excluded({ subset }: { subset: Subset }) {
  const reasons = Object.entries(subset.excluded);
  if (reasons.length === 0) return null;
  return (
    <details>
      <summary>Why samples were excluded</summary>
      <ul>
        {reasons.map(([reason, count]) => (
          <li key={reason}>
            {reason}: {count}
          </li>
        ))}
      </ul>
      {subset.problems.length > 0 && (
        <ul aria-label="Unreadable files">
          {subset.problems.map((problem) => (
            <li key={problem}>
              <code>{problem}</code>
            </li>
          ))}
        </ul>
      )}
    </details>
  );
}

/** The manifest as a file to commit alongside the experiment. */
function ManifestLink({ manifest }: { manifest: Manifest }) {
  const href = useMemo(
    () => URL.createObjectURL(new Blob([JSON.stringify(manifest, null, 2) + "\n"], { type: "application/json" })),
    [manifest],
  );
  useEffect(() => () => URL.revokeObjectURL(href), [href]);

  return (
    <a href={href} download={`subset-manifest-seed${manifest.seed}-cap${manifest.cap}.json`}>
      Download manifest
    </a>
  );
}

function useSubset(ready: boolean, seed: number, cap: number) {
  const [subset, setSubset] = useState<Subset | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ready) return;
    const controller = new AbortController();
    setLoading(true);
    fetchSubset(seed, cap, controller.signal)
      .then((result) => {
        setSubset(result);
        setError(null);
      })
      .catch((reason) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : String(reason));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [ready, seed, cap]);

  return { subset, error, loading };
}

/** "fog-night" → "Fog · night". */
function conditionName(condition: string): string {
  const [weather, light] = condition.split("-");
  return `${weather.charAt(0).toUpperCase()}${weather.slice(1)} · ${light}`;
}

function toWhole(value: string, min: number, max: number): number {
  const number = Math.trunc(Number(value));
  return Number.isFinite(number) ? Math.min(Math.max(number, min), max) : min;
}
