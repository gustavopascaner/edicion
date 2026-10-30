# Recetas de ilustración (`<work>/ilustra.js` y `concept.js`)

Ideas de la skill **motion** (modo libre) llevadas al talking head: mostrar lo que se dice como **imagen**, no como texto. Cada receta es una *técnica* para adaptar a la metáfora de este guion; nunca copiar la figura de otro video (el director compara código y metáforas). Herramientas del motor en `escenas.md` (`sv`, `P`, `E`, `L`, `spop`, `dash`, `ripple`, `along`, `particles`, `rough`, `roughCircle`, `iso`, `isoBox`, `pat`, `cutout`). Todo es función pura de `t` (se renderiza en paralelo y en desorden): nada de estado entre cuadros, azar solo con `r()`.

## Principios (de motion, no negociables)
1. **Mostrar, no escribir.** "Se esconde" = los ojos bajo la cama, no la palabra. Si un MG solo repite lo que el subtítulo ya dice, es una ilustración mal elegida o un MG de más.
2. **Un héroe que reaparece.** Un objeto o personaje ilustrado (la pastilla, la agenda, el paciente, el diente, el reloj) que vuelve 2–3 veces y **se transforma** con el discurso: en una `ilu` al lado de la cara, en la `concept` (vía `window.FIG`) y, si cierra, en el CTA. El hilo visual que une el video.
3. **Una metáfora por idea**, específica de este guion (la silueta punteada = "lo habitual"; la grilla de nueve iguales con uno distinto = "algo cambió"; la hoja que vuela de un lugar a otro = "esa información sirve en la consulta").
4. **Vida.** Nada quieto más de ~2 s: respira (`scale 1±.03`), parpadea, flota, mira hacia lo que pasa. Las tarjetas con `alive:true` flotan solas.
5. **Transiciones con sentido.** La pantalla completa que sigue a una ilustración puede *nacer* de ella: `enter:{kind:'iris',cx,cy}` en la fs, con `cx/cy` donde estaba la figura (match cut).

## Recetas
| | qué cuenta | para ideas como… | técnica |
|---|---|---|---|
| **R01 · Silueta punteada** | la figura se corre y deja su contorno punteado donde estaba | lo habitual vs. el cambio, "ya no está", ausencia | la misma `FIG` dos veces: una con `stroke-dasharray` y sin relleno (`fill:none;stroke:${HL}`), la otra se desplaza con `E.io(P(t,a,.8))` |
| **R02 · Nueve iguales, uno distinto** | grilla 3×3 de la misma figura; en `a` una cambia de pose/color y la rodea un anillo | "algo diferente", detectar la señal, el paciente que no encaja | `for` 3×3 con `FIG(...)`; en `a` esa se escala `E.back` y `roughCircle` alrededor con `dash()` |
| **R03 · Etiquetas que se pegan y se caen** | papelitos se le pegan al héroe y en `a` se tachan y caen girando | prejuicios, "está raro", excusas, mitos | `cutout()` sobre `rect`+`text` cortos (son rótulos, no frases), caída con `P(t,a,.7)` y `rotate` con `r()` |
| **R04 · Hoja que vuela** | una hoja sale de un objeto, viaja por un arco y entra en otro | la información que pasa del paciente a la consulta, derivación, el mensaje que llega | `along(path,x)` sobre un `path` invisible; rotación leve en el viaje; `ripple` al llegar |
| **R05 · Ojo que se abre** | párpado que se abre, pupila que se dilata y mira hacia un punto | observar, prestar atención, "mirá esto", diagnóstico | elipse con `ry` animado = párpado; pupila con `cx/cy` que sigue un objetivo `lerpPt`; brillo `HL2` |
| **R06 · Reloj que acelera** | agujas que giran lento y en `a` se disparan; marcas de velocidad | el tiempo que pasa, "no esperes", urgencia, plazos | `rotate` lineal + `Math.pow(P(t,a,1.2),2)*k`; marcas con `particles` que se alargan |
| **R07 · Camino con huellas** | la figura recorre un camino y deja huellas que van apareciendo | rutina, recorrido, proceso, pasos | `along(path, step)` para las huellas; cada una aparece cuando la figura pasa (`t>=tt`) |
| **R08 · Se parte / se une** | el héroe se divide en dos (o dos mitades encajan) | la mitad de la dosis, compartir, dividir el problema, "juntos" | dos grupos (`iz`, `de`) con `translate(±k)`; `k=E.back(P(t,a,.6))*90` (ver `ejemplo_ilustra.js`) |
| **R09 · Se llena / se vacía** | un recipiente o barra de la figura se llena hasta un nivel y en `a` se derrama o se vacía | acumulación, estrés, "hasta acá", reservas | `clipPath` con `rect` cuyo `y` baja; `particles` que caen con `E.i3` |
| **R10 · Lupa / foco** | un círculo recorre la figura y agranda lo que pasa por abajo; se detiene en `a` | "lo importante es…", revisar, detectar | dos copias de la figura: la grande dentro de un `clipPath` circular que sigue la lupa (`lerpPt`) |
| **R11 · Corazón / pulso vivo** | una forma late con el ritmo del discurso y en `a` cambia de ritmo o color | salud emocional, calma, alerta, estado | `scale(1+.06*Math.max(0,Math.sin(t*ω)))`; `ω` cambia en `a`; `ripple` por latido |
| **R12 · Se transforma** | el héroe pasa de una forma a otra (la receta se vuelve calendario, el problema se vuelve plan) | antes/después, cambio de estado, resultado | dos `path` con el mismo número de nodos y `d` interpolado por `L()` en cada punto; o `cutout` que gira y cambia de cara |

## Dónde va cada cosa
- **`ilu` (ov, al lado de la cara)**: la metáfora de ese tramo, 2–5 s, sin texto (o un `label`). Entra y sale sola (motor); la figura respira y cambia en `at`. Con `plate:'paper'|'hot'|'ink'` si el video de fondo es muy cargado.
- **`concept` (fs)**: la metáfora madre del video, sin texto, 3–4 s, con el héroe de `FIG` si corresponde (`heroe:true` en el job).
- **CTA**: si el héroe cierra la historia (la hoja llega al chat, el reloj se detiene), que aparezca ahí también (`heroe:true`).
- **Match cut**: `J('07_remate','fsTitle','fs',s,e,{…,enter:{kind:'iris',cx:540,cy:620}})` justo después de una `ilu` centrada en (540, 620).
