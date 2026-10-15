# edicion — skill de edición para Claude Code y Codex

Edita un video crudo vertical (talking head) con corte ajustado sin pausas, motion graphics con alfa, subtítulos dinámicos, b-roll y efectos de sonido, y entrega un **XML para Premiere** con todos los assets enlazados.

Qué hace:
- **Corte ajustado**: saca pausas, tomas falladas y repeticiones, y verifica el corte re-transcribiéndolo.
- **Motion graphics** con alfa sincronizados con las palabras: 3 pantallas completas y como máximo 3 gráficos superpuestos. **Subtítulos dinámicos** todo el tiempo, que se ocultan solos mientras hay un motion graphic para no competir.
- **B-roll semántico y música de Envato**: elige 3 momentos, busca con el MCP de Envato, ubica las vistas previas y las reemplaza por los originales licenciados.
- **Diseño sonoro sutil** con la librería de SFX: como máximo 5 efectos en toda la edición, en los momentos más importantes (remates, gancho, CTA, cortes).
- **Reencuadres y zooms** según la intención de cada frase (snap en el gancho, punch-in en el énfasis, alternancia para disimular jump cuts).
- **Dirección creativa**: revisa que b-roll, gráficos, subtítulos, cámara, SFX y música no compitan, y dibuja la línea de tiempo.
- **Tiempo de procesamiento**: al terminar informa cuánto tardó, con el desglose por paso.

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
| `scripts/envato.py` | Búsqueda en Envato, vistas previas, reemplazo por originales licenciados |
| `scripts/director.js` | Revisión de dirección creativa + línea de tiempo |
| `agents/openai.yaml` | Metadatos para Codex |

## Efectos de sonido

**Descarga (acceso restringido):** [edicion-sfx.zip en Google Drive](https://drive.google.com/file/d/1xip12kbwPecSh9bdOSapEasYvJaoPAxK/view?usp=sharing)

> **Licencia:** los efectos de sonido no se incluyen en este repositorio porque tienen licencias de terceros (Envato Elements y otros proveedores) que no permiten redistribuirlos. El archivo de Drive solo lo pueden descargar las personas autorizadas. Si no tenés acceso, la skill funciona igual, pero sin sonidos, y avisa cuáles faltan. También podés sumar tus propios sonidos con `scripts/sfx_import.py`. `assets/sfx/catalog.json` solo describe cada sonido (categoría, duración, volumen); no contiene audio.


Ver la librería: `python3 -I scripts/sfx_import.py --list`.
Sumar un sonido: `python3 -I scripts/sfx_import.py archivo.wav --id nombre --cat categoria --desc "cuándo usarlo"`.
El importador recorta silencios, normaliza a −16 LUFS, convierte a WAV 48 kHz y lo registra en el catálogo.

Las tipografías de `engine/fonts` (Bricolage Grotesque, Instrument Serif, Inter Tight, JetBrains Mono) son de Google Fonts, con licencia SIL Open Font License.

## Envato

El MCP público de Envato solo busca, no descarga ni licencia. `scripts/envato.py` lo usa por HTTP, así que no hace falta configurarlo en el agente. Mientras el material no esté licenciado, el XML usa las vistas previas con marca de agua (con el prefijo `PREVIEW_`). Para licenciar, alguien con cuenta de Envato Elements descarga cada ítem desde su link (*Download* → licenciar para el proyecto). Después, `envato.py collect` los toma de `~/Downloads` y actualiza la edición.
