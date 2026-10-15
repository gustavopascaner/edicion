---
name: edicion
description: Edita un video crudo vertical de Gus Pascaner (talking head para redes, marketing médico) con corte ajustado sin pausas ni tomas falladas, motion graphics modernos con alfa, subtítulos dinámicos, b-roll de la carpeta y efectos de sonido de su propia librería, y entrega un XML para Premiere con todos los assets enlazados (sin render de vista previa). Usar cuando el usuario escribe /edicion con un video o carpeta, o pide "editá este video como los anteriores".
---

# /edicion — edición con motion graphics + XML para Premiere

Entrada: un video crudo (o una carpeta con el crudo + material de apoyo: clips de kling/IA, PNG, música, SFX).
Salida en la carpeta del video: `<NAME>_EDIT/` con `<NAME>_v1_premiere.xml`, `Assets/{MG,Subtitulos,SFX}`, `LEEME.md`. **No se renderiza vista previa MP4** (el usuario lo pidió para ganar velocidad): la revisión visual se hace con las hojas de contacto del paso 5.
Hablarle al usuario en español rioplatense (voseo). Avisarle brevemente el avance entre pasos largos.

Rutas: `SK` = la carpeta de esta skill, donde está este SKILL.md (Claude Code: `~/.claude/skills/edicion`; Codex: `~/.codex/skills/edicion`) · scripts en `$SK/scripts` · motor en `$SK/engine/engine.html` · catálogo en `$SK/reference/escenas.md` · ejemplo en `$SK/reference/ejemplo_jobs.js`.
Workdir del proyecto: `<carpeta>/<NAME>_EDIT/.work` (persistente, permite hacer v2 en otra sesión).
Correr Python siempre con `python3 -I`. Pasar rutas con espacios entre comillas.

## 0 · Preparación
1. Dependencias: `which ffmpeg whisper-cli` (si faltan: `brew install ffmpeg whisper-cpp`). Modelo: `~/.cache/whisper-cpp/ggml-large-v3-turbo.bin` (si falta, descargar de `https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin`). Google Chrome instalado (o la variable `CHROME` con la ruta al ejecutable). `$SK/engine/node_modules` (si falta: `cd $SK/engine && npm ci`).
2. Inventario de la carpeta: `ffprobe` de cada video (duración, fps, rotación, `nb_frames`), tamaño de los PNG, duración de los audios. El crudo suele ser 1920×1080 con rotación 90 (= vertical 1080×1920, 30 fps).
3. Mirar el material de apoyo: `ffmpeg -vf "fps=2,scale=150:-1,tile=10x2"` → mirar la imagen. Identificar qué ilustra cada clip/foto (gancho, chiste, metáfora). Si hay escenas, detectar cortes con `scdet`.
4. Mirar un cuadro del crudo (color de ropa → colores de subtítulos, ver escenas.md).

## 1 · Transcribir
`python3 -I $SK/scripts/transcribe.py "<crudo>" "<work>"` → lista de frases con tiempos.
Whisper alucina sobre ruido ("Gracias", "Gracias por ver el video", "Suscríbete al canal", "CC por…"): verificar esas zonas y cualquier duda con
`python3 -I $SK/scripts/check.py "<work>" 21.9-26.3 ...` (habla ≈ −5…−25 dB; ruido ≈ −48…−70 dB).

## 2 · Decidir el guion (criterio editorial)
- **Sacar** frases repetidas, falsos arranques, tomas incompletas y tropiezos. Ante varias tomas de lo mismo, quedarse con la **última completa**.
- Corregir el texto para subtítulos (voseo: "querés", "tenés", "dejá"; "método IDEAS"; nombres propios).
- **CTA**: si grabó varias alternativas, usar por defecto **"mandame un mensaje(ito)"** (fue la elección explícita del usuario). Las demás se listan en el LEEME con su timecode del crudo. Si hay una lista de CTAs que **no** se repiten (opciones distintas, sin la misma intro), se pueden dejar todas como OPCIÓN 01/02… En la respuesta final decir cuál elegiste.
- Escribir `<work>/segs.json`: lista de **segmentos lógicos** (cada uno = idea que comparte un gráfico), cada uno con frases `[a, b, "texto"]` tomadas de las frases de transcribe/check.

## 3 · Corte AJUSTADO (obligatorio)
`python3 -I $SK/scripts/tighten.py "<work>"` recorta cada frase sobre la energía real de la voz y corta pausas internas ≥ 0,25 s (lecturas, miradas al costado, respiraciones). El usuario pidió explícitamente cortes sin silencios: **no dejar pausas**.
Crear `<work>/config.json` (abajo) y correr `python3 -I $SK/scripts/edl.py "<work>"` → imprime la duración y los tiempos por segmento y **re-transcribe el corte**: confirmar que no falte ni sobre ninguna palabra. Si falta un arranque, revisar con check.py y ajustar segs.json.

```json
{ "name": "SIGN_SPINNER", "version": 1, "fps": 30, "tail": 1.2,
  "src": "/abs/crudo.mp4", "edit_dir": "/abs/carpeta/SIGN_SPINNER_EDIT",
  "caption_colors": {"act":"var(--hot)","kwAct":"var(--lime)","kw":"#FFB08A"},
  "keywords": ["pacientes","scroll","correctas"],
  "broll": { "kl": {"path":"/abs/kling.mp4","frames":97,"rate":24,"w":1080,"h":1916},
             "s1": {"path":"/abs/foto.png","still":true,"w":941,"h":1672} },
  "music": "/abs/musica.wav", "music_dur": 53.1,
  "markers": [["HOOK",0],["CTA · Mandame un mensaje",17]] }
```
`tail` = segundos extra al final (cara a cámara) para que se lea el último gráfico.

## 4 · Diseñar los motion graphics → `<work>/jobs.js`
Basarse en `reference/ejemplo_jobs.js` y `reference/escenas.md`. Estilo fijo (al usuario le encantó, no cambiarlo): tarjetas crema con kicker mono y punto naranja, títulos Bricolage condensados en mayúsculas, resaltados naranja, ✓ lima, pantallas completas con grano y wipe en capas.
Reglas:
- **Algo pasa en cada segmento**: tarjeta, lista que se arma, sello, sticker, b-roll o pantalla completa. Sincronizar cada elemento con la palabra que lo dispara (`W(seg,'palabra')`).
- **Pantallas completas (fs) que tapan la cara** en los remates fuertes, de 1 a 3 s, cada 10–15 s aprox. Fondos alternados ink / naranja / crema.
- **Gancho fuerte en los primeros 2 s**: texto grande arriba y, si hay un clip de apoyo divertido o visual, que entre en el gancho (con sticker y flecha o HUD) y la música fuerte.
- **B-roll de la carpeta**: usarlo donde ilustra literalmente lo que se dice (metáforas: ruedita de hámster, cartel, rayos X). Fotos fijas con Ken Burns `[100,112]`. Encima, sticker/HUD/sello.
- Música de la carpeta: fuerte en el gancho (gain ≈ 0.3) y de fondo bajo (≈ 0.08) después. Audio de la carpeta del video (cámara, pasos, etc.) con `X()`.
- **SFX de la librería** (`$SK/assets/sfx`, ver abajo): cada gráfico lleva su sonido en el último parámetro de `J()`, y los sonidos literales van con `S()`.
- Usar escenas nuevas cuando la metáfora lo pida (agregarlas a engine.html siguiendo escenas.md). No reusar textos fijos de otras escenas que no apliquen (ej. `hook` dice MARKETING DESDE CERO).
- Pista `ov2` solo si una tarjeta debe ir encima de otro overlay (ej. tracker).

## 4b · Efectos de sonido (librería propia de la skill)
Todos los SFX viven en `$SK/assets/sfx/<categoría>/<id>.wav`, normalizados a −16 LUFS, y están descritos en `catalog.json` (duración, volumen por categoría y *anchor* = el golpe o arranque que cae justo en el evento). Ver la lista completa: `python3 -I $SK/scripts/sfx_import.py --list`. Al armar el XML se copian a `Assets/SFX` solo los que se usaron.

| Categoría | Cuándo |
|---|---|
| `whoosh` | Entrada de pantallas completas, wipes, cambios fuertes de tarjeta |
| `build` | Antes de un corte o remate (`reverse-whoosh`; `riser` ≈ 6 s, solo por id para el remate más grande) |
| `pop` | Aparición de tarjetas, stickers, ítems de lista |
| `click` | Interfaces: búsqueda, DM, botón seguir, tildar |
| `ding` | ✓ check, acierto, idea, dato positivo |
| `error` | ✗, tachar, mito, lo que está mal (`game-over` es una voz robótica: usar con humor) |
| `hit` | Remates, sellos, fs de impacto (`bass-drop` solo por id, máximo 1 por video) |
| `glitch` · `poof` | Algo que falla, se rompe o desaparece |
| `zoom` · `bounce` · `wind` | Punch-in o lupa · rebote con humor · aparición mágica |
| `foley` · `splash` · `car` | **Literales**: solo si lo que se dice o se ve coincide (escribir, cierre, estirar, inodoro, agua, autos) |

Uso en `jobs.js`:
- Categoría (se van alternando las variantes) o id puntual: `J(..., 'pop')` · `J(..., 'bass-drop')`.
- Varios sonidos dentro de un gráfico, en segundos desde su inicio: `J(..., ['pop', ['ding', R(s,W(3,'formando'))], ['click', 1.2, {gain:.2}]])`. Usarlo para que cada ✓ de una lista suene (`ding` o `pop`) al aparecer.
- Sonido suelto en un segundo de la línea de tiempo: `S('splash', W(4,'agua'))` · `S('car-pass-2', t, {gain:.25, dur:3})`.
Criterio: no poner sonido a todo. Un sonido por evento visual, sin pisarse (dejar ≥ 0,3 s entre dos), y los literales solo cuando suman al chiste o la metáfora. `node render.js --plan` lista todos los SFX con su segundo para revisarlos.
Para sumar sonidos nuevos: `python3 -I $SK/scripts/sfx_import.py <archivo> --id <id> --cat <categoría> [--anchor peak|onset] [--max 4] --desc "..."` (recorta, normaliza y lo registra).

## 5 · Probar y renderizar
1. `node $SK/scripts/render.js "<work>" --plan` (lista los gráficos con tiempos; detecta palabras no encontradas).
2. `T=end-0.4 node $SK/scripts/render.js "<work>" --test --only='^(?!cap)'` y luego `python3 -I $SK/scripts/sheets.py "<work>"` → **mirar las hojas (imágenes)** y corregir: textos cortados, superposiciones, elementos tapando lo importante del b-roll, timing (que el gráfico termine de armarse antes de salir).
3. Render final (en segundo plano, tarda unos minutos): `node $SK/scripts/render.js "<work>" --only='^(?!cap)'` y después `node $SK/scripts/render.js "<work>" --only='^cap'`. Los SFX se copian a `Assets/SFX` al armar el XML.

## 6 · XML + entrega
- `python3 -I $SK/scripts/build_xml.py "<work>"` y `xmllint --noout <xml>` (también genera el `.srt`).
- **No correr `preview.py`** salvo que el usuario pida explícitamente la vista previa. La revisión de gráficos ya se hizo con las hojas del paso 5; si hay que corregir algo, volver a renderizar solo ese job con `--only='^id$'` y regenerar el XML.
- Escribir `LEEME.md` en `<NAME>_EDIT/`: cómo importar (Archivo → Importar → XML; no mover la carpeta), tabla de pistas, estructura, qué se sacó, CTAs alternativos con timecodes, para revisar (Cmd+Shift+D para crossfades de audio, SRT nativo opcional).
- Responder corto con la ruta del XML: duración final, cómo se usó el b-roll, gráficos destacados, decisiones a revisar (CTA elegido, tomas elegidas).

## Versiones (v2, ajustes)
Si el usuario pide cambios sobre una edición existente: reusar `<NAME>_EDIT/.work`, subir `version` en config.json y apuntar `edit_dir` a `<NAME>_EDIT_v2` (para no pisar la v1), editar segs.json/jobs.js, y repetir desde el paso 3. Dejar la versión anterior intacta.

## Notas técnicas
- Compatible con Claude Code y Codex: todas las rutas son relativas a `$SK`; no depende de herramientas propias de ningún agente.
- XML FCP7 (xmeml v4): clipitems a la base de tiempo de la secuencia (30), archivos con su propia `rate` (kling = 24). En macOS, los nombres con tildes suelen estar en NFD: armar las rutas listando el directorio (`os.listdir`), no tipeándolas.
- No usar `rm -rf` con globs relativos (lo bloquea el sistema). Usar carpetas nuevas o rutas absolutas.
- Los MG con grano a pantalla completa pesan (QuickTime Animation); es normal que `Assets/MG` ocupe cientos de MB.
