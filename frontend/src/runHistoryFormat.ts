interface RunOfInput {
  sample_id: string;
  sample_title: string;
}

export interface InputGroup<Run> {
  sampleId: string;
  title: string;
  runs: Run[];
}

/** Runs grouped by the input they ran on. The runs come newest first, so the groups and their runs stay that way. */
export function groupByInput<Run extends RunOfInput>(runs: Run[]): InputGroup<Run>[] {
  const groups = new Map<string, InputGroup<Run>>();
  for (const run of runs) {
    const group = groups.get(run.sample_id) ?? { sampleId: run.sample_id, title: run.sample_title, runs: [] };
    group.runs.push(run);
    groups.set(run.sample_id, group);
  }
  return [...groups.values()];
}

const UNITS = ["kB", "MB", "GB", "TB"];

/** Decimal units, as file managers show sizes. */
export function formatBytes(bytes: number): string {
  if (bytes < 1000) return `${bytes} B`;
  let value = bytes;
  let unit = -1;
  while (value >= 1000 && unit < UNITS.length - 1) {
    value /= 1000;
    unit += 1;
  }
  return `${value.toFixed(1)} ${UNITS[unit]}`;
}
