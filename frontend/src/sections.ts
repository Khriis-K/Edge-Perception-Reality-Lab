import type { IconName } from "@blueprintjs/icons";

export interface Section {
  id: string;
  label: string;
  icon: IconName;
  explorerTitle: string;
  explorerEmpty: string;
}

// The rail's five sections, in order. The fourth is "Findings", never "Analysis".
export const SECTIONS: Section[] = [
  { id: "setup", label: "Setup", icon: "locate", explorerTitle: "Runs", explorerEmpty: "No runs yet." },
  { id: "benchmark", label: "Benchmark", icon: "grid-view", explorerTitle: "Conditions", explorerEmpty: "No benchmark run yet." },
  { id: "synthetic", label: "Synthetic", icon: "layers", explorerTitle: "Synthetic runs", explorerEmpty: "No synthetic runs yet." },
  { id: "findings", label: "Findings", icon: "timeline-bar-chart", explorerTitle: "Outline", explorerEmpty: "No findings yet." },
  { id: "report", label: "Report", icon: "document", explorerTitle: "Exports", explorerEmpty: "No exports yet." },
];

export function findSection(id: string | undefined): Section | undefined {
  return SECTIONS.find((section) => section.id === id);
}
