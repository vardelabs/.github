#!/usr/bin/env python3
"""Fail when a secret-named variable sits under a public env prefix.

Bundlers inline every variable under these prefixes into the client bundle, so
a name like VITE_STRIPE_SECRET_KEY ships its value to every visitor. Checks the
tracked files under a source directory and the job's environment. Prints names
and file paths only, never a value.
"""

import argparse
import os
import re
import subprocess
import sys

PUBLIC_NAME = re.compile(r"\b(?:VITE|NEXT_PUBLIC|PUBLIC|REACT_APP|EXPO_PUBLIC)_[A-Za-z0-9_]+\b")
SECRET_WORDS = {"SECRET", "TOKEN", "PASSWORD", "PASSWD", "PRIVATE"}
# Docs often name the very var they warn against; only code and config ship.
PROSE_SUFFIXES = (".md", ".mdx", ".rst", ".txt")


def is_secret_name(name: str) -> bool:
    segments = name.upper().split("_")
    return bool(SECRET_WORDS.intersection(segments)) or segments[-2:] == ["API", "KEY"]


def tracked_files(source: str) -> list[str]:
    listing = subprocess.run(
        ["git", "-C", source, "ls-files", "-z"],
        capture_output=True,
        check=True,
    )
    names = listing.stdout.decode().split("\0")
    return [os.path.join(source, name) for name in names if name and not name.lower().endswith(PROSE_SUFFIXES)]


def names_in_file(path: str) -> set[str]:
    try:
        with open(path, encoding="utf-8", errors="ignore") as handle:
            return set(filter(is_secret_name, PUBLIC_NAME.findall(handle.read())))
    except OSError:
        return set()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=".")
    parser.add_argument("--allow", default="", help="comma- or newline-separated publishable names")
    args = parser.parse_args()
    allowed = {name.strip() for name in re.split(r"[,\n]", args.allow) if name.strip()}

    findings = []
    for path in tracked_files(args.source):
        for name in sorted(names_in_file(path) - allowed):
            findings.append(f"{path}: {name}")
    env_names = {name for name in os.environ if PUBLIC_NAME.fullmatch(name) and is_secret_name(name)}
    for name in sorted(env_names - allowed):
        findings.append(f"job environment: {name}")

    for line in findings:
        print(f"::error::secret-named public env var {line}")
    if findings:
        print("A public prefix ships its value in the client bundle. Read the secret server-side instead,"
              " or add a publishable name to allow-names.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
