import type { FrontendRenderer } from "@streamlit/component-v2-lib";
import { mountEvidence, type EvidenceData } from "./workspace";
import "./style.css";

const render: FrontendRenderer<Record<string, never>, EvidenceData> = ({ parentElement, data }) => {
  const root = parentElement.querySelector<HTMLElement>(".component-root");
  if (!root) throw new Error("Evidence root is missing");
  return mountEvidence(root, data);
};

export default render;
