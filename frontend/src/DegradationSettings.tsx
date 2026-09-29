import { HTMLSelect } from "@blueprintjs/core";
import { createContext, useContext, useEffect, useId, useState, type ReactNode } from "react";
import {
  fetchDegradationParameters,
  fetchDegradations,
  type Degradation,
  type DegradationSettings,
} from "./api/client";
import { isActive, useCurrentJob } from "./CurrentJob";

const DEFAULT_SETTINGS: DegradationSettings = { kind: "fog", severity: 0.5, seed: 0 };
const MAX_SEED = 2 ** 32 - 1; // the server's limit

interface SettingsState {
  settings: DegradationSettings;
  update: (change: Partial<DegradationSettings>) => void;
}

const SettingsContext = createContext<SettingsState | null>(null);

/**
 * The degradation the next Synthetic run applies. Edited in the inspector, read by the run form,
 * so it lives above both (and survives the narrow-layout drawer closing).
 */
export function DegradationSettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const update = (change: Partial<DegradationSettings>) => setSettings((current) => ({ ...current, ...change }));
  return <SettingsContext.Provider value={{ settings, update }}>{children}</SettingsContext.Provider>;
}

export function useDegradationSettings(): SettingsState {
  const value = useContext(SettingsContext);
  if (!value) throw new Error("useDegradationSettings needs a DegradationSettingsProvider");
  return value;
}

/** The Synthetic inspector: one degradation, its severity, the parameters derived from it, and the seed. */
export function DegradationInspector() {
  const { settings, update } = useDegradationSettings();
  const running = isActive(useCurrentJob().job);
  const catalog = useCatalog();
  const parameters = useDerivedParameters(settings);
  const ids = { kind: useId(), severity: useId(), parameters: useId(), seed: useId() };
  const randomized = catalog.degradations.find((d) => d.kind === settings.kind)?.randomized;

  return (
    <section aria-label="Degradation" className="degradation-inspector">
      <h3 className="inspector-heading">Degradation</h3>
      <div className="field">
        <label htmlFor={ids.kind}>Type</label>
        <HTMLSelect
          id={ids.kind}
          value={settings.kind}
          disabled={running}
          onChange={(e) => update({ kind: e.target.value as DegradationSettings["kind"] })}
        >
          {catalog.degradations.map((d) => (
            <option key={d.kind} value={d.kind}>
              {d.title}
            </option>
          ))}
        </HTMLSelect>
      </div>

      <div className="field">
        <label htmlFor={ids.severity}>Severity</label>
        <div className="field-row">
          <input
            id={ids.severity}
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={settings.severity}
            disabled={running}
            onChange={(e) => update({ severity: Number(e.target.value) })}
          />
          {/* Not an <output>: that is a live region, and the slider already announces its value. */}
          <span className="field-value">{settings.severity.toFixed(2)}</span>
        </div>
      </div>

      <div className="field">
        <span id={ids.parameters}>Derived parameters</span>
        {parameters.values ? (
          <dl aria-labelledby={ids.parameters} className="parameters">
            {Object.entries(parameters.values).map(([name, value]) => (
              <div key={name}>
                <dt>{name}</dt>
                <dd>{formatParameter(value)}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="field-note">{parameters.error ?? "Loading…"}</p>
        )}
      </div>

      <div className="field">
        <label htmlFor={ids.seed}>Seed</label>
        <input
          id={ids.seed}
          className="bp6-input"
          type="number"
          min={0}
          max={MAX_SEED}
          step={1}
          value={settings.seed}
          disabled={running}
          onChange={(e) => update({ seed: toSeed(e.target.value) })}
        />
        <p className="field-note">
          {randomized === false
            ? "Stored with the run. This degradation is deterministic, so the seed doesn't change it."
            : "Stored with the run, so the same seed reproduces the same noise."}
        </p>
      </div>

      {catalog.error && (
        <p role="alert" className="run-error">
          {catalog.error}
        </p>
      )}
    </section>
  );
}

function useCatalog(): { degradations: Degradation[]; error: string | null } {
  const [degradations, setDegradations] = useState<Degradation[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetchDegradations()
      .then(setDegradations)
      .catch((e) => setError(`Could not load the degradations: ${(e as Error).message}`));
  }, []);
  return { degradations, error };
}

/** Asked of the server, so the inspector shows exactly the values a run will record. */
function useDerivedParameters({ kind, severity }: DegradationSettings) {
  // Tagged with the settings they belong to, so values for the previous choice are never shown.
  const key = `${kind}@${severity}`;
  const [loaded, setLoaded] = useState<{ key: string; values: Record<string, number> } | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    fetchDegradationParameters(kind, severity, controller.signal)
      .then((values) => setLoaded({ key, values }))
      .catch((e) => {
        if (!controller.signal.aborted) setError(`Could not load the parameters: ${(e as Error).message}`);
      });
    return () => controller.abort();
  }, [kind, severity]); // `key` is derived from these two
  return { values: loaded?.key === key ? loaded.values : null, error };
}

function formatParameter(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(3);
}

function toSeed(text: string): number {
  const value = Math.floor(Number(text));
  return Number.isFinite(value) ? Math.min(Math.max(value, 0), MAX_SEED) : 0;
}
