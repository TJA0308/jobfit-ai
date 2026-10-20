import { afterEach, describe, expect, it } from "vitest";
import { mountEvidence, type EvidenceData, type Match } from "./workspace";

const match: Match = {
  requirement: "Build Python services", status: "supported", evidence: "Built a Python API.",
  section: "projects", explanation: "Related wording; verify the claim.", evidence_start: 14,
  evidence_end: 33, requirement_start: 0, requirement_end: 21, retrieval_score: 55,
  matched_terms: ["python"],
};
const data: EvidenceData = { analysis_id: "a", filename: "resume.txt", matches: [match,
  { ...match, requirement: "Write SQL", status: "not_found", evidence: null },
  { ...match, requirement: "Test JavaScript", status: "partial", evidence: "JavaScript testing" },
] };
const cleanups: (() => void)[] = [];
function setup(payload = data) {
  const root = document.createElement("section");
  document.body.append(root);
  cleanups.push(mountEvidence(root, payload));
  return root;
}
function search(root: HTMLElement, query: string) {
  const input = root.querySelector("input")!;
  input.value = query;
  input.dispatchEvent(new Event("input"));
}
afterEach(() => { cleanups.splice(0).forEach(clean => clean()); document.body.replaceChildren(); });

describe("local evidence workspace", () => {
  it("selects exact evidence and source offsets without a server interface", () => {
    const root = setup();
    expect(root.querySelector("blockquote")?.textContent).toBe(match.evidence);
    expect(root.querySelector("details")?.textContent).toContain("14–33");
    root.querySelectorAll<HTMLButtonElement>(".requirement")[2].click();
    expect(root.querySelector("blockquote")?.textContent).toBe("JavaScript testing");
    expect(root.querySelectorAll('[aria-pressed="true"]')).toHaveLength(1);
  });
  it("searches requirements and excerpts, filters status and recovers from empty results", () => {
    const root = setup();
    search(root, "python api");
    expect(root.querySelectorAll(".requirement")).toHaveLength(1);
    const filter = root.querySelector("select")!;
    filter.value = "Needs attention";
    filter.dispatchEvent(new Event("change"));
    expect(root.querySelectorAll(".requirement")).toHaveLength(0);
    expect(root.querySelector("article")?.textContent).toContain("No requirements match");
    root.querySelector<HTMLButtonElement>(".clear")!.click();
    expect(root.querySelectorAll(".requirement")).toHaveLength(3);
    filter.value = "Needs attention";
    filter.dispatchEvent(new Event("change"));
    expect(root.querySelectorAll(".requirement")).toHaveLength(1);
    expect(root.querySelector("article")?.textContent).toContain("does not establish a missing ability");
  });
  it("renders hostile resume, filename, and requirement content as text", () => {
    const attack = '<img src=x onerror="alert(1)"><script>attack()</script>';
    const root = setup({ ...data, filename: attack, matches: [{ ...match, requirement: attack, evidence: attack }] });
    expect(root.querySelectorAll("img, script")).toHaveLength(0);
    expect(root.querySelector("blockquote")?.textContent).toBe(attack);
    expect(root.querySelector(".source")?.textContent).toContain(attack);
  });
  it("isolates instances and removes listeners when unmounted", () => {
    const first = setup();
    const second = setup();
    search(first, "absent");
    expect(second.querySelectorAll(".requirement")).toHaveLength(3);
    const oldInput = first.querySelector("input")!;
    cleanups[0]();
    oldInput.dispatchEvent(new Event("input"));
    expect(first.childNodes).toHaveLength(0);
    expect(second.querySelectorAll(".requirement")).toHaveLength(3);
  });
  it("handles no requirements and a fresh candidate payload", () => {
    const root = setup({ ...data, matches: [] });
    expect(root.querySelector('[role="status"]')?.textContent).toBe("0 of 0 requirements");
    cleanups[0]();
    cleanups.push(mountEvidence(root, { ...data, analysis_id: "b", filename: "other.txt", matches: [match] }));
    expect(root.querySelector(".source")?.textContent).toContain("other.txt");
    expect(root.querySelectorAll(".requirement")).toHaveLength(1);
  });
});
