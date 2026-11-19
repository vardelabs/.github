#!/usr/bin/env python3
"""Scan every served file for provider secrets and name each file that holds one.

gitleaks' default config skips paths by name (node_modules/, bootstrap*.js,
*.svg and more), and an extended config cannot drop those exemptions. So each
served file is copied to a neutral name first, and findings are mapped back to
the served path. Output is fully redacted and the report stays in a temp dir.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MEDIA_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".avif", ".tif", ".tiff",
    ".woff", ".woff2", ".ttf", ".otf", ".eot", ".mp3", ".mp4", ".webm", ".wav", ".pdf",
}


def served_files(root: Path) -> list[Path]:
    # A host serves through a symlinked directory, so the walk follows them;
    # the real-path set stops a link loop from walking forever.
    files, visited = [], set()
    for directory, subdirs, names in os.walk(root, followlinks=True):
        real = os.path.realpath(directory)
        if real in visited:
            subdirs.clear()
            continue
        visited.add(real)
        subdirs[:] = [name for name in subdirs if name != ".git"]
        for name in names:
            path = Path(directory, name)
            if path.is_file() and path.suffix.lower() not in MEDIA_SUFFIXES:
                files.append(path)
    return sorted(files)


def stage(files: list[Path], stage_dir: Path) -> dict[str, Path]:
    staged = {}
    for index, path in enumerate(files):
        name = f"{index}.scan"
        shutil.copyfile(path, stage_dir / name)
        staged[name] = path
    return staged


def run_gitleaks(stage_dir: Path, config: str, report: Path) -> int:
    return subprocess.run(
        ["gitleaks", "dir", str(stage_dir), "--config", config, "--redact=100", "--no-banner",
         "--log-level", "warn", "--report-format", "json", "--report-path", str(report)],
    ).returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    root = Path(args.path)
    if not root.is_dir():
        print(f"::error::no served output at {root}; build before the scan")
        return 1

    with tempfile.TemporaryDirectory(dir=os.environ.get("RUNNER_TEMP")) as work:
        stage_dir = Path(work, "served")
        stage_dir.mkdir()
        staged = stage(served_files(root), stage_dir)
        report = Path(work, "report.json")
        returncode = run_gitleaks(stage_dir, args.config, report)
        if not report.exists():
            print("::error::gitleaks wrote no report, so the scan result is unknown")
            return 1
        findings = json.loads(report.read_text())

    for finding in findings:
        served = staged[Path(finding["File"]).name].relative_to(root)
        print(f"::error::{finding['RuleID']} in served file {served}, line {finding['StartLine']}")
    print(f"scanned {len(staged)} served files, {len(findings)} findings")
    return 1 if findings or returncode != 0 else 0


if __name__ == "__main__":
    sys.exit(main())
