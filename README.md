# edicion — skill de edición para Claude Code y Codex

Edita un video crudo vertical (talking head) con corte ajustado sin pausas, motion graphics con alfa, subtítulos dinámicos, b-roll y efectos de sonido, y entrega un **XML para Premiere** con todos los assets enlazados.

Las instrucciones para el agente están en [`SKILL.md`](SKILL.md).

## Instalación (macOS)

Requisitos: Google Chrome, Node 18+, Python 3 y [Homebrew](https://brew.sh) (para `ffmpeg` y `whisper-cpp`).

No hace falta cuenta de GitHub. Antes de instalar, bajá `edicion-sfx.zip` (ver [Efectos de sonido](#efectos-de-sonido)) y pasá su ruta al instalador.

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

**Descarga (acceso restringido):** [edicion-sfx.zip en Google Drive](https://drive.google.com/file/d/1xip12kbwPecSh9bdOSapEasYvJaoPAxK/view?usp=sharing)

> **Licencia:** los efectos de sonido no se incluyen en este repositorio porque tienen licencias de terceros (Envato Elements y otros proveedores) que no permiten redistribuirlos. El archivo de Drive solo lo pueden descargar las personas autorizadas. Si no tenés acceso, la skill funciona igual, pero sin sonidos, y avisa cuáles faltan. También podés sumar tus propios sonidos con `scripts/sfx_import.py`. `assets/sfx/catalog.json` solo describe cada sonido (categoría, duración, volumen); no contiene audio.


Ver la librería: `python3 -I scripts/sfx_import.py --list`.
Sumar un sonido: `python3 -I scripts/sfx_import.py archivo.wav --id nombre --cat categoria --desc "cuándo usarlo"`.
El importador recorta silencios, normaliza a −16 LUFS, convierte a WAV 48 kHz y lo registra en el catálogo.

Las tipografías de `engine/fonts` (Bricolage Grotesque, Instrument Serif, Inter Tight, JetBrains Mono) son de Google Fonts, con licencia SIL Open Font License.
