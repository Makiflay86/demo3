#!/bin/bash
# Instala el plugin de Claude Code en el proyecto destino.
# Uso: bash install.sh /ruta/a/tu-proyecto

set -e

DESTINO="${1:-$(pwd)}"

if [[ ! -d "$DESTINO" ]]; then
  echo "Error: el directorio '$DESTINO' no existe." >&2
  exit 1
fi

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Instalando plugin en: $DESTINO"

# Copiar CLAUDE.md si no existe ya
if [[ -f "$DESTINO/CLAUDE.md" ]]; then
  echo "  ⚠ CLAUDE.md ya existe, no se sobreescribe. Consulta '$PLUGIN_DIR/CLAUDE.md' como referencia."
else
  cp "$PLUGIN_DIR/CLAUDE.md" "$DESTINO/CLAUDE.md"
  echo "  ✓ CLAUDE.md copiado"
fi

# Copiar .claude/settings.json
mkdir -p "$DESTINO/.claude/hooks"

if [[ -f "$DESTINO/.claude/settings.json" ]]; then
  echo "  ⚠ .claude/settings.json ya existe, no se sobreescribe. Revísalo manualmente."
else
  cp "$PLUGIN_DIR/.claude/settings.json" "$DESTINO/.claude/settings.json"
  echo "  ✓ .claude/settings.json copiado"
fi

# Copiar hook
cp "$PLUGIN_DIR/.claude/hooks/black_format.sh" "$DESTINO/.claude/hooks/black_format.sh"
chmod +x "$DESTINO/.claude/hooks/black_format.sh"
echo "  ✓ .claude/hooks/black_format.sh copiado y marcado como ejecutable"

# Verificar black
BLACK_OK=false
if [[ -x "$DESTINO/venv/bin/black" ]] || [[ -x "$DESTINO/.venv/bin/black" ]]; then
  BLACK_OK=true
elif command -v black &>/dev/null; then
  BLACK_OK=true
fi

if $BLACK_OK; then
  echo "  ✓ black encontrado"
else
  echo "  ⚠ black no encontrado. Instálalo con: pip install black"
fi

echo ""
echo "Plugin instalado correctamente en '$DESTINO'."
echo "Recuerda editar CLAUDE.md con la información de tu proyecto."
