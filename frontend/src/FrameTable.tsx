import { useState } from "react";
import { useBenchmarkFrame } from "./BenchmarkFrame";
import { useBenchmarkResults } from "./BenchmarkResults";
import { conditionName } from "./benchmarkFormat";
import { sortFrames, type FrameColumn, type SortDirection } from "./frameReview";

const COLUMNS: [column: FrameColumn, name: string][] = [
  ["id", "Frame"],
  ["hits", "Hits"],
  ["misses", "Misses"],
  ["false_alarms", "False alarms"],
  ["class_confusions", "Class confusions"],
  ["ignored", "Ignored"],
  ["score", "Error score"],
];

/** The bottom dock's Frame table: the condition's frames and their error counts, sortable by any column. */
export function FrameTable() {
  const { selected: condition, results } = useBenchmarkResults();
  const { ranked, frameId, openFrame } = useBenchmarkFrame();
  const [sort, setSort] = useState<{ column: FrameColumn; direction: SortDirection }>({
    column: "score",
    direction: "descending",
  });
  if (!results || !condition) return <p className="empty-state">Run a benchmark to list its frames.</p>;

  const rows = sortFrames(ranked, sort.column, sort.direction);
  const toggle = (column: FrameColumn) =>
    setSort({
      column,
      direction: sort.column === column && sort.direction === "descending" ? "ascending" : "descending",
    });
  return (
    <table className="subset-table frame-table">
      <caption>
        {conditionName(condition.condition)}: {rows.length} frames at confidence ≥{" "}
        {results.display_threshold.toFixed(2)}. Error score: misses, false alarms and class confusions, each times its weight.
      </caption>
      <thead>
        <tr>
          {COLUMNS.map(([column, name]) => (
            <th key={column} scope="col" aria-sort={sort.column === column ? sort.direction : undefined}>
              <button type="button" className="sort-button" onClick={() => toggle(column)}>
                {name}
                {sort.column === column && (sort.direction === "descending" ? " ▼" : " ▲")}
              </button>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id} aria-current={row.id === frameId ? "true" : undefined}>
            <th scope="row">
              <button type="button" className="link-button" onClick={() => openFrame(row.id)}>
                {row.id}
              </button>
            </th>
            <td>{row.hits}</td>
            <td>{row.misses}</td>
            <td>{row.false_alarms}</td>
            <td>{row.class_confusions}</td>
            <td>{row.ignored}</td>
            <td>{row.score}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
