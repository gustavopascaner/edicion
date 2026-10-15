# edicion — skill de edición para Claude Code y Codex

Edita un video crudo vertical (talking head) con corte ajustado sin pausas, motion graphics con alfa, subtítulos dinámicos, b-roll y efectos de sonido, y entrega un **XML para Premiere** con todos los assets enlazados.

Las instrucciones para el agente están en [`SKILL.md`](SKILL.md).

## Instalación (macOS)

Requisitos: Google Chrome, Node 18+, Python 3 y [Homebrew](https://brew.sh) (para `ffmpeg` y `whisper-cpp`).

No hace falta cuenta de GitHub. Los efectos de sonido **no están en el repo** (tienen licencias de terceros): pedile a Gus el archivo `edicion-sfx.zip` y pasá su ruta al instalador.

```bash
git clone https://github.com/gustavopascaner/edicion.git ~/skills/edicion
```

```bash
bash ~/skills/edicion/scripts/install.sh ~/Downloads/edicion-sfx.zip
```

El instalador descomprime los sonidos en `assets/sfx/`, además enlaza la carpeta en `~/.claude/skills/edicion` (Claude Code) y `~/.codex/skills/edicion` (Codex), instala `ffmpeg`, `whisper-cpp` y las dependencias de node, y descarga el modelo de Whisper (~1,6 GB). Para actualizar: `git pull` en la carpeta clonada.

## Uso

- **Claude Code:** `/edicion /ruta/al/video.mp4` (o una carpeta con el crudo y material de apoyo).
- **Codex:** `$edicion /ruta/al/video.mp4`, o pedirle "editá este video como los anteriores".

Resultado en la carpeta del video: `<NOMBRE>_EDIT/` con el XML, `Assets/{MG,Subtitulos,SFX}` y un `LEEME.md`. En Premiere: Archivo → Importar → el XML (sin mover la carpeta).

## Estructura

| Carpeta | Qué hay |
|---|---|
| `scripts/` | Transcripción, corte, render de gráficos, armado del XML, importador de SFX |
| `engine/` | Motor HTML de motion graphics (se renderiza con Chrome) y tipografías |
| `reference/` | Catálogo de escenas y un `jobs.js` de ejemplo |
| `assets/sfx/` | Librería de efectos de sonido + `catalog.json` |
| `agents/openai.yaml` | Metadatos para Codex |

## Efectos de sonido

Ver la librería: `python3 -I scripts/sfx_import.py --list`.
Sumar un sonido: `python3 -I scripts/sfx_import.py archivo.wav --id nombre --cat categoria --desc "cuándo usarlo"`.
El importador recorta silencios, normaliza a −16 LUFS, convierte a WAV 48 kHz y lo registra en el catálogo.

Las tipografías de `engine/fonts` (Bricolage Grotesque, Instrument Serif, Inter Tight, JetBrains Mono) son de Google Fonts, con licencia SIL Open Font License.
