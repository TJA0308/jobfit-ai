"""Verify runtime asset discovery and, optionally, deployment wheel contents."""
from __future__ import annotations

import argparse
from pathlib import Path
import tomllib
from zipfile import ZipFile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path)
    args = parser.parse_args()
    package = Path(__file__).resolve().parents[1] / "components/jobfit-evidence/jobfit_evidence"
    manifest = package / "pyproject.toml"
    metadata = tomllib.loads(manifest.read_text(encoding="utf-8"))
    component = metadata["tool"]["streamlit"]["component"]["components"][0]
    asset_dir = package / component["asset_dir"]
    assets = [manifest]
    for pattern in ("index-*.js", "index.css"):
        matches = list(asset_dir.glob(pattern))
        if len(matches) != 1:
            raise SystemExit(f"Expected exactly one {pattern} in {asset_dir}, found {len(matches)}")
        assets.extend(matches)
    if args.wheel:
        with ZipFile(args.wheel) as wheel:
            for asset in assets:
                member = f"jobfit_evidence/{asset.relative_to(package).as_posix()}"
                if wheel.read(member) != asset.read_bytes():
                    raise SystemExit(f"Wheel asset differs from local build: {member}")
    print("Component manifest and unique JS/CSS assets verified" + ("; wheel contents match" if args.wheel else ""))


if __name__ == "__main__":
    main()
