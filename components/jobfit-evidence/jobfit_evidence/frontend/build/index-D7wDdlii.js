//#region src/workspace.ts
var e = {
	supported: "Experience wording found",
	partial: "Partial wording / mention",
	not_found: "No evidence found",
	review: "Review required"
}, t = {
	"All requirements": [
		"supported",
		"partial",
		"not_found",
		"review"
	],
	"Needs attention": ["not_found", "review"],
	"Experience wording": ["supported"],
	"Partial mentions": ["partial"]
};
function n(e, t = "", n = "") {
	let r = document.createElement(e);
	return r.textContent = t, r.className = n, r;
}
function r(r, i) {
	r.replaceChildren();
	let a = new AbortController(), { signal: o } = a, s = n("div", "", "controls"), c = n("label", "Search requirements and excerpts"), l = n("input");
	l.type = "search", l.placeholder = "Try Python, testing, or a project…", c.append(l);
	let u = n("label", "Show requirements"), d = n("select");
	Object.keys(t).forEach((e) => {
		let t = n("option", e);
		t.value = e, d.append(t);
	}), u.append(d);
	let f = n("button", "Clear filters", "clear");
	f.type = "button", s.append(c, u, f);
	let p = n("p", "", "count");
	p.setAttribute("role", "status");
	let m = n("div", "", "workspace"), h = n("nav", "", "requirements");
	h.setAttribute("aria-label", "Requirements");
	let g = n("article", "", "detail");
	g.setAttribute("aria-label", "Selected requirement evidence"), m.append(h, g), r.append(s, p, m);
	let _ = 0;
	function v(t) {
		let r = i.matches[t];
		if (g.replaceChildren(), !r) return;
		g.append(n("span", e[r.status], `badge ${r.status}`)), g.append(n("h3", "Job requirement"), n("p", r.requirement, "quote")), g.append(n("h3", "Resume evidence")), r.evidence === null ? g.append(n("p", "No sufficiently related passage found. This does not establish a missing ability.")) : (g.append(n("blockquote", r.evidence)), g.append(n("p", `${r.section ?? "Unsectioned"} · ${i.filename}`, "source"))), g.append(n("p", r.explanation, "explanation"));
		let a = n("details");
		a.append(n("summary", "Source details")), a.append(n("p", `Job description characters ${r.requirement_start}–${r.requirement_end}.`)), r.evidence !== null && (a.append(n("p", `Extracted resume characters ${r.evidence_start}–${r.evidence_end}. Offsets refer to extracted text, not PDF page coordinates.`)), a.append(n("p", `Retrieval cosine: ${r.retrieval_score}/100. This is not qualification confidence.`)), a.append(n("p", `Shared terms: ${r.matched_terms.join(", ") || "None"}`))), g.append(a), h.querySelectorAll("button").forEach((e) => {
			e.setAttribute("aria-pressed", String(Number(e.dataset.index) === t));
		});
	}
	function y() {
		let r = l.value.trim().toLocaleLowerCase(), a = i.matches.map((e, t) => ({
			match: e,
			index: t
		})).filter(({ match: e }) => t[d.value].includes(e.status) && `${e.requirement}\n${e.evidence ?? ""}`.toLocaleLowerCase().includes(r));
		h.replaceChildren(), p.textContent = `${a.length} of ${i.matches.length} requirements`, a.length ? (a.some((e) => e.index === _) || (_ = a[0].index), a.forEach(({ match: t, index: r }) => {
			let i = n("button", "", "requirement");
			i.type = "button", i.dataset.index = String(r), i.append(n("span", `${String(r + 1).padStart(2, "0")} · ${e[t.status]}`, `eyebrow ${t.status}`)), i.append(n("span", t.requirement)), h.append(i);
		}), v(_)) : g.replaceChildren(n("p", "No requirements match these filters. Clear filters to continue."));
	}
	return h.addEventListener("click", (e) => {
		let t = e.target.closest("button[data-index]");
		t && h.contains(t) && (_ = Number(t.dataset.index), v(_));
	}, { signal: o }), l.addEventListener("input", y, { signal: o }), d.addEventListener("change", y, { signal: o }), f.addEventListener("click", () => {
		l.value = "", d.value = "All requirements", y(), l.focus();
	}, { signal: o }), y(), () => {
		a.abort(), r.replaceChildren();
	};
}
//#endregion
//#region src/index.ts
var i = ({ parentElement: e, data: t }) => {
	let n = e.querySelector(".component-root");
	if (!n) throw Error("Evidence root is missing");
	return r(n, t);
};
//#endregion
export { i as default };
