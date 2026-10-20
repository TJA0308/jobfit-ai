# JobFit evidence workspace

Private local package for JobFit AI, generated from [Streamlit's official Components v2 template](https://github.com/streamlit/component-template/tree/master/cookiecutter/v2), using **Pure Typescript**. The template's manifest, relative Vite base, library output, and package-data wiring are retained. Generated template code is under the included Apache-2.0 license; this does not assign a license to the parent repository.

Template source revision: `465144fa6764ac1227f299e222ef492262ed70c9`.

## Develop

Use Python 3.13 and Node 24. From `jobfit_evidence/frontend`:

```sh
npm ci
npm test
npm run build
```

From the **repository root**, with its virtual environment active:

```sh
python -m pip install -e ./components/jobfit-evidence
python -m streamlit run components/jobfit-evidence/example.py
```

Root requirements install this package automatically. The compiled frontend is committed in `jobfit_evidence/frontend/build`; deployments need no Node installation. Rebuild and commit assets whenever frontend sources change. CI checks the build against committed assets. `npm run dev` watches sources during development.

`python scripts/verify_component.py` (from the repository root) checks the manifest and unique asset matches. Add `--wheel <path>` to verify that a built wheel contains identical manifest/JS/CSS files.

## Contract

`evidence_browser(payload, key=...)` accepts an analysis ID, filename, and typed evidence matches. The frontend displays exact text using safe DOM methods. Search, category filtering, and selection remain local; there are no state/trigger callbacks, storage, or network requests. Local selection resets on unmount. Multiple instances remain independent and cleanup removes their handlers.

The in-package manifest declares `asset_dir = "frontend/build"`. The registration name is `jobfit-evidence.jobfit_evidence`, with exactly one `index-*.js` and one `index.css`. Shadow styles use Streamlit theme variables. Keep the runtime on Streamlit 1.66 or later within major version 1.

DOM tests cover behavior, not browser layout or host lifecycle. See the parent [UI verification notes](../../docs/UI.md).
