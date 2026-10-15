// Decisión editorial de ubicación: dónde van los subtítulos y los motion graphics para NO pisar la cara.
// Usa config.face (face.js) y el zoom máximo de los reencuadres: la cara "ocupa" lo que ocupa con el zoom más fuerte.
// Devuelve {face:[x0,y0,x1,y1], zones:[[y0,y1],…] libres arriba/abajo, capTop, capH, capPos:'abajo'|'arriba', note}
const W=1080,H=1920,TOP_SAFE=110,BOT_SAFE=H-280,GAP=40,CAP_H=210,CAP_DEFAULT=1230;
module.exports=cfg=>{
  const f=cfg.face;
  if(!f||f.bottom==null)return {face:null,zones:[],capTop:CAP_DEFAULT,capH:CAP_H,capPos:'abajo',note:'sin datos de cara (correr face.js): subtítulos en la posición estándar'};
  const MAXS=cfg.max_zoom||(f.top!=null?Math.min(1.3,0.47/Math.max(.05,0.5-f.top)):1.24),S=Math.max(1,Math.min(1.3,MAXS));
  const z=(v,c,s)=>c+(v-c)*s;   // el zoom escala desde el centro del cuadro
  const x0=Math.min(f.left??.2,z(f.left??.2,.5,S))*W,x1=Math.max(f.right??.8,z(f.right??.8,.5,S))*W;
  const y0=Math.min(f.top,z(f.top,.5,S))*H,y1=Math.max(f.bottom,z(f.bottom,.5,S))*H;
  const face=[Math.round(Math.max(0,x0)),Math.round(Math.max(0,y0)),Math.round(Math.min(W,x1)),Math.round(Math.min(H,y1))];
  const above=[TOP_SAFE,Math.round(face[1]-GAP)],below=[Math.round(face[3]+GAP),BOT_SAFE];
  const zones=[above,below].filter(r=>r[1]-r[0]>0);
  let capTop,capPos;
  if(below[1]-below[0]>=CAP_H){capPos='abajo';capTop=Math.min(Math.max(CAP_DEFAULT,below[0]),below[1]-CAP_H);}
  else if(above[1]-above[0]>=CAP_H){capPos='arriba';capTop=above[1]-CAP_H;}   // pegados arriba de la cabeza, cerca de la mirada
  else{capPos=(below[1]-below[0])>=(above[1]-above[0])?'abajo':'arriba';capTop=capPos==='abajo'?below[0]:Math.max(TOP_SAFE,above[1]-CAP_H);}
  const low=f.top>.33;
  const note=`${low?'cara baja (mucho aire arriba)':'cara en posición normal'} → subtítulos ${capPos} (y≈${capTop}); MG que pisen la cara se mueven a la zona libre ${
    zones.map(r=>`${r[0]}–${r[1]}`).join(' / ')||'(no hay)'}`;
  return {face,zones,capTop,capH:CAP_H,capPos,note};
};
