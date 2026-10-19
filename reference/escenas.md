# Catálogo de escenas (engine/engine.html)

Lienzo 1080×1920. Paleta: `--ink #0E0D0C` · `--paper #F3EEE5` · `--hot #FF5A1F` (naranja) · `--lime #D4FF3A` · `--mute #8C857A`.
Tipografías: Bricolage Grotesque condensada (títulos, mayúsculas), Inter Tight (UI), JetBrains Mono (kickers), Instrument Serif itálica (acentos).
Zonas: gráficos arriba (y 200–1100), subtítulos en y≈1230. Los tiempos `*At` son **segundos locales** de la escena; usar `R(s, W(seg,'palabra'))`.
Pistas: `ov` = superpuesto · `ov2` = superpuesto por encima de otro ov (ej. tarjeta sobre el tracker) · `fs` = pantalla completa (tapa la cara; usar 1–3 s).
Helper `H('texto')` = resaltado naranja dentro de líneas `disp`.

## Tarjetas superpuestas (ov)
| escena | params | uso |
|---|---|---|
| `listCard` | `kick, title?, tsize?, y?, dark?, skin?, items:[{t, at, mark:'x'|'check'|'num'|'q', strikeAt?, sw?}]` — skins `notebook` `sticky` `ui` `terminal` | listas que se van armando: ✓ virtudes, ✕ errores tachados, 01/02 pasos, ? preguntas |
| `textcard` | `kick, lines:[html], size?, at:[t por línea], y?, dark?, skin?` — skins `kinetic` `highlight` `ticket` (`stub?`) | frase fuerte en 2–4 líneas; usar `H()` en la palabra clave |
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
| `sticker` | `kick, text, size?, x?, y?, bg?, aw (1 = sin flecha), ax, ay, skin?` — skins `tape` `bubble` (`tail:'right'`) | etiqueta inclinada con flecha dibujada; ideal sobre b-roll |
| `stamp` | `kick?, text, at, y?, rot?, color?, size?, skin?` — skin `round` (`ring`, `d`) | sello que cae y tiembla ("NO LITERAL") |
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
| `fsTitle` | `kick, lines:[html], size?, top?, bg?, accent?, color?, kickColor?, kickDot?, marks? (n ✕), marksAt?, sub?, skin?` — fondos: ink (default), `bg:'var(--hot)',color:'var(--ink)'` naranja, `bg:'var(--paper)'` · skins `split` (`bg2?, mid?`) `stack` (`echo?, max?, width?`) `ticker` (`tick?`) |
| `bigword` | `kick, lines:[2], size?, sub?, subAt?` — palabras que entran letra por letra, una o dos por renglón ("ESTÁS/JODIDO."). **Nunca partir una palabra con guion entre renglones** (nada de "PREVISI-/BILIDAD"): la palabra larga va entera en su renglón y el motor achica el tamaño para que entre |
| `counter` | `kick, to, countEnd, pillAt, strikeAt` — contador de seguidores tachado |
| `metrics` | `kick, tiles:[{l, v, at, fmt:'k'|'m'}], stampAt` — métricas de vanidad ≠ PACIENTES |
| `calendar` | `qAt` — "EL MES QUE VIENE ¿?" |
| `method` | — revelación "el método IDEAS" |
| `letter` | `n, l, word, wsize?, sub, light?, bg, accent` — intro de cada letra del método |
| `recap` | — IDEAS completo |
| `speed` | — velocímetro "PISAMOS EL ACELERADOR" |
| `concept` | `at, bg:'ink'\|'hot'\|'paper', seed?, top?, grid:false?, ox?, oy?, scale?, persp?, grain?` + lo que lea tu `concept.js` — **sin texto, 3–4 s** — animación conceptual **nueva para cada video**, programada en `<work>/concept.js` (obligatoria: una de las 2–4 fs). Ver abajo. |

## Subtítulos
Automáticos (un .mov por clip de V1). Palabra activa resaltada; `config.keywords` = palabras clave con color propio.
`config.caption_colors`: **elegir según el color de la ropa** para que el resaltado contraste:
- ropa naranja/cálida → `{"act":"var(--lime)","kwAct":"#fff","kw":"var(--lime)"}`
- ropa verde/fría/neutra → `{"act":"var(--hot)","kwAct":"var(--lime)","kw":"#FFB08A"}`

Estilo de subtítulos (`config.caption_style` > arte.json `"subtitulos"` > brand.json `"captions":{"style":…}` > `box`): string o `{style, size?, case:'upper'|'none', font:'display'|'body'|'serif', dy?}`.
| style | look |
|---|---|
| `box` (default, el de siempre) | caja de color en la palabra activa, Brico 92 px mayúsculas |
| `underline` | subrayado animado bajo la palabra activa |
| `pop` | la palabra activa crece y toma el color, sin caja |
| `karaoke` | la palabra activa se va llenando de color (relleno progresivo) |
| `minimal` | minúsculas, Inter; las palabras clave en serif itálica |
| `stacked` | 2 líneas: la primera chica, la segunda grande |
Todos respetan `caption_colors`, `keywords`, la posición de layout.js (capTop) y se ocultan bajo los MG. Ojo: la skill motion usa `captions` en brand.json para lo suyo (`on/upper/size`); acá solo cuenta si tiene `style`.

## Skins (`skin:` en params, o por escena en arte.json `"skins"`)
Sin skin = el look de siempre (idéntico). Todas usan la paleta (`--ink --paper --hot --lime`) y las fuentes (Brico/Inter/Mono/Serif) de la marca, respetan la cara (avoidFace) y salen en los últimos 0,3 s. Skin desconocida = error al renderizar.
| escena | skin | look |
|---|---|---|
| listCard | `notebook` | hoja rayada con margen, letra serif, tildes/cruces/tachados dibujados a mano |
| listCard | `sticky` | un papelito adhesivo por ítem (2 columnas hasta 4 ítems, 3 si hay más), con cinta |
| listCard | `ui` | panel de app: barra con 3 puntos, filas que entran deslizando, switches que se prenden (✓ lima, ✕ hot) |
| listCard | `terminal` | consola mono que tipea cada ítem con `[OK]` / `[ERROR]` / `[?]` |
| textcard | `kinetic` | sin caja, líneas gigantes alternando paper/hot con sombra dura en tinta |
| textcard | `highlight` | cada línea sobre una franja de marcador que se pinta de izq. a der. |
| textcard | `ticket` | entrada con troquel y línea punteada; `kick` y `stub` en el talón |
| fsTitle | `split` | dos paneles que entran de lados opuestos (mitad de las líneas arriba, resto abajo) |
| fsTitle | `stack` | cada línea llena el ancho, ecos en contorno que sangran por el borde (1–3 palabras cortas) |
| fsTitle | `ticker` | bandas diagonales con el kick repetido en marquesina + el título |
| sticker | `tape` · `bubble` | etiqueta de papel con cinta · globo de diálogo |
| stamp | `round` | sello circular con texto en anillo que gira |

**Movimiento** (`motion:` en params, o arte.json `"motion"`): cambia la entrada de líneas (`rise`) y tarjetas (`OV`) en todas las escenas: `mask` (default: máscara que sube) · `slide` (lateral) · `pop` (rebote) · `type` (revela como tipeo) · `flip` (giro 3D) · `blur` (foco). Uno por video, coherente con el arquetipo.

## Tratamientos de b-roll (`B(clave, seg, inicio, dur, kb, {fx, label, bg, side, w})` o `config.broll[clave].fx`)
| fx | qué hace | en Premiere |
|---|---|---|
| `full` (default) | pantalla completa, como siempre | escala para llenar |
| `push` | Ken Burns también en video (`kb`, default `[100,110]`) | keyframes de escala |
| `phone` · `polaroid` · `circle` · `window` | fondo de marca (`bg:'ink'|'paper'|'hot'`) con un **agujero** donde se ve el b-roll + decoración (teléfono, polaroid con `label` manuscrito, anillo, ventana con etiqueta) y **los subtítulos de ese tramo adentro del marco** | b-roll en V2 escalado/posicionado al agujero (Basic Motion: escala + centro) + MG `bx_NN_<clave>` en la pista de subtítulos (encima del b-roll, debajo de stickers) |
| `pip` | ventanita en la zona libre (la cara sigue a la vista; `side:'left'`, `w` máx.); si no hay ≥ 380 px libres pasa a `window` | escala + centro + MG con borde |
Los marcos cortan con el b-roll (sin salida animada) y no cuentan como MG. Encima de un marco van stickers/sellos igual que sobre un b-roll.

## Gramáticas del concept (elegir una por video: `// GRAMÁTICA:` en concept.js)
| gramática | idea | herramientas |
|---|---|---|
| `trazo` | todo dibujado a mano, imperfecto | `rough(g,pts,r,{close,w,col,jit,pasadas})` → paths para `dash()` · `roughCircle(g,cx,cy,rad,r)` |
| `descentrada` | la figura sangra del borde, mucho aire en el otro lado | params `ox`, `oy`, `scale` del job (p.ej. `ox:260, scale:1.4`) |
| `tipografía` | formas hechas de letras/caracteres (sin texto legible, o UNA palabra gigante si se decide) | `sv('text',…)` con `font-family:Brico` |
| `isométrica` | profundidad, cajas, escaleras, capas | `iso(x,y,z)` · `isoBox(g,x,y,z,w,d,h,[top,izq,der])` · param `persp:'iso'` o `{rx,ry,rz,d}` |
| `collage` | recortes de papel, sombras duras, semitono, grano | `cutout(el,rot)` · `pat(g,'dots'|'lines'|'cross',col)` → `fill:url(#…)` · param `grain:'heavy'` |
| `datos` | diagrama: ejes, puntos, barras con intención (no la "barra que sube") | `sv('line'…)`, `particles()`, `along()` |
| `plana` | la vieja: línea plana centrada (ya usada en todos los videos anteriores: evitar) | — |

## Agregar una escena nueva
Escribir `SC.nombre=p=>{ ...construir DOM con h(), ml(), kick()...; return t=>{ ...animar según t... } }` en engine.html antes de `SC.listCard=listCard;`.
Helpers: `P(t,a,d)` progreso 0–1 · `E.expo/back/el/o3/io` easings · `rise(el,t,a)` máscara que sube · `popIn(el,t,a)` · `OV(card)` entrada/salida de tarjeta · `FS(bg,accent)` wipe de pantalla completa · `DUR` duración.
Siempre incluir salida en los últimos 0.3 s. Revisar con `--test` + sheets.py antes del render final.

## Animación conceptual (`concept`): una nueva por video
No hay motivos prearmados: cada video trae su propia animación en `<work>/concept.js`, que `render.js` carga en el motor. Los 14 motivos viejos están en `reference/concept_ejemplos.js` **solo como referencia técnica** (no copiarlos ni adaptarlos; el director avisa si se reusa código o metáfora).

```js
// IDEA: <qué frase/idea del guion ilustra>
// METÁFORA: <la imagen, en una línea — nueva, no usada antes (node director.js --conceptos)>
// GRAMÁTICA: <trazo | descentrada | tipografía | isométrica | collage | datos — distinta a la de los últimos 3>
// BEATS: 1) planteo … 2) momento clave en `a` (palabra '…') … 3) resolución …
window.CONCEPT=(g,p,a,D,r)=>{
  // g = <svg> 1000×1000 (zona visible ≈ 110–890) · p = params del job · a = momento clave (s locales) · D = duración · r() = azar con semilla
  const core=sv('circle',{cx:500,cy:500,r:60},g,`fill:${HL}`);
  return t=>{ spop(core,t,.1); /* … */ };
};
```
**Colores**: solo `FG` (figura), `HL` (resaltado), `HL2`, `SUB` (líneas tenues): se adaptan al fondo (`bg` ink → crema + naranja, hot → tinta + lima, paper → tinta + naranja) y a la marca.
**Herramientas**: `sv(tag, attrs, padre, css)` crear SVG · `P(t,a,d)` progreso 0–1 · `E.back/el/o3/io/expo` easings · `L(a,b,x)` interpolar · `cl(x)` limitar 0–1 · `spop(el,t,a)` aparecer con rebote · `dash(el,largo,x)` dibujar un trazo · `ripple(g,cx,cy)` onda · `along(path,x)` punto sobre un path · `lerpPt(p,q,x)` · `particles(g,n,r,{r,fill,box})` nube de partículas.
**Checklist**: se entiende sin texto en 3 s · una sola idea, un solo momento fuerte (en `a`, sincronizado con la palabra) · arranca armándose (no aparece todo junto) · se mueve hasta el final (nada congelado) · salida en los últimos 0,3 s · composición según la gramática elegida (centrada solo si es `plana`) · probar con `--test --only='concept' --t=0.3,<at>,end-0.4` y mirar los PNG.
