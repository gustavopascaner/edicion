# Cómo importar en DaVinci Resolve

Usá el archivo `*_resolve.xml` de esta carpeta (el `*_premiere.xml` es para Premiere). No muevas ni renombres la carpeta: los assets están enlazados con rutas absolutas.

1. **Proyecto nuevo y vacío** (Project Manager → New Project).
2. Antes de importar: **File → Project Settings → Image Scaling → Input Scaling → Mismatched resolution files: «Center crop with no resizing»** → Save. Así la escala del XML (zooms, b-roll, marcos) se aplica igual que en Premiere.
3. **File → Import → Timeline…** (Mac: Cmd+Shift+I · Windows: Ctrl+Shift+I) → elegir `*_resolve.xml`. En el cuadro *Load XML* dejar tildado:
   - *Automatically set project settings* (toma 1080×1920 vertical y 30 fps)
   - *Automatically import source clips into media pool*
   - *Use sizing information*
4. Si algún clip aparece en rojo (offline): seleccionarlo en el Media Pool → clic derecho → *Relink Selected Clips…* → elegir la carpeta `Assets`.

## Qué trae
- **V1** cara a cámara con los reencuadres y zooms · **V2** b-roll · **V3+** subtítulos y motion graphics (ProRes 4444 con alfa).
- **A1** voz: cada corte lleva un crossfade de 2 fotogramas (sin clics).
- **A2+** SFX y música **ya procesados** (`Assets/Audio_Resolve`): el nivel, el recorte y los fades están grabados en el archivo, por eso los clips van a 0 dB. Subir o bajar con el volumen del clip o el fader de la pista.
- Marcadores de las partes (HOOK, CTA…).
- Subtítulos nativos opcionales: **File → Import → Subtitle…** → `Assets/Subtitulos/*.srt` y arrastrarlo a la línea de tiempo (los subtítulos con diseño ya están en V3).

## Si algo se ve raro
- **Motion graphics con fondo negro o bordes claros**: seleccionarlos en el Media Pool → clic derecho → *Clip Attributes… → Video → Alpha Mode: Straight*.
- **Zooms o b-roll con otro tamaño**: revisar el paso 2 (Center crop with no resizing) y volver a importar en un proyecto nuevo.
