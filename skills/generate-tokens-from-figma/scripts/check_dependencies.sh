#!/usr/bin/env bash
set -euo pipefail

FIGMA_HELP_URL="https://help.figma.com/hc/en-us/articles/39166810751895-Figma-skills-for-MCP"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"

found_figma_use="false"
for path in \
  "$CODEX_HOME/skills/figma-use/SKILL.md" \
  "$CODEX_HOME/skills/figma:figma-use/SKILL.md" \
  "$CODEX_HOME/plugins/cache/openai-curated/figma"/*/skills/figma-use/SKILL.md \
  "$CODEX_HOME/plugins/cache"/*/figma*/skills/figma-use/SKILL.md
do
  if [ -f "$path" ]; then
    found_figma_use="true"
    break
  fi
done

if [ "$found_figma_use" != "true" ]; then
  cat >&2 <<EOF
Missing required Figma MCP skill: figma-use.

Install the Figma MCP skills before generating tokens:
$FIGMA_HELP_URL

Figma documents two setup paths:
- Install the Figma plugin in a supported agentic tool; the skills are included automatically.
- Download the skills manually and place them in the skills folder expected by your tool.
EOF
  exit 2
fi

if command -v python3 >/dev/null 2>&1; then
  echo "python=$(command -v python3)"
  echo "figma-use=available"
  exit 0
fi

if command -v python >/dev/null 2>&1; then
  python_version="$(python - <<'PY'
import sys
print(sys.version_info[0])
PY
)"
  if [ "$python_version" = "3" ]; then
    echo "python=$(command -v python)"
    echo "figma-use=available"
    exit 0
  fi
fi

echo "Python 3 is missing; attempting automatic installation..." >&2

if command -v brew >/dev/null 2>&1; then
  brew install python
elif command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3
elif command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y python3
elif command -v yum >/dev/null 2>&1; then
  sudo yum install -y python3
elif command -v apk >/dev/null 2>&1; then
  sudo apk add python3
elif [ "$(uname -s)" = "Darwin" ] && command -v xcode-select >/dev/null 2>&1; then
  xcode-select --install
  cat >&2 <<'EOF'
Started macOS Command Line Tools installation. Re-run this dependency check after the installer finishes.
EOF
else
  cat >&2 <<'EOF'
No supported automatic Python installer was found.
Install Python 3, then re-run the dependency check.
EOF
  exit 3
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python installation command completed, but python3 is still unavailable on PATH." >&2
  exit 3
fi

echo "python=$(command -v python3)"
echo "figma-use=available"
