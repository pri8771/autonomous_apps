#!/usr/bin/env python3
"""One-time checksum-verified BotChorus source bootstrap. Contains no secrets."""
# This committed touch occurs only after the workflow exists on the default branch.
from __future__ import annotations
import base64, hashlib, io, os, shutil, subprocess, tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "projects/.botchorus-bundle"
ARCHIVE_SHA256 = "c3c73676dc465351ef4ec374b42bbe209bcbedfc45f50b22ff3ed96709d1c66f"


def run(*args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def main() -> None:
    encoded = "".join(path.read_text(encoding="ascii").strip() for path in sorted(PARTS.glob("part-*.b64")))
    payload = base64.b64decode(encoded, validate=True)
    actual = hashlib.sha256(payload).hexdigest()
    if actual != ARCHIVE_SHA256:
        raise SystemExit(f"BotChorus bootstrap checksum mismatch: {actual}")
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        for member in archive.getmembers():
            target = (ROOT / member.name).resolve()
            if ROOT.resolve() not in target.parents or not member.isfile():
                raise SystemExit(f"Unsafe archive member: {member.name}")
        archive.extractall(ROOT, filter="data")
    env = os.environ.copy()
    env["BOTCHORUS_RUN_KIND"] = "bootstrap_cloud"
    env["BOTCHORUS_NOW"] = env.get("BOTCHORUS_NOW", "2026-08-24T18:00:00Z")
    run("python3", "projects/botchorus/operator.py", "--no-network", env=env)
    run("python3", "projects/botchorus/operator.py", "--check", env=env)
    run("python3", "-m", "unittest", "discover", "-s", "projects/botchorus/tests", "-p", "test_*.py", env=env)
    shutil.rmtree(PARTS)
    Path(__file__).unlink()
    workflow = ROOT / ".github/workflows/botchorus-bootstrap.yml"
    if workflow.exists():
        workflow.unlink()


if __name__ == "__main__":
    main()
