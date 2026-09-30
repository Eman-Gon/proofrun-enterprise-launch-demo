#!/usr/bin/env python3
"""Write prospective operator configuration for a real ProofRun investigation."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
REFS = ("v1.0.0", "v1.1.0-rc1", "v1.1.0-fixed")
IMAGE = re.compile(r"(?:sha256:|[A-Za-z0-9][A-Za-z0-9._/:@-]*@sha256:)[a-f0-9]{64}\Z")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True,
                        help="Locally available, immutable Python execution image (sha256 digest).")
    parser.add_argument("--workspace", default="operator", help="Authorized ProofRun workspace identifier.")
    parser.add_argument("--output", type=Path, default=ROOT / ".demo-results" / "proofrun-config")
    args = parser.parse_args()
    if not IMAGE.fullmatch(args.image):
        parser.error("--image must be an immutable sha256 image ID or repository@sha256 digest.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}", args.workspace):
        parser.error("--workspace must be a safe, exact workspace identifier.")
    env = {"PATH": os.defpath, "LANG": "C", "GIT_CONFIG_NOSYSTEM": "1"}
    revisions = {}
    for ref in REFS:
        try:
            result = subprocess.run(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
                                    cwd=ROOT, env=env, capture_output=True, text=True,
                                    check=True, timeout=10)
        except (subprocess.SubprocessError, OSError) as exc:
            print(f"Could not resolve local release tag {ref}: {exc}", file=sys.stderr)
            return 1
        sha = result.stdout.strip()
        if not re.fullmatch(r"[a-f0-9]{40}", sha):
            print(f"Expected a 40-character commit SHA for {ref}.", file=sys.stderr)
            return 1
        revisions[ref] = sha
    if len(set(revisions.values())) != len(REFS):
        print("The three release tags must resolve to different commits.", file=sys.stderr)
        return 1
    target = {
        "id": "northstar-enterprise-launch",
        "name": "Northstar — enterprise onboarding release",
        "repository": str(ROOT),
        "workspaces": [args.workspace],
        "images": {sha: args.image for sha in revisions.values()},
        "requirements": [{
            "id": "customer-import-compatibility",
            "description": "Preserve the HTTP status and response body for supported synthetic customer import requests.",
            "kind": "preserve_response",
            "path_prefix": "/customers/import",
            "methods": ["POST"],
        }],
        "runtime": {
            "collector_image": args.image,
            "command": ["python", "-m", "northstar", "--host", "0.0.0.0", "--port", "8080"],
            "test_command": ["python", "-m", "unittest", "discover", "-s", "tests", "-v"],
            "workdir": ".",
            "port": 8080,
            "health_path": "/health",
            "startup_seconds": 30,
            "env": {"APP_ENV": "proofrun"},
        },
        "test_paths": ["tests/*.py"],
        "test_success_pattern": r"(?m)^Ran [1-9][0-9]* tests? in [0-9.]+s$",
        "repair_paths": ["northstar/customers.py"],
        "exclude_paths": ["README.md", "docs/DEMO.md", "docs/RESULTS.md", "docs/*verification.json", "scripts/*", "checks/*", ".github/*"],
    }
    request = {
        "target_id": target["id"],
        "baseline_revision": revisions[REFS[0]],
        "candidate_revision": revisions[REFS[1]],
        "benefit": "Enable enterprise teams to preview a CSV customer import and identify invalid or duplicate rows before onboarding.",
        "budget_seconds": 300,
        "repair": True,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    for filename, data in (("targets.json", {"targets": [target]}), ("request.json", request)):
        path = args.output / filename
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(path.resolve())
    print("Prospective configuration only: no image build, AI call, or ProofRun investigation was executed.")
    print("The operator must make this repository and immutable Python image available to ProofRun's runtime.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
