#!/usr/bin/env python3
"""Replay the release story using real HTTP requests against exact Git revisions.

These are operator-selected deterministic checks, not an AI investigation or a
ProofRun execution. The working checkout is never changed.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import uuid


ROOT = Path(__file__).resolve().parents[1]
REFS = ("v1.0.0", "v1.1.0-rc1", "v1.1.0-fixed")
DISCLAIMER = "Operator-selected deterministic checks; no AI or ProofRun investigation was executed."
ENV = {
    "PATH": os.defpath,
    "LANG": "C",
    "PYTHONNOUSERSITE": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "PYTHONIOENCODING": "utf-8",
    "GIT_CONFIG_NOSYSTEM": "1",
}


def run_git(*argv: str) -> str:
    return subprocess.run(["git", *argv], cwd=ROOT, env=ENV, capture_output=True,
                          text=True, check=True, timeout=20).stdout.strip()


def archive_revision(sha: str, destination: Path) -> None:
    """Materialize a committed tree without checkout, hooks, or inherited secrets."""
    destination.mkdir()
    archive = destination.parent / f"{destination.name}.tar"
    subprocess.run(["git", "archive", "--format=tar", f"--output={archive}", sha],
                   cwd=ROOT, env=ENV, capture_output=True, check=True, timeout=20)
    with tarfile.open(archive) as contents:
        for member in contents.getmembers():
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts or ".git" in relative.parts:
                raise RuntimeError(f"Unsafe archive entry: {member.name}")
            path = destination.joinpath(*relative.parts)
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                path.parent.mkdir(parents=True, exist_ok=True)
                source = contents.extractfile(member)
                if source is None:
                    raise RuntimeError(f"Missing archived file: {member.name}")
                with source, path.open("wb") as output:
                    shutil.copyfileobj(source, output)
            else:
                raise RuntimeError(f"Unsupported archive entry: {member.name}")
    archive.unlink()


def hashes(directory: Path) -> dict[str, str]:
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((directory / "tests").rglob("*.py"))}


def run_suite(project: Path, suite: Path, log: Path) -> dict:
    command = [sys.executable, "-m", "unittest", "discover", "-s", str(suite), "-v"]
    with log.open("w", encoding="utf-8") as output:
        result = subprocess.run(command, cwd=project, env=ENV, stdout=output,
                                stderr=subprocess.STDOUT, timeout=30)
    log_text = log.read_text(encoding="utf-8")
    completed = re.search(r"(?m)^Ran ([1-9][0-9]*) tests? in [0-9.]+s$", log_text)
    return {"command": command, "exit_code": result.returncode,
            "tests_run": int(completed.group(1)) if completed else 0,
            "passed": result.returncode == 0 and bool(completed), "log": str(log)}


def request(port: int, path: str, payload: dict | None = None) -> dict:
    # HTTPConnection connects directly to loopback and never consults proxy env.
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        body = json.dumps(payload).encode() if payload is not None else None
        connection.request("POST" if payload is not None else "GET", path, body=body,
                           headers={"Content-Type": "application/json"} if body else {})
        response = connection.getresponse()
        raw = response.read(1024 * 1024)
        try:
            parsed = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = {"unparsed_body": raw.decode("utf-8", errors="replace")}
        return {"status": response.status, "body": parsed}
    finally:
        connection.close()


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


@contextmanager
def serve(project: Path, log: Path):
    """Use a fresh ephemeral loopback port; retry a possible bind race."""
    with log.open("w", encoding="utf-8") as output:
        for attempt in range(3):
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            process = subprocess.Popen(
                [sys.executable, "-m", "northstar", "--host", "127.0.0.1", "--port", str(port)],
                cwd=project, env=ENV, stdout=output, stderr=subprocess.STDOUT,
            )
            ready = False
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and process.poll() is None:
                    try:
                        ready = request(port, "/health")["status"] == 200
                    except (OSError, http.client.HTTPException):
                        ready = False
                    if ready:
                        # Confirm this child stayed alive after the successful probe.
                        time.sleep(0.05)
                        ready = process.poll() is None
                        break
                    time.sleep(0.1)
                if ready:
                    yield port
                    return
            finally:
                stop(process)
        raise RuntimeError(f"Application did not become healthy after three attempts. See {log}")


def run_probes(project: Path, ref: str, log: Path) -> list[dict]:
    checks = []
    with serve(project, log) as port:
        for customer_id, label in (("12345", "numeric control"), ("00123", "leading-zero identifier"),
                                   ("abc-123", "partner identifier")):
            payload = {"customer_id": customer_id, "name": "Avery Chen"}
            results = [request(port, "/customers/import", payload) for _ in range(2)]
            expected_status = 422 if ref == REFS[1] and customer_id == "abc-123" else 201
            expected_id = "123" if ref == REFS[1] and customer_id == "00123" else customer_id
            passed = all(result["status"] == expected_status for result in results)
            if expected_status == 201:
                expected_body = {"customer": {"customer_id": expected_id, "name": "Avery Chen"}, "imported": True}
                passed = passed and all(result["body"] == expected_body for result in results)
            passed = passed and results[0] == results[1]
            checks.append({"label": label, "path": "/customers/import", "method": "POST",
                           "input": payload, "repetitions": results,
                           "expected_status": expected_status,
                           "expected_customer_id": expected_id if expected_status == 201 else None,
                           "legacy_contract_preserved": all(result == {
                               "status": 201,
                               "body": {"customer": {"customer_id": customer_id, "name": "Avery Chen"}, "imported": True},
                           } for result in results),
                           "matches_story": passed})
        payload = {"csv": "customer_id,name\n12345,Avery Chen\n67890,Jordan Lee\n"}
        results = [request(port, "/imports/preview", payload) for _ in range(2)]
        expected_status = 404 if ref == REFS[0] else 200
        passed = all(result["status"] == expected_status for result in results)
        if expected_status == 200:
            for result in results:
                body = result["body"]
                passed = passed and isinstance(body, dict) and all(
                    body.get(key) == value for key, value in {"total": 2, "ready": 2, "rejected": 0}.items())
                rows = body.get("rows", []) if isinstance(body, dict) else []
                passed = passed and isinstance(rows, list) and len(rows) == 2 and all(isinstance(row, dict) for row in rows) and [row.get("customer") for row in rows] == [
                    {"customer_id": "12345", "name": "Avery Chen"},
                    {"customer_id": "67890", "name": "Jordan Lee"},
                ]
        checks.append({"label": "bulk preview feature", "path": "/imports/preview", "method": "POST",
                       "input": payload, "repetitions": results, "expected_status": expected_status,
                       "matches_story": passed and results[0] == results[1]})
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".demo-results",
                        help="Parent directory for a fresh timestamped receipt and logs.")
    args = parser.parse_args()
    timestamp = datetime.now(timezone.utc)
    run_dir = args.output.resolve() / f"run-{timestamp:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True)
    receipt = {"schema": "northstar.demo-replay.v1", "started_at": timestamp.isoformat(),
               "disclaimer": DISCLAIMER, "repository": str(ROOT), "python": sys.version,
               "revisions": [], "passed": False}
    print(DISCLAIMER)
    print("Replaying committed releases; expected candidate failures are part of this demo.")
    try:
        resolved = {ref: run_git("rev-parse", "--verify", f"{ref}^{{commit}}") for ref in REFS}
        if any(not re.fullmatch(r"[a-f0-9]{40}", sha) for sha in resolved.values()):
            raise RuntimeError("Release tags must resolve to exact 40-character commit SHAs.")
        if len(set(resolved.values())) != 3:
            raise RuntimeError("The three release tags must resolve to distinct commits.")
        for ref, sha in resolved.items():
            project = run_dir / ref
            archive_revision(sha, project)
        baseline_hashes = hashes(run_dir / REFS[0])
        if not baseline_hashes:
            raise RuntimeError("The baseline release contains no tests to freeze.")
        frozen_tests = run_dir / "frozen-baseline-tests"
        shutil.copytree(run_dir / REFS[0] / "tests", frozen_tests)
        receipt["frozen_baseline_test_hashes"] = baseline_hashes
        for ref, sha in resolved.items():
            project = run_dir / ref
            current_hashes = hashes(project)
            unchanged = all(current_hashes.get(path) == digest for path, digest in baseline_hashes.items())
            item = {"ref": ref, "sha": sha, "test_sha256": current_hashes,
                    "baseline_test_files_unchanged": unchanged}
            receipt["revisions"].append(item)
            item["current_suite"] = run_suite(project, project / "tests", run_dir / f"{ref}-tests.log")
            item["frozen_baseline_suite"] = run_suite(project, frozen_tests, run_dir / f"{ref}-frozen-tests.log")
            item["checks"] = run_probes(project, ref, run_dir / f"{ref}-server.log")
            item["legacy_contract_preserved_for_selected_checks"] = all(
                check["legacy_contract_preserved"] for check in item["checks"] if "legacy_contract_preserved" in check)
            item["matches_story"] = unchanged and item["current_suite"]["passed"] and item["frozen_baseline_suite"]["passed"] and all(
                check["matches_story"] for check in item["checks"])
            observations = []
            for check in item["checks"]:
                result = check["repetitions"][0]
                customer = result["body"].get("customer", {}) if isinstance(result["body"], dict) else {}
                observations.append(f"{check['label']}: HTTP {result['status']}" +
                                    (f" / ID {customer['customer_id']!r}" if "customer_id" in customer else ""))
            print(f"\n{ref} ({sha[:12]}): {item['current_suite']['tests_run']} tests, "
                  f"{'PASS' if item['current_suite']['passed'] else 'FAIL'}; "
                  f"frozen baseline {'PASS' if item['frozen_baseline_suite']['passed'] else 'FAIL'}")
            print("  " + "; ".join(observations))
            if not item["matches_story"]:
                print("  UNEXPECTED RESULT — inspect receipt and logs.")
        receipt["passed"] = all(item["matches_story"] for item in receipt["revisions"])
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, http.client.HTTPException, tarfile.TarError) as exc:
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        print(f"Replay failed: {receipt['error']}", file=sys.stderr)
    finally:
        receipt["completed_at"] = datetime.now(timezone.utc).isoformat()
        receipt_path = run_dir / "receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(f"\nReceipt: {receipt_path}")
    print("Demo story verified with recorded HTTP evidence." if receipt["passed"] else "Demo story verification FAILED.")
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
