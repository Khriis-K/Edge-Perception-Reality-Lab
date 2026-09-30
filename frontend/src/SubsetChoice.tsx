import { createContext, useContext, useState, type ReactNode } from "react";

/** The seed and cap the user chose; null until they change one, so the server's defaults apply. */
export type SubsetChoice = { seed: number; cap: number } | null;

type SubsetChoiceState = [SubsetChoice, (choice: SubsetChoice) => void];

const SubsetChoiceContext = createContext<SubsetChoiceState | null>(null);

/** Chosen in Setup's Subset table, run from the Benchmark screen: both draw the same subset. */
export function SubsetChoiceProvider({ children }: { children: ReactNode }) {
  const state = useState<SubsetChoice>(null);
  return <SubsetChoiceContext.Provider value={state}>{children}</SubsetChoiceContext.Provider>;
}

export function useSubsetChoice(): SubsetChoiceState {
  const value = useContext(SubsetChoiceContext);
  if (!value) throw new Error("useSubsetChoice needs a SubsetChoiceProvider");
  return value;
}
