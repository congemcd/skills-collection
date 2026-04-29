---
name: apng-creator
description: Create animated PNG/APNG files from a directory or list of PNG frame images. Use when the user wants to generate an APNG from a PNG sequence with numeric prefix or suffix frame indexes, validate frame ordering, handle missing or non-consecutive indexes, and choose a frame rate.
---

# APNG Creator

Create an animated PNG from an indexed PNG frame sequence. Use the bundled helper script for validation and assembly so filename handling and output naming stay deterministic.

## Workflow

1. **Check dependencies first.** Run `which apngasm`.
   - If `apngasm` is missing, explain that it is needed to assemble individual PNG frames into a valid APNG container without reimplementing APNG encoding by hand.
   - Then directly install it with `brew install apngasm`.
2. **Identify inputs.** Accept either one input directory or an explicit list of frame files.
3. **Validate filenames before generating output.**
   - PNG frame names must contain a numeric prefix or suffix, such as `001-frame.png`, `frame-001.png`, or `frame001.png`.
   - If a name has both prefix and suffix indexes, use the suffix index.
   - If duplicate indexes exist, stop and ask the user to rename files.
4. **Handle validation decisions.**
   - If some files are missing indexes, ask whether to ignore unindexed files or stop.
   - If indexes are not consecutive, ask whether to continue or stop.
   - If the inputs include files that are not `.png`, ask whether to ignore them or stop.
   - If no usable `.png` file has an index, tell the user and stop.
5. **Choose frame rate and output.**
   - Use 60 fps unless the user specifies a target frame rate.
   - If no output path is specified, write `<input-folder-name>.png` beside the input folder.
   - If that default output path already exists, auto-number as `<input-folder-name>-1.png`, `<input-folder-name>-2.png`, and so on.
   - If the user provides an explicit output path that already exists, stop unless the user explicitly requested overwrite behavior.
6. **Generate the APNG.** Run:

```bash
python3 scripts/create_apng.py <input-dir-or-files> --fps 60
```

Use `--output <path>` when the user specifies an output file. Use `--overwrite` only when the user explicitly says to overwrite an existing explicit output path.

## Helper Script

`scripts/create_apng.py` performs filename validation, prompts for required decisions, creates a temporary consecutive frame sequence, and invokes `apngasm <output.png> <first-frame.png> 1 <fps>`.

Useful options:

- `--fps <integer>`: target frame rate; defaults to `60`.
- `--output <path>`: explicit APNG output path.
- `--overwrite`: allow replacing an explicit existing output path.
- `--ignore-unindexed`: ignore PNG files without numeric prefix or suffix indexes.
- `--ignore-non-png`: ignore non-PNG inputs.
- `--allow-gaps`: continue when numeric indexes are not consecutive.
- `--dry-run`: validate inputs and print the command without invoking `apngasm`.
