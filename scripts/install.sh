#!/bin/bash
# Instala la skill para Claude Code y/o Codex enlazando esta carpeta, e instala dependencias.
# uso: bash scripts/install.sh [ruta/a/edicion-sfx.zip]   (desde la carpeta clonada del repo)
set -e
SK="$(cd "$(dirname "$0")/.." && pwd)"
for d in "$HOME/.claude/skills" "$HOME/.codex/skills"; do
  mkdir -p "$d"
  if [ -e "$d/edicion" ] && [ ! -L "$d/edicion" ]; then echo "⚠️  $d/edicion ya existe y no es un enlace: lo dejo como está"; continue; fi
  ln -sfn "$SK" "$d/edicion" && echo "✓ enlazada en $d/edicion"
done
command -v brew >/dev/null && { command -v ffmpeg >/dev/null || brew install ffmpeg; command -v whisper-cli >/dev/null || brew install whisper-cpp; }
(cd "$SK/engine" && npm ci --silent) && echo "✓ dependencias de node"
M="$HOME/.cache/whisper-cpp/ggml-large-v3-turbo.bin"
[ -f "$M" ] || { mkdir -p "$(dirname "$M")"; curl -L -o "$M" https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin; }
if [ -n "$1" ]; then unzip -o -q "$1" -d "$SK/assets/sfx" -x "__MACOSX/*" && echo "✓ sonidos instalados ($(find "$SK/assets/sfx" -name '*.wav' | wc -l | tr -d ' ') archivos)";
elif ! find "$SK/assets/sfx" -name '*.wav' | grep -q .; then echo "⚠️  Faltan los sonidos: volvé a correr con la ruta a edicion-sfx.zip"; fi
echo "✓ listo. En Claude Code: /edicion <video>. En Codex: \$edicion <video>."
