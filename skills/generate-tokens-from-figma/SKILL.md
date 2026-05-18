---
name: generate-tokens-from-figma
description: Generate design token reports and token files from Figma variables and styles. Use when Codex needs to inspect a Figma design file, create a variables/styles extraction report, normalize Figma names, and export DTCG 2025.10 `.tokens.json` files for variables, color styles, text styles, or explicitly requested additional style types.
---

# Generate Tokens From Figma

## Workflow

Always run this as a two-phase workflow:

0. Check dependencies.
1. Create a report.
2. Generate token files from the report.

Use `figma-use` read-only scripts for Figma inspection. Do not mutate the Figma file. If the requested output format is not specified, use the bundled default template at `templates/dtcg-2025-10.tokens.template.json` and the mapping guidance in `references/dtcg-2025-10.md`.

## Dependency Check

Before inspecting Figma or generating tokens, run:

```bash
<skill-dir>/scripts/check_dependencies.sh
```

This preflight checks:

- Figma MCP skills, especially `figma-use`.
- Python availability for the generator script.

If Figma skills are missing, stop and guide the user to install them using Figma's official instructions: [Figma skills for MCP](https://help.figma.com/hc/en-us/articles/39166810751895-Figma-skills-for-MCP). Tell the user that Figma documents the Figma plugin path as the easiest setup when their agentic tool supports it, and manual skill download/install as the manual alternative.

If Python is missing, install it automatically with the available platform package manager. The preflight script tries Homebrew on macOS, then common Linux package managers. If no supported package manager exists or installation needs user approval, continue only after Python is available.

## Report Phase

Create both report files in the user's chosen output directory, defaulting to the current workspace:

- `figma-token-report.md`
- `figma-token-report.json`

The report must include:

- Figma source metadata: URL or file key, node ID when provided, editor type, extraction time.
- Variable collections with modes, variable counts, resolved types, aliases, and raw values.
- Styles found in the file.
- Styles selected for token generation.
- Skipped items with reasons.
- Validation warnings.
- A normalization table for every generated collection, mode, variable, style, and output file.

Normalization rows must include:

```json
{
  "kind": "variable|style|mode|collection|file",
  "source": "Colors|Text Styles|Paint Styles|...",
  "originalName": "Large Title/Regular",
  "normalizedName": "large-title-regular",
  "collision": false,
  "collisionOf": null
}
```

## Token Generation

Use `scripts/generate_figma_tokens.py` to generate token files from `figma-token-report.json`.

Default outputs:

- `tokens/variables/<normalized-collection>.tokens.json`, one file per variable collection.
- `tokens/styles/color.tokens.json`, generated from local paint/color styles.
- `tokens/styles/text.tokens.json`, generated from local text styles.

Only generate other style types, such as effects or grids, when the user explicitly requests those style types.

Figma variable modes must become normalized groups inside each collection file. For example, a `Colors` collection with `Light`, `Dark`, and `IC - Light` modes becomes a `colors.tokens.json` file with `light`, `dark`, and `ic-light` groups.

## Naming Rules

Normalize every generated token, group, mode, file, and style name:

- Translate non-English names to concise English before normalization.
- Lowercase.
- Replace separator runs with one `-`. Separators include whitespace, `/`, `_`, punctuation separators, ` - `, ` / `, and repeated separator characters.
- Remove characters that are not lowercase ASCII letters, digits, or `-`.
- Trim leading and trailing `-`.
- If the result is empty, use `token`.

On collisions after normalization, append `-2`, `-3`, etc. Record the collision in `figma-token-report.md`, `figma-token-report.json`, and the final response.
