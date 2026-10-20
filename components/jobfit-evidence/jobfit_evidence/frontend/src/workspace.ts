export type Status = "supported" | "partial" | "not_found" | "review";
export interface Match {
  requirement: string;
  status: Status;
  evidence: string | null;
  section: string | null;
  explanation: string;
  evidence_start: number | null;
  evidence_end: number | null;
  requirement_start: number;
  requirement_end: number;
  retrieval_score: number;
  matched_terms: string[];
}
export interface EvidenceData {
  analysis_id: string;
  filename: string;
  matches: Match[];
}
const labels: Record<Status, string> = {
  supported: "Experience wording found", partial: "Partial wording / mention",
  not_found: "No evidence found", review: "Review required",
};
const filters: Record<string, Status[]> = {
  "All requirements": ["supported", "partial", "not_found", "review"],
  "Needs attention": ["not_found", "review"],
  "Experience wording": ["supported"], "Partial mentions": ["partial"],
};

function element<K extends keyof HTMLElementTagNameMap>(tag: K, text = "", className = "") {
  const node = document.createElement(tag);
  node.textContent = text;
  node.className = className;
  return node;
}

/** No storage or network. Navigation stays inside this component instance. */
export function mountEvidence(root: HTMLElement, data: EvidenceData): () => void {
  root.replaceChildren();
  const abort = new AbortController();
  const { signal } = abort;
  const controls = element("div", "", "controls");
  const searchLabel = element("label", "Search requirements and excerpts");
  const search = element("input");
  search.type = "search";
  search.placeholder = "Try Python, testing, or a project…";
  searchLabel.append(search);
  const filterLabel = element("label", "Show requirements");
  const filter = element("select");
  Object.keys(filters).forEach(value => {
    const option = element("option", value);
    option.value = value;
    filter.append(option);
  });
  filterLabel.append(filter);
  const clear = element("button", "Clear filters", "clear");
  clear.type = "button";
  controls.append(searchLabel, filterLabel, clear);
  const count = element("p", "", "count");
  count.setAttribute("role", "status");
  const workspace = element("div", "", "workspace");
  const list = element("nav", "", "requirements");
  list.setAttribute("aria-label", "Requirements");
  const detail = element("article", "", "detail");
  detail.setAttribute("aria-label", "Selected requirement evidence");
  workspace.append(list, detail);
  root.append(controls, count, workspace);
  let selected = 0;

  function showDetail(index: number) {
    const match = data.matches[index];
    detail.replaceChildren();
    if (!match) return;
    detail.append(element("span", labels[match.status], `badge ${match.status}`));
    detail.append(element("h3", "Job requirement"), element("p", match.requirement, "quote"));
    detail.append(element("h3", "Resume evidence"));
    if (match.evidence !== null) {
      detail.append(element("blockquote", match.evidence));
      detail.append(element("p", `${match.section ?? "Unsectioned"} · ${data.filename}`, "source"));
    } else {
      detail.append(element("p", "No sufficiently related passage found. This does not establish a missing ability."));
    }
    detail.append(element("p", match.explanation, "explanation"));
    const source = element("details");
    source.append(element("summary", "Source details"));
    source.append(element("p", `Job description characters ${match.requirement_start}–${match.requirement_end}.`));
    if (match.evidence !== null) {
      source.append(element("p", `Extracted resume characters ${match.evidence_start}–${match.evidence_end}. Offsets refer to extracted text, not PDF page coordinates.`));
      source.append(element("p", `Retrieval cosine: ${match.retrieval_score}/100. This is not qualification confidence.`));
      source.append(element("p", `Shared terms: ${match.matched_terms.join(", ") || "None"}`));
    }
    detail.append(source);
    list.querySelectorAll<HTMLButtonElement>("button").forEach(button => {
      button.setAttribute("aria-pressed", String(Number(button.dataset.index) === index));
    });
  }

  function refresh() {
    const query = search.value.trim().toLocaleLowerCase();
    const visible = data.matches.map((match, index) => ({ match, index })).filter(({ match }) =>
      filters[filter.value].includes(match.status) &&
      `${match.requirement}\n${match.evidence ?? ""}`.toLocaleLowerCase().includes(query));
    list.replaceChildren();
    count.textContent = `${visible.length} of ${data.matches.length} requirements`;
    if (!visible.length) {
      detail.replaceChildren(element("p", "No requirements match these filters. Clear filters to continue."));
      return;
    }
    if (!visible.some(item => item.index === selected)) selected = visible[0].index;
    visible.forEach(({ match, index }) => {
      const button = element("button", "", "requirement");
      button.type = "button";
      button.dataset.index = String(index);
      button.append(element("span", `${String(index + 1).padStart(2, "0")} · ${labels[match.status]}`, `eyebrow ${match.status}`));
      button.append(element("span", match.requirement));
      list.append(button);
    });
    showDetail(selected);
  }

  // Delegation keeps listener count constant as the list changes.
  list.addEventListener("click", event => {
    const button = (event.target as HTMLElement).closest<HTMLButtonElement>("button[data-index]");
    if (!button || !list.contains(button)) return;
    selected = Number(button.dataset.index);
    showDetail(selected);
  }, { signal });
  search.addEventListener("input", refresh, { signal });
  filter.addEventListener("change", refresh, { signal });
  clear.addEventListener("click", () => {
    search.value = "";
    filter.value = "All requirements";
    refresh();
    search.focus();
  }, { signal });
  refresh();
  return () => { abort.abort(); root.replaceChildren(); };
}
