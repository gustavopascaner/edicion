---
name: edicion
description: Edita un video crudo vertical de Gus Pascaner (talking head para redes, marketing médico) con corte ajustado sin pausas ni tomas falladas, motion graphics modernos con alfa, subtítulos dinámicos, b-roll semántico y música de Envato, diseño sonoro automático con su librería de SFX, reencuadres y zooms según el discurso, y una revisión de dirección creativa; entrega un XML para Premiere con todos los assets enlazados (sin render de vista previa) e informa cuánto tardó. Usar cuando el usuario escribe /edicion con un video o carpeta, o pide "editá este video como los anteriores".
---

# /edicion — edición con motion graphics + XML para Premiere

Entrada: un video crudo (o una carpeta con el crudo + material de apoyo: clips de kling/IA, PNG, música, SFX).
Salida en la carpeta del video: `<NAME>_EDIT/` con `<NAME>_v1_premiere.xml`, `Assets/{MG,Subtitulos,SFX,Envato}`, `LEEME.md`. **No se renderiza vista previa MP4** (el usuario lo pidió para ganar velocidad): la revisión visual se hace con las hojas de contacto del paso 5.
Hablarle al usuario en español rioplatense (voseo). Avisarle brevemente el avance entre pasos largos.

Rutas: `SK` = la carpeta de esta skill, donde está este SKILL.md (Claude Code: `~/.claude/skills/edicion`; Codex: `~/.codex/skills/edicion`) · scripts en `$SK/scripts` · motor en `$SK/engine/engine.html` · catálogo en `$SK/reference/escenas.md` · ejemplo en `$SK/reference/ejemplo_jobs.js`.
Workdir del proyecto: `<carpeta>/<NAME>_EDIT/.work` (persistente, permite hacer v2 en otra sesión).
Correr Python siempre con `python3 -I`. Pasar rutas con espacios entre comillas.

## 0 · Preparación
0. **Cronómetro**: apenas se sabe el nombre, crear el workdir y correr `python3 -I $SK/scripts/timing.py start "<work>"`. Los scripts anotan solos cuánto tarda cada paso.
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
  "music": {"path":"/abs/musica.wav"},
  "face": {"top": 0.22},
  "markers": [["HOOK",0],["CTA · Mandame un mensaje",17]] }
```
`tail` = segundos extra al final (cara a cámara) para que se lea el último gráfico.
`face.top` = altura (0–1) de la parte de arriba de la cabeza en el cuadro (mirarlo en el frame del paso 0.4): limita el zoom máximo para no cortarla. `music` lo completa `envato.py use` (o una ruta de la carpeta del video). Opcionales: `sfx_per_10s` (densidad de SFX, default 4), `sound_design: "manual"`, `max_zoom`.

## 4 · Diseñar los motion graphics → `<work>/jobs.js`
Basarse en `reference/ejemplo_jobs.js` y `reference/escenas.md`. Estilo fijo (al usuario le encantó, no cambiarlo): tarjetas crema con kicker mono y punto naranja, títulos Bricolage condensados en mayúsculas, resaltados naranja, ✓ lima, pantallas completas con grano y wipe en capas.
Reglas:
- **Algo pasa en cada segmento**: tarjeta, lista que se arma, sello, sticker, b-roll o pantalla completa. Sincronizar cada elemento con la palabra que lo dispara (`W(seg,'palabra')`).
- **Pantallas completas (fs) que tapan la cara** en los remates fuertes, de 1 a 3 s, cada 10–15 s aprox. Fondos alternados ink / naranja / crema.
- **Gancho fuerte en los primeros 2 s**: texto grande arriba y, si hay un clip de apoyo divertido o visual, que entre en el gancho (con sticker y flecha o HUD) y la música fuerte.
- **B-roll**: primero el de la carpeta (clips de kling/IA, fotos), donde ilustra lo que se dice (metáforas: ruedita de hámster, cartel, rayos X). Fotos fijas con Ken Burns `[100,112]`. Además, **3 momentos de Envato** (paso 4a). Encima del b-roll, solo sticker/HUD/sello.
- Audio extra de la carpeta del video (cámara, pasos, etc.) con `X()`.
- **SFX**: automáticos (paso 4b). No hace falta poner el último parámetro de `J()` salvo para cambiar el sonido.
- Usar escenas nuevas cuando la metáfora lo pida (agregarlas a engine.html siguiendo escenas.md). No reusar textos fijos de otras escenas que no apliquen (ej. `hook` dice MARKETING DESDE CERO).
- Pista `ov2` solo si una tarjeta debe ir encima de otro overlay (ej. tracker).

## 4a · B-roll semántico + música de Envato
El MCP de Envato **solo busca** (no descarga ni licencia). `envato.py` lo llama por HTTP, así que funciona igual en Claude y en Codex aunque el MCP no esté configurado.
1. **Elegir 3 momentos** del guion donde una imagen real suma: una situación concreta (paciente en consulta, alguien scrolleando), una metáfora visual o un dato que se entiende mejor visto. Repartidos (primer tercio, medio, antes del CTA), de 1,5–3,5 s, **nunca** durante una pantalla completa ni en el CTA final, y en tramos donde la tarjeta de ese momento pueda ser un sticker/HUD o no haya tarjeta.
2. **Buscar** (términos concretos en inglés, describiendo la imagen, no la palabra del guion): `python3 -I $SK/scripts/envato.py search "<work>" video "<términos>" --vertical [--sub Medical]`. Si hay pocos resultados, repetir sin `--vertical` (los horizontales se recortan al centro). Mirar la hoja `<work>/envato/<búsqueda>.jpg` (fila n = candidato #n) y elegir: auténtico (no pose de stock), sujeto centrado que entre en 9:16, luz y color parecidos al crudo, sin texto, que **amplíe** lo que se dice en vez de repetirlo.
3. **Usar**: `python3 -I $SK/scripts/envato.py use "<work>" <clave> <búsqueda>#<n>` (registra la vista previa en `config.broll`) y ubicarlo en jobs.js con `B('<clave>', seg_origen, inicio, dur)`.
4. **Música**: `python3 -I $SK/scripts/envato.py search "<work>" music "<estilo en inglés>" --mood <mood> --tempo "<tempo>" [--genre <género>]` (siempre instrumental). Elegir por el tono del video y por el perfil de energía que imprime (parejo, sin caídas largas; para videos enérgicos `Upbeat (110-140 BPM)`, para videos cálidos `Medium (90-110 BPM)`), y `envato.py use "<work>" music <búsqueda>#<n>`. Si el usuario dejó música en la carpeta, usar esa (`"music": {"path": ...}`). El volumen se arma solo en el XML: fuerte en el gancho, baja bajo la voz y sube en el cierre (`hook_gain` 0.3 · `bed_gain` 0.08 · `outro_gain` 0.22 · `offset` = segundo de la canción donde arranca, para entrar en una parte con energía).
5. **Licenciar y descargar**: mientras tanto el XML usa las vistas previas con marca de agua (prefijo `PREVIEW_`). Si el agente tiene un navegador con la sesión de Envato iniciada: mostrar la lista (`envato.py report "<work>"`) y **pedir confirmación una sola vez**; después, en cada link: *Download* → licenciar para un proyecto con el nombre del video → descargar el original (video en la mayor resolución vertical/HD; música en WAV). Si no hay navegador o no hay sesión, darle al usuario la tabla de links para que lo haga. Luego `python3 -I $SK/scripts/envato.py collect "<work>"` (busca en `~/Downloads`, descomprime, copia a `Assets/Envato` y reemplaza las vistas previas) y volver a correr `build_xml.py`. Nunca usar material de otros bancos ni saltear la búsqueda.

## 4b · Diseño sonoro (automático, con la librería de la skill)
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

**Automático** (por defecto): cada gráfico suena según su escena y sus momentos internos — tarjeta → `pop`; ✓ → `ding`; ✕ y tachado → `error`; sello/stop/remate → `hit`; buscador, DM, seguir → `click`; pantalla completa → `whoosh` (bigword → `hit`); `reverse-whoosh` antes del primer remate grande; `whoosh` suave al cortar a b-roll; `zoom` en el snap del gancho. Después se raleán por prioridad: ≥ 0,35 s entre sonidos, ≤ 3 cada 2 s y ≤ `sfx_per_10s` (4) cada 10 s. Las variantes se alternan para que no suene siempre igual.
Manual (pisa al automático para ese gráfico):
- Categoría o id puntual: `J(..., 'pop')` · `J(..., 'bass-drop')` · `J(..., null)` = sin sonido.
- Varios sonidos dentro de un gráfico, en segundos desde su inicio: `J(..., ['pop', ['ding', R(s,W(3,'formando'))], ['click', 1.2, {gain:.2}]])`. Usarlo para que cada ✓ de una lista suene (`ding` o `pop`) al aparecer.
- Sonido suelto en un segundo de la línea de tiempo: `S('splash', W(4,'agua'))` · `S('car-pass-2', t, {gain:.25, dur:3})`.
Los literales (`foley`, `splash`, `car`) nunca son automáticos: ponerlos con `S()` solo cuando suman al chiste o la metáfora. `node render.js --plan` lista todos los SFX (los automáticos marcados `(auto)`).
Para sumar sonidos nuevos: `python3 -I $SK/scripts/sfx_import.py <archivo> --id <id> --cat <categoría> [--anchor peak|onset] [--max 4] --desc "..."` (recorta, normaliza y lo registra).

## 4c · Reencuadres y zooms (automáticos según el discurso)
`render.js` decide la escala de cada clip de V1 y la escribe en `framing.json`; el XML la aplica con keyframes:
- `snap` (zoom rápido 100→118 %) en el gancho · `punch` (124 %) en las frases de énfasis: con `!`, con palabra clave en un clip corto, o bajo un sello/bigword (máx. uno cada 6 s) · `push` (acercamiento lento) en preguntas y en el CTA · `tight` (114 %) / `wide` (100→103 %) alternados para disimular los jump cuts (siempre ≥ 8 % de diferencia entre clips seguidos) · los clips tapados por fs o b-roll quedan en `wide`.
- El zoom máximo sale de `config.face.top` (no corta la cabeza); default 124 %.
- Para forzar un encuadre: `F(seg, 'punch')` o `F.clip(i, 'wide')` en jobs.js.

## 5 · Dirección creativa, prueba y render
1. `node $SK/scripts/render.js "<work>" --plan` (lista los gráficos, SFX y encuadres con tiempos; detecta palabras no encontradas).
2. **Dirección creativa**: `node $SK/scripts/director.js "<work>"` → informe (`direction.md`) + línea de tiempo (`timeline.png`, mirarla). Revisa que nada compita: dos tarjetas a la vez, tarjetas tapando el b-roll, b-roll bajo una pantalla completa o en el CTA, pantallas completas muy seguidas o muy largas, cara visible < 55 %, tramos de más de 12 s sin ningún evento, golpes muy seguidos, SFX encimados o demasiados, jump cuts sin cambio de encuadre, material de Envato sin licenciar. **Corregir todos los ⚠️** en jobs.js / config.json y repetir 1–2 hasta que quede limpio (o justificar en el LEEME los que se dejan a propósito).
3. `T=end-0.4 node $SK/scripts/render.js "<work>" --test --only='^(?!cap)'` y luego `python3 -I $SK/scripts/sheets.py "<work>"` → **mirar las hojas (imágenes)** y corregir: textos cortados, superposiciones, elementos tapando lo importante del b-roll, timing (que el gráfico termine de armarse antes de salir).
4. Render final (en segundo plano, tarda unos minutos): `node $SK/scripts/render.js "<work>" --only='^(?!cap)'` y después `node $SK/scripts/render.js "<work>" --only='^cap'`. Los SFX se copian a `Assets/SFX` al armar el XML.

## 6 · XML + entrega
- `python3 -I $SK/scripts/build_xml.py "<work>"` y `xmllint --noout <xml>` (también genera el `.srt`).
- **No correr `preview.py`** salvo que el usuario pida explícitamente la vista previa. La revisión de gráficos ya se hizo con las hojas del paso 5; si hay que corregir algo, volver a renderizar solo ese job con `--only='^id$'` y regenerar el XML.
- **Tiempo**: `python3 -I $SK/scripts/timing.py report "<work>"` → tiempo total de procesamiento y desglose por paso (también queda en `<work>/timing.md`).
- Escribir `LEEME.md` en `<NAME>_EDIT/`: cómo importar (Archivo → Importar → XML; no mover la carpeta), tabla de pistas, estructura, qué se sacó, CTAs alternativos con timecodes, **material de Envato** (salida de `envato.py report`, con lo que falte licenciar), resumen de la dirección creativa, **tiempo de procesamiento**, y para revisar (Cmd+Shift+D para crossfades de audio, SRT nativo opcional).
- Responder corto con la ruta del XML: **tiempo total de procesamiento**, duración final, los 3 b-rolls y la música elegidos (y si falta licenciarlos), gráficos destacados, decisiones a revisar (CTA elegido, tomas elegidas).

## Versiones (v2, ajustes)
Si el usuario pide cambios sobre una edición existente: reusar `<NAME>_EDIT/.work`, subir `version` en config.json y apuntar `edit_dir` a `<NAME>_EDIT_v2` (para no pisar la v1), editar segs.json/jobs.js, y repetir desde el paso 3. Arrancar un cronómetro nuevo (`timing.py start`) para la versión. Dejar la versión anterior intacta.

## Notas técnicas
- Compatible con Claude Code y Codex: todas las rutas son relativas a `$SK`; no depende de herramientas propias de ningún agente.
- XML FCP7 (xmeml v4): clipitems a la base de tiempo de la secuencia (30), archivos con su propia `rate` (kling = 24). En macOS, los nombres con tildes suelen estar en NFD: armar las rutas listando el directorio (`os.listdir`), no tipeándolas.
- No usar `rm -rf` con globs relativos (lo bloquea el sistema). Usar carpetas nuevas o rutas absolutas.
- Los MG con grano a pantalla completa pesan (QuickTime Animation); es normal que `Assets/MG` ocupe cientos de MB.
