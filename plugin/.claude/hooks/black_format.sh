#!/bin/bash
# Hook PostToolUse: ejecuta black sobre archivos Python editados.
# El JSON de entrada tiene la forma: { "tool_input": { "file_path": "..." }, ... }
#
# Resolución de black (en orden de prioridad):
#   1. venv/bin/black  (relativo al directorio del proyecto)
#   2. .venv/bin/black
#   3. black del PATH global

INPUT=$(cat)
FILE=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null)

if [[ "$FILE" != *.py ]]; then
  exit 0
fi

# Detectar el directorio raíz del proyecto (donde está este hook)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

if [[ -x "$PROJECT_ROOT/venv/bin/black" ]]; then
  BLACK="$PROJECT_ROOT/venv/bin/black"
elif [[ -x "$PROJECT_ROOT/.venv/bin/black" ]]; then
  BLACK="$PROJECT_ROOT/.venv/bin/black"
elif command -v black &>/dev/null; then
  BLACK="black"
else
  echo "black no encontrado, saltando formateo" >&2
  exit 0
fi

"$BLACK" "$FILE"
