// ⚠️ SOLO REFERENCIA DE SINTAXIS: no copiar las figuras (director.js avisa si se reusa este código). Cada video dibuja las suyas.
// <work>/ilustra.js = las ilustraciones superpuestas de ESTE video (escena 'ilu', SKILL.md paso 4) y sus figuras compartidas.
// render.js lo carga ANTES de concept.js: window.FIG queda disponible también en window.CONCEPT (así el héroe reaparece en la conceptual).
//
// Contrato: window.ILU.<fig>=(g,p,a,D,r)=>{ …dibujar en g… ; return t=>{ …animar: función pura de t… } }
//   g = <svg> de 1000×1000 (todo visible; el motor lo escala al tamaño del job: w/h) · p = params del job · a = momento clave en s locales (p.at)
//   D = duración · r() = azar con semilla. La entrada y la salida (pop/encogido en los últimos 0,3 s) las hace el motor: la figura solo vive y cambia.
//   Colores: FG (figura), HL (resaltado), HL2, SUB — se adaptan al tono (paper/ink), a la placa (plate) y a la marca. SIN texto (solo p.label).
//   Herramientas: sv, P, E, L, cl, spop, dash, ripple, along, lerpPt, particles, rough, roughCircle, iso, isoBox, pat, cutout (escenas.md).
window.FIG=window.FIG||{};window.ILU=window.ILU||{};
// Figura compartida (el héroe de este video): una pastilla en dos mitades, con parámetros de pose para que "viva" en cada aparición.
// Devuelve los grupos para animarlos desde afuera.
FIG.pastilla=(g,x,y,s)=>{const w=sv('g',{transform:`translate(${x} ${y}) scale(${s})`},g),iz=sv('g',{},w),de=sv('g',{},w);
  sv('path',{d:'M0 -70 H-90 A70 70 0 0 0 -90 70 H0 Z'},iz,`fill:${FG}`);
  sv('path',{d:'M0 -70 H90 A70 70 0 0 1 90 70 H0 Z'},de,`fill:${HL}`);
  sv('path',{d:'M-120 -20 Q-80 -50 -40 -40'},iz,`fill:none;stroke:${SUB};stroke-width:12;stroke-linecap:round`);   // brillo
  return {w,iz,de};};
// Ilustración: la pastilla respira y en `a` se parte en dos mitades que se separan (idea del guion: "la mitad de la dosis").
ILU.pastilla_parte=(g,p,a,D,r)=>{const o=sv('g',{},g),f=FIG.pastilla(o,500,500,1.6),rip=ripple(g,500,500,HL2);
  const chispas=particles(g,10,r,{r:[6,12],fill:HL2,box:[380,380,620,620]});
  return t=>{spop(o,t,.05,.6);                                   // aparece con rebote
    const br=1+Math.sin(t*2.2)*.03;                               // respira (nada quieto)
    const k=E.back(P(t,a,.6))*95;                                 // en `a` cada mitad se va para su lado
    f.iz.setAttribute('transform',`translate(${-k} 0) rotate(${-k*.12}) scale(${br})`);
    f.de.setAttribute('transform',`translate(${k} 0) rotate(${k*.12}) scale(${br})`);
    rip(t,a);
    chispas.forEach((c,i)=>{const q=P(t,a+.05+i*.02,.7),d=E.o3(q)*180;c.el.setAttribute('cx',c.x+Math.cos(c.ph)*d);c.el.setAttribute('cy',c.y+Math.sin(c.ph)*d);c.el.style.opacity=q>0?1-q:0;});};};
// En jobs.js:  J('03_mitad','ilu','ov',s,e,{fig:'pastilla_parte',at:R(s,W(2,'mitad')),w:560,label:'la mitad'});
// En concept.js el héroe vuelve:  const f=FIG.pastilla(g,500,500,2.2); … (y en jobs.js ese concept lleva heroe:true)
