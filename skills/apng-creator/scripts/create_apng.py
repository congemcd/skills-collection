#!/usr/bin/env python3
"""Create an APNG from a numerically indexed PNG sequence."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PREFIX_RE = re.compile(r"^(\d+)(?:\D|$)")
SUFFIX_RE = re.compile(r"(?:^|\D)(\d+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate PNG frame names and assemble them into an APNG.",
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="One input directory or an explicit list of frame files.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=60,
        help="Frames per second. Defaults to 60.",
    )
    parser.add_argument(
        "--output",
        help="Output APNG path. Defaults to <input-folder-name>.png beside the input folder.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an explicit output path.",
    )
    parser.add_argument(
        "--ignore-unindexed",
        action="store_true",
        help="Ignore PNG files that do not have a numeric prefix or suffix index.",
    )
    parser.add_argument(
        "--ignore-non-png",
        action="store_true",
        help="Ignore input files that are not .png files.",
    )
    parser.add_argument(
        "--allow-gaps",
        action="store_true",
        help="Continue when indexed PNG files are not consecutive.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print the apngasm command without running it.",
    )
    return parser.parse_args()


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def prompt_yes_no(question: str) -> bool:
    while True:
        try:
            answer = input(f"{question} [y/N] ").strip().lower()
        except EOFError:
            print()
            return False
        if answer in {"y", "yes"}:
            return True
        if answer in {"", "n", "no"}:
            return False
        print("Please answer y or n.")


def collect_input_files(raw_inputs: list[str]) -> tuple[list[Path], Path]:
    paths = [Path(item).expanduser().resolve() for item in raw_inputs]
    if len(paths) == 1 and paths[0].is_dir():
        input_dir = paths[0]
        return sorted([p for p in input_dir.iterdir() if p.is_file()]), input_dir

    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            fail(f"Explicit file mode does not accept directories: {path}")
        if not path.exists():
            fail(f"Input file does not exist: {path}")
        if not path.is_file():
            fail(f"Input path is not a file: {path}")
        files.append(path)

    if not files:
        fail("No input files were provided.")

    parents = {path.parent for path in files}
    input_dir = files[0].parent if len(parents) == 1 else Path.cwd().resolve()
    return sorted(files), input_dir


def detect_index(path: Path) -> int | None:
    stem = path.stem
    suffix = SUFFIX_RE.search(stem)
    if suffix:
        return int(suffix.group(1))
    prefix = PREFIX_RE.search(stem)
    if prefix:
        return int(prefix.group(1))
    return None


def validate_frames(
    files: list[Path],
    ignore_non_png: bool,
    ignore_unindexed: bool,
    allow_gaps: bool,
) -> list[tuple[int, Path]]:
    non_png = [path for path in files if path.suffix.lower() != ".png"]
    if non_png and not ignore_non_png:
        sample = ", ".join(path.name for path in non_png[:5])
        if not prompt_yes_no(f"Found non-PNG files ({sample}). Ignore them and continue?"):
            fail("Stopped because non-PNG files were present.")

    png_files = [path for path in files if path.suffix.lower() == ".png"]
    indexed: list[tuple[int, Path]] = []
    unindexed: list[Path] = []
    for path in png_files:
        index = detect_index(path)
        if index is None:
            unindexed.append(path)
        else:
            indexed.append((index, path))

    if unindexed and not ignore_unindexed:
        sample = ", ".join(path.name for path in unindexed[:5])
        if not prompt_yes_no(f"Found PNG files without numeric indexes ({sample}). Ignore them and continue?"):
            fail("Stopped because unindexed PNG files were present.")

    if not indexed:
        fail("No usable .png file has a numeric prefix or suffix index.")

    by_index: dict[int, list[Path]] = {}
    for index, path in indexed:
        by_index.setdefault(index, []).append(path)
    duplicates = {index: paths for index, paths in by_index.items() if len(paths) > 1}
    if duplicates:
        details = "; ".join(
            f"{index}: {', '.join(path.name for path in paths)}"
            for index, paths in sorted(duplicates.items())
        )
        fail(f"Duplicate frame indexes found. Rename files before continuing. {details}")

    indexed.sort(key=lambda item: (item[0], item[1].name))
    indexes = [index for index, _path in indexed]
    expected = list(range(indexes[0], indexes[-1] + 1))
    if indexes != expected and not allow_gaps:
        missing = sorted(set(expected) - set(indexes))
        preview = ", ".join(str(index) for index in missing[:10])
        if len(missing) > 10:
            preview += ", ..."
        if not prompt_yes_no(f"Frame indexes are not consecutive; missing {preview}. Continue anyway?"):
            fail("Stopped because frame indexes are not consecutive.")

    return indexed


def default_output_path(input_dir: Path) -> Path:
    base = input_dir.parent / f"{input_dir.name}.png"
    if not base.exists():
        return base
    counter = 1
    while True:
        candidate = input_dir.parent / f"{input_dir.name}-{counter}.png"
        if not candidate.exists():
            return candidate
        counter += 1


def choose_output_path(raw_output: str | None, input_dir: Path, overwrite: bool) -> Path:
    if raw_output:
        output = Path(raw_output).expanduser().resolve()
        if output.exists() and not overwrite:
            fail(f"Explicit output already exists: {output}. Provide a different --output or use --overwrite.")
        return output
    return default_output_path(input_dir)


def prepare_sequence(frames: list[tuple[int, Path]], sequence_dir: Path) -> Path:
    width = max(6, len(str(len(frames))))
    first_frame: Path | None = None
    for position, (_index, source) in enumerate(frames, start=1):
        target = sequence_dir / f"frame{position:0{width}d}.png"
        if first_frame is None:
            first_frame = target
        try:
            os.symlink(source, target)
        except OSError:
            shutil.copy2(source, target)
    if first_frame is None:
        fail("No frames were available after validation.")
    return first_frame


def main() -> None:
    args = parse_args()
    if args.fps <= 0:
        fail("--fps must be a positive integer.")

    files, input_dir = collect_input_files(args.inputs)
    frames = validate_frames(
        files,
        ignore_non_png=args.ignore_non_png,
        ignore_unindexed=args.ignore_unindexed,
        allow_gaps=args.allow_gaps,
    )
    output = choose_output_path(args.output, input_dir, args.overwrite)
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="apng-creator-") as temp_root:
        first_frame = prepare_sequence(frames, Path(temp_root))
        command = ["apngasm", str(output), str(first_frame), "1", str(args.fps)]
        print(f"Frames: {len(frames)}")
        print(f"FPS: {args.fps}")
        print(f"Output: {output}")
        print("Command:", " ".join(command))
        if args.dry_run:
            return
        if shutil.which("apngasm") is None:
            fail("apngasm is not installed. Install it with: brew install apngasm")
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
