# Catálogo de escenas (engine/engine.html)

Lienzo 1080×1920. Paleta: `--ink #0E0D0C` · `--paper #F3EEE5` · `--hot #FF5A1F` (naranja) · `--lime #D4FF3A` · `--mute #8C857A`.
Tipografías: Bricolage Grotesque condensada (títulos, mayúsculas), Inter Tight (UI), JetBrains Mono (kickers), Instrument Serif itálica (acentos).
Zonas: gráficos arriba (y 200–1100), subtítulos en y≈1230. Los tiempos `*At` son **segundos locales** de la escena; usar `R(s, W(seg,'palabra'))`.
Pistas: `ov` = superpuesto · `ov2` = superpuesto por encima de otro ov (ej. tarjeta sobre el tracker) · `fs` = pantalla completa (tapa la cara; usar 1–3 s).
Helper `H('texto')` = resaltado naranja dentro de líneas `disp`.

## Tarjetas superpuestas (ov)
| escena | params | uso |
|---|---|---|
| `listCard` | `kick, title?, tsize?, y?, dark?, items:[{t, at, mark:'x'|'check'|'num'|'q', strikeAt?, sw?}]` | listas que se van armando: ✓ virtudes, ✕ errores tachados, 01/02 pasos, ? preguntas |
| `textcard` | `kick, lines:[html], size?, at:[t por línea], y?, dark?` | frase fuerte en 2–4 líneas; usar `H()` en la palabra clave |
| `target` | `kick, a (serif), b (grande), bs?, c, precAt, qAt` | mira/objetivo: "personas correctas", "paciente ideal" |
| `search` | `kick, query, typeAt, pickAt, youSub` | buscador que tipea y te elige ("te tiene que encontrar") |
| `choice` | `youAt, otherAt, pickAt` | el paciente elige al otro profesional |
| `flow` | `kick, nodes:[{t, at}]` | A → B → C vertical |
| `chart` | — | curva de crecimiento "DATOS > OPINIONES" |
| `algo` | `stampAt` | "esperando al algoritmo…" con sello NUNCA MÁS |
| `loop` | `nodes:[{t,at}]×3` | ciclo medir/repetir/mejorar |
| `voice` | `sepanAt, existAt` | ecualizador "QUE SEPAN QUE EXISTÍS" |
| `check10` | `tickAt, goalAt` | checklist de 10 pasos |
| `excuses` | `kick, items:[{t, at}]` | burbujas de excusas que se apilan con contador ×N |
| `scroll` | `stopAt` | teléfono con feed que frena + STOP |
| `name` | `numAt` | GUS PASCANER + contador "+300 profesionales" |
| `hook` | `tags:[2], tagAt:[2], bigAt` | "MARKETING DESDE CERO" (texto fijo, adaptar si se reusa) |
| `stat` | `kick, to (ej 99.9), countEnd, l1` | número gigante que cuenta |
| `sticker` | `kick, text, size?, x?, y?, bg?, aw (1 = sin flecha), ax, ay` | etiqueta inclinada con flecha dibujada; ideal sobre b-roll |
| `stamp` | `kick?, text, at, y?, rot?, color?, size?` | sello que cae y tiembla ("NO LITERAL") |
| `hud` | `tag, kick, text, labAt, flash?` | HUD de rayos X/cámara sobre b-roll (esquinas, REC, scan, texto tipeado) |
| `pensas` | `at:[3 tiempos], noAt` | palabra repetida ×3 + remate (sobre b-roll) |
| `tracker` | `n (1-5), word` | barra I·D·E·A·S fija arriba durante una sección |
| CTAs: `dm` | `opt, msg, reply, replyAt` | chat de DM — CTA "mandame un mensaje" |
| `follow` | `clickAt, opt?, av? (iniciales), stats? [[a,b],[a,b]], title?` | botón Seguir → Siguiendo (por defecto datos de Gus) |
| `comment` | `opt, word, reply, boxKick, boxTitle, boxSub, typeAt, sendAt, classAt, betterAt` | comentá la palabra X |
| `book` | `opt, btnAt, stampAt` | libro método IDEAS + PRECIO RIDÍCULO |

## Pantalla completa (fs)
| escena | params |
|---|---|
| `fsTitle` | `kick, lines:[html], size?, top?, bg?, accent?, color?, kickColor?, kickDot?, marks? (n ✕), marksAt?, sub?` — fondos: ink (default), `bg:'var(--hot)',color:'var(--ink)'` naranja, `bg:'var(--paper)'` |
| `bigword` | `kick, lines:[2], size?, sub?, subAt?` — palabra partida letra por letra ("PREVISI-/BILIDAD", "ESTÁS/JODIDO.") |
| `counter` | `kick, to, countEnd, pillAt, strikeAt` — contador de seguidores tachado |
| `metrics` | `kick, tiles:[{l, v, at, fmt:'k'|'m'}], stampAt` — métricas de vanidad ≠ PACIENTES |
| `calendar` | `qAt` — "EL MES QUE VIENE ¿?" |
| `method` | — revelación "el método IDEAS" |
| `letter` | `n, l, word, wsize?, sub, light?, bg, accent` — intro de cada letra del método |
| `recap` | — IDEAS completo |
| `speed` | — velocímetro "PISAMOS EL ACELERADOR" |

## Subtítulos
Automáticos (un .mov por clip de V1). Palabra activa resaltada; `config.keywords` = palabras clave con color propio.
`config.caption_colors`: **elegir según el color de la ropa** para que el resaltado contraste:
- ropa naranja/cálida → `{"act":"var(--lime)","kwAct":"#fff","kw":"var(--lime)"}`
- ropa verde/fría/neutra → `{"act":"var(--hot)","kwAct":"var(--lime)","kw":"#FFB08A"}`

## Agregar una escena nueva
Escribir `SC.nombre=p=>{ ...construir DOM con h(), ml(), kick()...; return t=>{ ...animar según t... } }` en engine.html antes de `SC.listCard=listCard;`.
Helpers: `P(t,a,d)` progreso 0–1 · `E.expo/back/el/o3/io` easings · `rise(el,t,a)` máscara que sube · `popIn(el,t,a)` · `OV(card)` entrada/salida de tarjeta · `FS(bg,accent)` wipe de pantalla completa · `DUR` duración.
Siempre incluir salida en los últimos 0.3 s. Revisar con `--test` + sheets.py antes del render final.
