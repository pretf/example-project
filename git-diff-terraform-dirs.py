#!/usr/bin/env python

import argparse
import subprocess
from collections import defaultdict
from os.path import relpath
from pathlib import Path
from typing import Dict, Generator, List


def get_dirs(name_patterns: List[str]) -> Generator[Path, None, None]:
    cwd = Path()

    dirs: Dict[Path, List[str]] = defaultdict(list)
    for pattern in name_patterns:
        for path in cwd.rglob(pattern):
            for part in path.parts:
                if part.startswith("."):
                    break
            else:
                dirs[path.parent].append(pattern)
    for path, patterns in dirs.items():
        if len(patterns) == len(name_patterns):
            yield Path(relpath(path))


def get_changed_files(source_ref: str, target_ref: str) -> Generator[Path, None, None]:
    output = subprocess.check_output(
        ["git", "diff", "--name-only", source_ref, target_ref]
    )
    for name in output.decode().splitlines():
        yield Path(name)


def get_affected_dirs(
    *name_patterns: str, source_ref: str, target_ref: str
) -> Generator[Path, None, None]:

    changed_file_dirs = set()
    for changed_file in get_changed_files(source_ref, target_ref):
        changed_file_dirs.add(changed_file.parent)

    for candidate_dir in sorted(get_dirs(name_patterns)):
        for changed_dir in changed_file_dirs:
            try:
                candidate_dir.relative_to(changed_dir)
            except ValueError:
                pass
            else:
                yield candidate_dir
                break


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Finds directories that could potentially be affected by Git changes. This "
            "assumes a perfectly hierarchical project structure where a file change in one "
            "directory has the potential to affect that directory and all directories below "
            "it. CI/CD systems can use this to determine where to run 'terraform plan' and "
            "'terraform apply'. Run this from the root directory of a Git repository."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "names",
        metavar="name",
        type=str,
        nargs="*",
        default=["terraform.tfvars"],
        help=(
            "File name pattern(s) to indicate where Terraform can "
            "run. If multiple names are provided then directories "
            "must contain all of them."
        ),
    )
    parser.add_argument(
        "-s",
        "--source-ref",
        dest="source_ref",
        action="store",
        default="HEAD",
        help="Git ref to look at for changes.",
    )
    parser.add_argument(
        "-t",
        "--target-ref",
        dest="target_ref",
        action="store",
        default="origin/master",
        help="Git ref to compare against.",
    )

    args = parser.parse_args()

    for path in get_affected_dirs(
        *args.names, source_ref=args.source_ref, target_ref=args.target_ref
    ):
        print(path)
