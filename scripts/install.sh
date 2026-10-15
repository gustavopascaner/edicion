#!/bin/bash
# Instala la skill "edicion" en macOS para Claude Code y Codex, con todo lo que necesita.
# uso (desde la carpeta clonada del repo):  bash scripts/install.sh [ruta/a/edicion-sfx.zip]
# Instala lo que falte: Homebrew, Node, FFmpeg, whisper-cpp y Google Chrome; el modelo de Whisper; las dependencias
# de Node; los efectos de sonido; y enlaza la skill en ~/.claude y ~/.codex. (En Windows: scripts\install.ps1)
SK="$(cd "$(dirname "$0")/.." && pwd)"
ok(){ printf "\033[32mOK\033[0m  %s\n" "$1"; }; info(){ printf "\033[36m...\033[0m %s\n" "$1"; }; warn(){ printf "\033[33m!!\033[0m  %s\n" "$1"; }

# 0 · Herramientas de desarrollador (git y python3)
if ! xcode-select -p >/dev/null 2>&1; then
  warn "Faltan las herramientas de desarrollador de Apple: se abre el instalador. Cuando termine, volvé a correr este script."
  xcode-select --install; exit 1
fi
# 1 · Homebrew
if ! command -v brew >/dev/null; then
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$b" ] && eval "$("$b" shellenv)"; done
fi
if ! command -v brew >/dev/null; then
  info "Instalando Homebrew (te va a pedir la contraseña de la Mac)..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || { warn "No se pudo instalar Homebrew"; exit 1; }
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$b" ] && eval "$("$b" shellenv)"; done
fi
ok "Homebrew"
# 2 · Programas
for p in "node:node" "ffmpeg:ffmpeg" "whisper-cli:whisper-cpp"; do
  c=${p%%:*}; f=${p#*:}
  if command -v "$c" >/dev/null; then ok "$f ya instalado"; else info "Instalando $f..."; brew install "$f" >/dev/null && ok "$f"; fi
done
if [ -d "/Applications/Google Chrome.app" ] || [ -n "$CHROME" ]; then ok "Google Chrome ya instalado"
else info "Instalando Google Chrome..."; brew install --cask google-chrome >/dev/null && ok "Google Chrome"; fi
# 3 · Modelo de Whisper (~1,6 GB)
M="$HOME/.cache/whisper-cpp/ggml-large-v3-turbo.bin"
if [ -f "$M" ] && [ "$(stat -f%z "$M")" -gt 1000000000 ]; then ok "Modelo de Whisper ya descargado"
else info "Descargando el modelo de Whisper (~1,6 GB, tarda unos minutos)..."; mkdir -p "$(dirname "$M")"
  curl -L --fail -o "$M" https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin && ok "Modelo de Whisper"; fi
# 4 · Dependencias de Node
info "Instalando dependencias de Node..."; (cd "$SK/engine" && npm ci --silent) && ok "Dependencias de Node"
# 5 · Efectos de sonido
if [ -n "$1" ]; then unzip -o -q "$1" -d "$SK/assets/sfx" && ok "Efectos de sonido ($(find "$SK/assets/sfx" -name '*.wav' | wc -l | tr -d ' ') archivos)"
elif ! find "$SK/assets/sfx" -name '*.wav' | grep -q .; then warn "Faltan los efectos de sonido: volvé a correr con la ruta a edicion-sfx.zip"; fi
# 6 · Enlazar la skill
for d in "$HOME/.claude/skills" "$HOME/.codex/skills"; do
  mkdir -p "$d"
  if [ -e "$d/edicion" ] && [ ! -L "$d/edicion" ]; then [ "$(cd "$d/edicion" && pwd -P)" = "$(cd "$SK" && pwd -P)" ] && ok "Skill en $d/edicion" || warn "$d/edicion ya existe y no es un enlace: lo dejo como está"; continue; fi
  ln -sfn "$SK" "$d/edicion" && ok "Skill enlazada en $d/edicion"
done
# 7 · Chequeo final
echo; python3 -I "$SK/scripts/doctor.py"
echo; echo "Listo. En Claude Code: /edicion <video>   ·   En Codex: \$edicion <video>"
