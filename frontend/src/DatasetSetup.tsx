import { Button, Icon } from "@blueprintjs/core";
import type { DatasetPartStatus, DatasetStatus } from "./api/client";
import { SubsetTable } from "./SubsetTable";
import { useDatasetStatus } from "./useDatasetStatus";

/**
 * The dataset folder, read-only: it is set when the backend starts (--dataset or EDGE_LAB_DATASET),
 * never from the browser. Shows whether each required part is present, and what can be skipped.
 */
export function DatasetSetup() {
  const { status, error, checking, recheck } = useDatasetStatus();

  return (
    <section aria-labelledby="dataset-heading" className="dataset-setup">
      <h2 id="dataset-heading">Dataset</h2>

      <div className="dataset-folder">
        <label htmlFor="dataset-folder">Dataset folder</label>
        <input
          id="dataset-folder"
          readOnly
          value={status ? (status.root ?? "Not configured") : ""}
          placeholder="Checking…"
        />
        <Button text="Re-check" icon="refresh" onClick={recheck} loading={checking} />
      </div>

      <p aria-live="polite" className="dataset-message">
        {error ? `Couldn't check the dataset: ${error}` : status?.message}
      </p>

      {status && <Parts status={status} />}
      <SubsetTable ready={status?.ready ?? false} />
      {status && <NotNeeded items={status.not_needed} />}
    </section>
  );
}

function Parts({ status }: { status: DatasetStatus }) {
  return (
    <ul aria-label="Required dataset parts" className="dataset-parts">
      {status.parts.map((part) => (
        <PartRow key={part.key} part={part} />
      ))}
    </ul>
  );
}

function PartRow({ part }: { part: DatasetPartStatus }) {
  // The word carries the state; the icon and colour only reinforce it.
  const state = part.present ? "Present" : part.checked ? "Missing" : "Not checked";

  return (
    <li className="dataset-part" data-present={part.present}>
      <Icon icon={part.present ? "tick-circle" : "error"} aria-hidden />
      <div>
        <p>
          <strong>{state}</strong> · {part.name} <code>{part.folder}</code>
        </p>
        <p className="dataset-part-message">{part.message}</p>
        {!part.present && (
          <details>
            <summary>Diagnostic detail</summary>
            <code>{part.detail}</code>
          </details>
        )}
      </div>
    </li>
  );
}

function NotNeeded({ items }: { items: string[] }) {
  return (
    <div className="dataset-not-needed">
      <h3>Not needed: skip extracting these</h3>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <p>
        Check that every <code>.z01</code>…<code>.zNN</code> part is downloaded and that extraction finishes with no
        CRC errors.
      </p>
    </div>
  );
}
