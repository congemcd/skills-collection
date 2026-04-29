# Skills Collection

Portable Agent Skills that use the common `SKILL.md` folder format. Each skill is
stored as source under `skills/`; packaged `.skill` archives are stored separately
under `packaged-skills/`.

## Skills

- `apng-creator` - Create an APNG from a numerically indexed PNG frame sequence.
- `batch-image-compressor` - Compress JPEG and PNG images without changing
  resolution or format.

## Repository Layout

```text
skills-collection/
├── skills/
│   ├── apng-creator/
│   │   ├── SKILL.md
│   │   └── scripts/
│   └── batch-image-compressor/
│       └── SKILL.md
└── packaged-skills/
    ├── apng-creator.skill
    └── batch-image-compressor.skill
```

Use the folders under `skills/` for source editing and manual installation. Use
the archives under `packaged-skills/` only when a tool or marketplace expects a
single packaged artifact.

## Installation Guide

There are two practical ways to install these skills: ask an agent to install
them for you, or copy/link the skill folders manually.

### Option 1: Ask an agent to install automatically

Open your target agent and give it one of these prompts.

```text
Install the <skill-name> skill from this repository's skills/<skill-name> folder.
Install it as a global skill for the agent I am using. Keep the folder name
<skill-name> and include all bundled files such as scripts/, references/, or assets/.
After installing, list available skills or tell me how to verify it loaded.
```

```text
Install the <skill-name> skill from this repository's skills/<skill-name> folder
as a project-local skill in the current repository. Keep the folder name
<skill-name> and include all bundled files. After installing, list available
skills or tell me how to verify it loaded.
```

For a project-local install, replace "global skill" with "project-local skill in
the current repository."

### Option 2: Install manually

Run commands from the root of this repository unless noted otherwise. Replace
`<skill-name>` with the folder name of the skill you want to install.

#### Codex

Install globally:

```bash
mkdir -p ~/.codex/skills
cp -R skills/<skill-name> ~/.codex/skills/<skill-name>
```

Restart Codex after installing so it reloads the skill list.

#### Claude Code

Install globally:

```bash
mkdir -p ~/.claude/skills
cp -R skills/<skill-name> ~/.claude/skills/<skill-name>
```

Install for one project:

```bash
mkdir -p /path/to/project/.claude/skills
cp -R skills/<skill-name> /path/to/project/.claude/skills/<skill-name>
```

Claude Code can invoke loaded skills automatically, or directly with
`/<skill-name>`.

#### Gemini CLI

Install from the local folder:

```bash
gemini skills install ./skills/<skill-name>
gemini skills list
```

For development, link the whole local collection instead of copying it:

```bash
gemini skills link ./skills
gemini skills list
```

If Gemini CLI is already running, use `/skills reload`.

#### OpenCode

Install globally:

```bash
mkdir -p ~/.config/opencode/skills
cp -R skills/<skill-name> ~/.config/opencode/skills/<skill-name>
```

Install for one project:

```bash
mkdir -p /path/to/project/.opencode/skills
cp -R skills/<skill-name> /path/to/project/.opencode/skills/<skill-name>
```

OpenCode also recognizes the shared Agent Skills paths
`~/.agents/skills/<name>` and `.agents/skills/<name>`.

#### OpenClaw

Install globally:

```bash
mkdir -p ~/.openclaw/skills
cp -R skills/<skill-name> ~/.openclaw/skills/<skill-name>
```

Install for one workspace:

```bash
mkdir -p /path/to/workspace/skills
cp -R skills/<skill-name> /path/to/workspace/skills/<skill-name>
```

OpenClaw also recognizes shared Agent Skills paths such as
`~/.agents/skills/<name>` and `<workspace>/.agents/skills/<name>`.

## Compatibility Notes

- The portable source format is a directory containing `SKILL.md` plus optional
  supporting files such as `scripts/`, `references/`, or `assets/`.
- Product-specific metadata is intentionally omitted from these skills.
- Some tools load new skills only after restart or reload.
- Treat third-party skills as code: read `SKILL.md` and bundled scripts before
  enabling them.

## References

- OpenAI skills catalog: https://github.com/openai/skills
- Claude Code skills: https://code.claude.com/docs/en/skills
- Gemini CLI skills commands: https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/cli-reference.md
- OpenCode Agent Skills: https://opencode.ai/docs/skills
- OpenClaw skills: https://docs.openclaw.ai/tools/skills
