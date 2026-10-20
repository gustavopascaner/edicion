// Dirección creativa unificada: revisa que video, b-roll, gráficos, subtítulos, SFX y música no compitan entre sí.
// uso: node director.js <workdir>   (después de `render.js --plan`) · node director.js --conceptos (historial de animaciones conceptuales)
//      node director.js --huellas (estética de los últimos 10 videos: arquetipo, escenas, skins, subtítulos, b-roll) · --sembrar <work>… (solo registra la huella, no escribe nada en el proyecto)
// → imprime el informe, lo guarda en <workdir>/direction.md y dibuja la línea de tiempo en <workdir>/timeline.png
const fs=require('fs'),path=require('path'),{CHROME,fileURL,logTime}=require('./platform.js');
// Historial de animaciones conceptuales (una por video, nunca recicladas): ~/.config/edicion/conceptos.jsonl
const os=require('os'),crypto=require('crypto');
const HDIR=process.env.EDICION_HIST||path.join(os.homedir(),'.config','edicion'),HIST=path.join(HDIR,'conceptos.jsonl'),HUE=path.join(HDIR,'huellas.jsonl');
const readJL=f=>fs.existsSync(f)?fs.readFileSync(f,'utf8').split('\n').filter(Boolean).map(l=>{try{return JSON.parse(l)}catch{return null}}).filter(Boolean):[];
const readHist=()=>readJL(HIST),writeJL=(f,a)=>{fs.mkdirSync(path.dirname(f),{recursive:true});fs.writeFileSync(f,a.map(e=>JSON.stringify(e)).join('\n')+'\n');};
// ── Huella estética de un video (anti-repetición entre videos): ~/.config/edicion/huellas.jsonl ──
const BGN=v=>{v=String(v||'ink');return /hot/.test(v)?'hot':/paper/.test(v)?'paper':/lime/.test(v)?'lime':/ink/.test(v)?'ink':v.replace(/\s/g,'');};
// gramáticas visuales del concept (SKILL.md 4): la vieja "línea plana centrada" es 'plana' (todos los concept anteriores al cambio)
const GRAMS=[['trazo',/trazo|mano|rough|boceto/],['descentrada',/descentr|sangr|borde|recort.*cuadro/],['tipografia',/tipogr|letra|palabra/],['isometrica',/isom|profund|perspect|3d/],['collage',/foto|collage|recort|grano|papel/],['datos',/dato|diagrama|grafic|esquema/],['plana',/plana|centrad|l[ií]nea/]];
const gramKey=x=>{x=String(x||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');return (GRAMS.find(([,re])=>re.test(x))||[x.split(/\W+/)[0]||''])[0];};
const hdr=(src,k)=>(src.match(new RegExp('^\\s*//\\s*'+k+'\\s*:\\s*(.+)$','mi'))||[])[1]?.trim()||'';
function huella(WD){const rj=f=>JSON.parse(fs.readFileSync(path.join(WD,f))),ex=f=>fs.existsSync(path.join(WD,f));
  const cfg=rj('config.json'),jobs=rj('jobs.json'),{broll}=rj('broll.json'),fr=ex('framing.json')?rj('framing.json'):[],art=ex('arte.json')?rj('arte.json'):{};
  const mg=jobs.filter(j=>j.track!=='cap').sort((a,b)=>a.start-b.start);
  let cs=cfg.caption_style??art.subtitulos;if(cs==null)try{cs=require('./brand.js').captionStyle(require('./brand.js').loadBrand(cfg.brand));}catch{}
  const cj=ex('concept.js')?fs.readFileSync(path.join(WD,'concept.js'),'utf8'):'',cc=mg.find(j=>j.scene==='concept');
  return {video:cfg.name,fecha:new Date().toISOString().slice(0,10),marca:cfg.brand?path.basename(String(cfg.brand)):'editorial',arquetipo:art.arquetipo||cfg.arquetipo||'',firma:art.firma||'',
    seq:mg.map(j=>j.scene+':'+j.track),fs:mg.filter(j=>j.track==='fs').map(j=>BGN(j.p.bg)),skins:[...new Set(mg.map(j=>j.scene+'.'+(j.p.skin||'default')))],
    motion:[...new Set(mg.map(j=>j.p.motion||art.motion||'mask'))],subs:(typeof cs==='string'?cs:cs&&cs.style)||'box',broll:broll.map(b=>b.fx||'full'),
    encuadres:fr.map(f=>f.mode).join(' '),gramatica:cc?(hdr(cj,'GRAM[AÁ]TICA')?gramKey(hdr(cj,'GRAM[AÁ]TICA')):'plana'):'',concept_bg:cc?BGN(cc.p.bg):''};}
const lcs=(a,b)=>{const d=Array(b.length+1).fill(0);for(const x of a){let pv=0;for(let j=1;j<=b.length;j++){const t=d[j];d[j]=x===b[j-1]?pv+1:Math.max(d[j],d[j-1]);pv=t;}}return d[b.length];};
const seqS=(a,b)=>a.length||b.length?lcs(a,b)/Math.max(a.length,b.length):1;
const jac=(a,b)=>{const A=new Set(a),B=new Set(b);if(!A.size&&!B.size)return 1;let i=0;A.forEach(x=>B.has(x)&&i++);return i/(A.size+B.size-i);};
// similitud 0–1: secuencia de escenas (LCS) 35 % · skins 20 % · fondos de las fs 10 % · subtítulos 10 % · b-roll 10 % · arquetipo 10 % · movimiento 5 %
function simil(h,o){const p={escenas:seqS(h.seq,o.seq||[]),skins:jac(h.skins,o.skins||[]),fondos:seqS(h.fs,o.fs||[]),subtítulos:+(h.subs===(o.subs||'box')),
    'b-roll':jac(h.broll,o.broll||[]),arquetipo:+((h.arquetipo||'')===(o.arquetipo||'')),movimiento:jac(h.motion,o.motion||['mask'])};
  const Wt={escenas:.35,skins:.2,fondos:.1,subtítulos:.1,'b-roll':.1,arquetipo:.1,movimiento:.05};return {s:Object.keys(Wt).reduce((a,k)=>a+Wt[k]*p[k],0),p};}
if(process.argv[2]==='--huellas'){const h=readJL(HUE).slice(-10);
  console.log(h.length?'Estética de los últimos videos (elegir un arquetipo distinto al de los últimos 3 de la misma marca):\n'+h.map(e=>`  ${e.fecha}  ${e.video.padEnd(20)} ${String(e.marca).padEnd(16)} arq:${(e.arquetipo||'—').padEnd(12)} subs:${e.subs.padEnd(9)} fs:${e.fs.join('/')||'—'}  b-roll:${[...new Set(e.broll)].join('/')||'—'}  concept:${e.gramatica||'—'}/${e.concept_bg||'—'}\n      ${e.seq.map(x=>x.split(':')[0]).join(' > ')}  ·  skins: ${e.skins.filter(x=>!/\.default$/.test(x)).join(', ')||'todas default'}`).join('\n'):'Todavía no hay huellas (se guardan al correr director.js en cada video).');
  process.exit(0);}
if(process.argv[2]==='--sembrar'){let H=readJL(HUE);for(const w of process.argv.slice(3).filter(w=>fs.existsSync(path.join(w,'jobs.json'))).sort((a,b)=>fs.statSync(path.join(a,'jobs.json')).mtimeMs-fs.statSync(path.join(b,'jobs.json')).mtimeMs)){try{const h=huella(path.resolve(w));H=H.filter(e=>e.video!==h.video);H.push(h);console.log('huella:',h.video,h.seq.length,'escenas');}catch(e){console.log('✗',w,e.message);}}writeJL(HUE,H);process.exit(0);}
if(process.argv[2]==='--conceptos'){const h=readHist();
  console.log(h.length?'Animaciones conceptuales ya usadas (no repetir la metáfora; [gramática·fondo]: elegir una gramática distinta a la de los últimos 3):\n'+h.slice(-20).map(e=>`  ${e.date}  ${e.video.padEnd(22)} [${e.gramatica||'plana'}·${e.bg||'ink'}] ${e.metafora}  ← ${e.idea}`).join('\n'):'Todavía no hay animaciones conceptuales en el historial.');
  process.exit(0);}
const WD=path.resolve(process.argv[2]),rd=f=>JSON.parse(fs.readFileSync(path.join(WD,f)));
const cfg=rd('config.json'),edl=rd('edl.json'),jobs=rd('jobs.json'),{broll}=rd('broll.json');
const sfx=fs.existsSync(path.join(WD,'sfx.json'))?rd('sfx.json'):[],framing=fs.existsSync(path.join(WD,'framing.json'))?rd('framing.json'):[];
const FPS=cfg.fps||30,T=edl.total/FPS,t0=Date.now();
const ov=jobs.filter(j=>j.track==='ov'),ov2=jobs.filter(j=>j.track==='ov2'),fsj=jobs.filter(j=>j.track==='fs'),caps=jobs.filter(j=>j.track==='cap');
const B=broll.map(b=>({...b,end:b.start+b.dur}));
const ovl=(a,b)=>Math.max(0,Math.min(a.end,b.end)-Math.max(a.start,b.start));
const f2=x=>x.toFixed(1)+'s';
const ok=[],warn=[];const W=(m)=>warn.push(m),O=(m)=>ok.push(m);
// ── Visual ──
const OVER_BROLL=/sticker|hud|stamp|pensas|tracker/;
for(let i=0;i<ov.length;i++)for(let k=i+1;k<ov.length;k++)if(ovl(ov[i],ov[k])>0.1)W(`Dos tarjetas a la vez: ${ov[i].id} y ${ov[k].id} (${f2(ovl(ov[i],ov[k]))}). Mover una a ov2 solo si es un tracker, o separarlas.`);
for(const b of B){
  for(const f of fsj)if(ovl(b,f)>0.1)W(`B-roll "${b.src}" (${f2(b.start)}) queda tapado por la pantalla completa ${f.id}: moverlo.`);
  for(const j of ov)if(ovl(b,j)>0.3&&!OVER_BROLL.test(j.scene))W(`La tarjeta ${j.id} (${j.scene}) tapa el b-roll "${b.src}" en ${f2(Math.max(b.start,j.start))}: sobre b-roll usar sticker/hud/stamp o correr el b-roll.`);
  if(b.dur<1.2||b.dur>4.5)W(`B-roll "${b.src}" dura ${f2(b.dur)}: ideal 1,5–4 s.`);
  for(const f of fsj)if(Math.abs(b.start-f.end)<0.3||Math.abs(f.start-b.end)<0.3)W(`B-roll "${b.src}" pegado a la pantalla completa ${f.id}: dejar ≥ 0,3 s de cara entre ambos o unirlos a propósito.`);}
const lastSeg=Math.max(...edl.clips.map(c=>c.seg)),cta=edl.clips.find(c=>c.seg===lastSeg).tl_in/FPS;
for(const b of B)if(b.start>=cta-0.1)W(`B-roll "${b.src}" cae en el CTA final: dejar la cara a cámara en el cierre.`);
if(B.length&&B.length<2)W(`Hay ${B.length} b-roll: el objetivo son 2–4 momentos repartidos (inicio, medio, antes del CTA).`);
{const ev=B.filter(b=>((cfg.broll||{})[b.src]||{}).envato).length;if(ev>4)W(`Hay ${ev} b-rolls de Envato: el objetivo son 2–4; quedarse con los que más amplían lo que se dice.`);}
if(B.length>=2){const s=B.map(b=>b.start).sort((a,b)=>a-b);if(s[s.length-1]-s[0]<T*0.35)W('Los b-rolls están amontonados: repartirlos a lo largo del video.');}
for(const f of fsj){const d=f.end-f.start;if(f.scene==='concept'){if(d<2.8||d>4.6)W(`Pantalla conceptual ${f.id} dura ${f2(d)}: ideal 3–4 s.`);}else if(d<0.8||d>3.6)W(`Pantalla completa ${f.id} dura ${f2(d)}: ideal 1–3 s.`);}
{const bgs=fsj.map(f=>BGN(f.p.bg)),dk=bgs.filter(b=>b==='ink').length;if(dk>0&&dk/bgs.length>0.34)W(`Demasiados fondos oscuros: ${dk} de ${bgs.length} pantallas completas en ink. Predominan los claros (paper), algún hot y el ink solo eventualmente (máx. 1 de cada 3); no repetir el mismo fondo seguido.`);}
{const cc=fsj.filter(f=>f.scene==='concept');
 if(!cc.length)W('Falta la pantalla conceptual sin texto (escena "concept", 3–4 s): una de las 3 pantallas completas tiene que ilustrar un concepto con una animación nueva (concept.js).');
 else if(cc.some(f=>f.p.motif))W(`Pantalla conceptual reciclada (motivo viejo "${cc.find(f=>f.p.motif).p.motif}"): diseñar y programar una animación nueva para este video en concept.js.`);
 else{const cj=path.join(WD,'concept.js');
  if(!fs.existsSync(cj))W('Falta concept.js: la animación conceptual se programa desde cero para cada video.');
  else{const src=fs.readFileSync(cj,'utf8'),hd=k=>(src.match(new RegExp('^\\s*//\\s*'+k+'\\s*:\\s*(.+)$','mi'))||[])[1]?.trim()||'';
   const idea=hd('IDEA'),met=hd('MET[AÁ]FORA'),beats=hd('BEATS'),gram=hd('GRAM[AÁ]TICA'),gk=gram?gramKey(gram):'',cbg=BGN(cc[0].p.bg);
   if(!gram)W('concept.js no declara la gramática visual (// GRAMÁTICA: trazo | descentrada | tipografía | isométrica | collage | datos): elegir una distinta a la de los últimos videos.');
   if(!idea||!met||!beats)W('concept.js no tiene el encabezado completo (// IDEA: … // METÁFORA: … // BEATS: …): escribir la idea antes de programarla.');
   const code=src.replace(/\/\/.*$/gm,'').replace(/\/\*[\s\S]*?\*\//g,'').replace(/\s+/g,''),hash=crypto.createHash('sha1').update(code).digest('hex').slice(0,12);
   const legacy=path.join(__dirname,'..','reference','concept_ejemplos.js');
   if(fs.existsSync(legacy)){const lc=fs.readFileSync(legacy,'utf8').replace(/\/\/.*$/gm,'').replace(/\s+/g,'');
     const copied=lc.split(/MOT\.\w+=/).slice(1).map(b=>b.slice(0,100)).filter(b=>b.length>=100&&code.includes(b));
     if(copied.length)W('concept.js copia código de un motivo viejo de concept_ejemplos.js: la animación tiene que ser nueva.');}
   const nW=warn.length,prev=readHist().filter(e=>e.video!==cfg.name);
   const dup=prev.find(e=>e.hash===hash);if(dup)W(`concept.js es idéntico al de "${dup.video}" (${dup.date}): diseñar una animación nueva.`);
   const stop=new Set('de la el los las un una que con por para en y o a se al del sus su lo como mas más'.split(' '));
   const kw=x=>new Set(x.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').split(/[^a-z]+/).filter(w=>w.length>3&&!stop.has(w)));
   const last3=prev.slice(-3);if(gk&&last3.some(e=>(e.gramatica||'plana')===gk))W(`La gramática "${gk}" ya se usó en ${last3.filter(e=>(e.gramatica||'plana')===gk).map(e=>e.video).join(', ')}: elegir otra (node director.js --conceptos).`);
   if(last3.length>=2&&last3.slice(-2).every(e=>(e.bg||'ink')===cbg))W(`El fondo "${cbg}" de la conceptual se repite con los 2 últimos videos: probar ${cbg==='ink'?'paper o hot':'otro'}.`);
   const mk=kw(met);for(const e of prev.slice(-10)){const rep=[...kw(e.metafora||'')].filter(w=>mk.has(w));if(rep.length>=2)W(`La metáfora se parece a la de "${e.video}" (${e.metafora}): buscar otra imagen.`);}
   if(warn.length===nW)O(`Pantalla conceptual nueva (${gk||'sin gramática'} · fondo ${cbg}): ${met||'(sin metáfora)'} — ${idea||'(sin idea)'}.`);
   if(idea&&met){const h=readHist().filter(e=>e.video!==cfg.name);h.push({video:cfg.name,date:new Date().toISOString().slice(0,10),idea,metafora:met,hash,...(gk?{gramatica:gk}:{}),bg:cbg});writeJL(HIST,h);}}}}
const fss=fsj.map(f=>f.start).sort((a,b)=>a-b);
for(let i=1;i<fss.length;i++)if(fss[i]-fss[i-1]<6)W(`Pantallas completas muy seguidas (${f2(fss[i-1])} y ${f2(fss[i])}): espaciarlas ≥ 6 s.`);
// pantallas completas: objetivo 2–4 (config.fs_min / fs_max) · MG superpuestos: máximo config.mg_max (default 3; con 2 alcanza si el video es corto)
const FSM=cfg.fs_max??4,FSN=Math.min(cfg.fs_min??2,FSM),MGM=cfg.mg_max??3,nOv=ov.length+ov2.length;
(fsj.length>FSM?W:O)(`Pantallas completas: ${fsj.length} (objetivo ${FSN}–${FSM})${fsj.length>FSM?' — sobran: quedarse con los remates más fuertes':''}.`);
if(T>25&&fsj.length<FSN)W(`Hay ${fsj.length} pantalla(s) completa(s): el objetivo es ${FSN}–${FSM} (los remates más fuertes, repartidos, una conceptual).`);
(nOv>MGM?W:O)(`Motion graphics superpuestos: ${nOv} (máximo ${MGM})${nOv>MGM?' — sobran: dejar solo los que más suman y que el resto lo cuenten los subtítulos':''}.`);
const capOver=caps.flatMap(c=>(c.p.groups||[]).map(g=>({start:c.start+g.s,end:c.start+g.e}))).filter(g=>[...ov,...ov2,...fsj].some(j=>ovl(g,j)>0.05));
(capOver.length?W:O)(capOver.length?`Subtítulos visibles debajo de un motion graphic en ${capOver.map(g=>f2(g.start)).join(', ')}: volver a correr render.js.`:'Subtítulos ocultos mientras hay motion graphics: no compiten.');
// cara visible y "aire"
const step=0.1;let face=0,clean=0,idle=0,maxIdle=0,idleAt=0;
const evs=[...jobs.filter(j=>j.track!=='cap').map(j=>j.start),...B.map(b=>b.start),...framing.filter(f=>/punch|snap/.test(f.mode)).map(f=>f.tl_in/FPS)].sort((a,b)=>a-b);
for(let t=0;t<T;t+=step){const covered=fsj.some(f=>t>=f.start&&t<f.end)||B.some(b=>b.fx!=='pip'&&t>=b.start&&t<b.end);
  if(!covered)face+=step;if(!covered&&!ov.some(j=>t>=j.start&&t<j.end))clean+=step;}
for(let i=0;i<=evs.length;i++){const a=i?evs[i-1]:0,b=i<evs.length?evs[i]:T;if(b-a>maxIdle){maxIdle=b-a;idleAt=a;}}
const pf=face/T*100,pc=clean/T*100;
(pf<50?W:O)(`Cara a cámara visible el ${pf.toFixed(0)}% del video${pf<50?' (poca: la persona tiene que sostener el video, objetivo ≥ 50%)':''}.`);
(pc<5?W:O)(`Cara sin ningún gráfico encima: ${pc.toFixed(0)}%${pc<5?' (muy cargado: dejar respirar 1–2 tramos cortos, por ejemplo justo después de un remate)':''}.`);
(maxIdle>15?W:O)(`Tramo más largo sin ningún evento visual: ${f2(maxIdle)} desde ${f2(idleAt)}${maxIdle>15?' (se vuelve monótono: sumar un punch-in o un b-roll)':''}.`);
if(!evs.length||evs[0]>1.0)W('Nada visual en el primer segundo: el gancho necesita texto o movimiento desde el arranque.');
// ── Sonido ──
const hits=sfx.filter(x=>x.cat==='hit');for(let i=1;i<hits.length;i++)if(hits[i].at-hits[i-1].at<4)W(`Dos golpes (hit) a menos de 4 s (${f2(hits[i-1].at)} y ${f2(hits[i].at)}): pierden fuerza.`);
for(let i=1;i<sfx.length;i++)if(sfx[i].at-sfx[i-1].at<0.25&&sfx[i].cat!=='build'&&sfx[i-1].cat!=='build')W(`SFX encimados en ${f2(sfx[i].at)}: ${sfx[i-1].id} + ${sfx[i].id}.`);
const SMAX=cfg.sfx_max??5;(sfx.length>SMAX?W:O)(`SFX: ${sfx.length} en toda la edición (máximo ${SMAX})${sfx.length>SMAX?' — sacar los menos importantes':''}: ${sfx.map(x=>x.id+' '+f2(x.at)).join(' · ')}.`);
for(const x of sfx)if(x.at<(cfg.sfx_start??1.5))W(`SFX ${x.id} en ${f2(x.at)}: el video no tiene que arrancar con un efecto (nada antes de ${cfg.sfx_start??1.5} s).`);
for(let i=1;i<sfx.length;i++)if(sfx[i].at-sfx[i-1].at<3)W(`SFX muy cerca (${f2(sfx[i-1].at)} y ${f2(sfx[i].at)}): separarlos ≥ 3 s para que sea sutil.`);
{const CATL=JSON.parse(fs.readFileSync(path.join(__dirname,'..','assets','sfx','catalog.json'))),LV=CATL.levels||{},VOICE=cfg.voice_lufs??(()=>{try{return JSON.parse(fs.readFileSync(path.join(WD,'conform.json'))).voice_lufs}catch(e){}})()??LV.voice_lufs??-16,REFPK=cfg.sfx_ref_peak??(VOICE+(LV.voice_crest_db??12));
 const cnt={};for(const x of sfx)cnt[x.id]=(cnt[x.id]||0)+1;
 for(const [id,n] of Object.entries(cnt))if(n>1)W(`El sonido "${id}" suena ${n} veces en la misma edición: repetirlo cansa (salvo que sea un guiño a propósito). Dejar que rote o pedir otro id.`);
 for(const x of sfx){const m=CATL.sounds[x.id]||{},pk=x.peak_db??(x.gain>0&&m.tp!=null?20*Math.log10(x.gain)+m.tp:null);
  if(pk!=null&&pk>REFPK-8)W(`SFX ${x.id} en ${f2(x.at)}: pico ${pk.toFixed(1)} dBFS, solo ${(REFPK-pk).toFixed(1)} dB por debajo de los picos de la voz (lo sutil es 10–14 dB): bajar su gain${pk>-3?' — CASI CLIPEA, revisar ya':''}.`);
  const c=CATL.categories[x.cat]||{};
  if(c.auto===false)(x.auto?W:O)(x.auto?`SFX literal "${x.id}" (${x.cat}) en ${f2(x.at)} salió AUTOMÁTICO: los literales solo van a mano cuando lo dicho/visto coincide.`:`SFX literal "${x.id}" (${x.cat}) en ${f2(x.at)}: confirmar que lo que se dice o se ve en ese momento coincide (si no, sacarlo).`);
  if(x.dur>3&&x.cat!=='build')W(`SFX ${x.id} en ${f2(x.at)} dura ${x.dur.toFixed(1)} s: puede tapar palabras (cortarlo con {dur:..}).`);
  if(m.anchor!=null&&x.anchor!=null&&Math.abs(m.anchor-x.anchor)>.02)W(`SFX ${x.id}: el anchor de sfx.json (${x.anchor}) no coincide con el del catálogo (${m.anchor}): volver a correr render.js.`);}
 if(sfx.length){const rl=sfx.filter(x=>x.gain_db!=null&&x.peak_db!=null);if(rl.length)O(`Niveles SFX: ${rl.map(x=>x.gain_db+' dB').join(' · ')} (pico ${Math.max(...rl.map(x=>x.peak_db))} dBFS; voz de referencia ${VOICE} LUFS).`);
  try{const hp=process.env.EDICION_SFXHIST||path.join(os.homedir(),'.config','edicion','sfx_hist.jsonl'),H=fs.readFileSync(hp,'utf8').split('\n').filter(Boolean).map(l=>JSON.parse(l)).filter(h=>h.video!==cfg.name).slice(-3);
   for(const h of H){const same=sfx.filter(x=>(h.ids||[]).includes(x.id)).length;if(sfx.length>=3&&same/sfx.length>=.6)W(`${same} de ${sfx.length} SFX son los mismos que en "${h.video}": variar (sfx_hist.jsonl).`);}}catch{}}}
const M=cfg.music&&typeof cfg.music==='object'?cfg.music:null;
if(M){if((M.envato||{}).status==='preview')W('La música es la vista previa con marca de agua de Envato: falta licenciarla.');if((M.envato||{}).status==='pending')W('La música de Envato todavía no se descargó: licenciar y correr envato.py collect.');O(`Música: pareja en ${M.bed_gain??.08} todo el video, con fade-out final (sin subir en el gancho ni en el cierre).`);}
else if(cfg.music)O('Música colocada a mano (X).');else W('Sin música de fondo.');
for(const b of B){const m=(cfg.broll||{})[b.src]||{};if((m.envato||{}).status==='preview')W(`B-roll "${b.src}" es la vista previa con marca de agua: falta licenciarlo.`);if((m.envato||{}).status==='pending')W(`B-roll "${b.src}" de Envato todavía no se descargó: licenciar y correr envato.py collect.`);}
// ── Cámara ──
const modes={};framing.forEach(f=>modes[f.mode]=(modes[f.mode]||0)+1);
if(framing.length)O('Encuadres: '+Object.entries(modes).map(([k,v])=>`${k} ×${v}`).join(' · ')+'.');
for(let i=1;i<framing.length;i++){const a=framing[i-1],b=framing[i];if(Math.abs(a.s1-b.s0)<6&&!(a.mode==='wide'&&b.mode==='wide'&&(a.s0!==a.s1)))W(`Jump cut sin cambio de encuadre entre los clips ${a.i} y ${b.i} (${a.s1}% → ${b.s0}%).`);}
// ── Variedad estética (huellas de los últimos videos) ──
{const art=fs.existsSync(path.join(WD,'arte.json'))?rd('arte.json'):null,h=huella(WD),all=readJL(HUE).filter(e=>e.video!==cfg.name),prev=all.slice(-5);
 if(!art)W('Falta <work>/arte.json (paso 4-pre · dirección de arte): arquetipo, firma y momentos distintivos de ESTE video.');
 else{if(!art.arquetipo)W('arte.json no tiene "arquetipo".');if(!art.firma)W('arte.json no tiene "firma" (un recurso visual que se repite 2–3 veces).');
  const same=all.filter(e=>e.marca===h.marca).slice(-3);if(art.arquetipo&&same.some(e=>e.arquetipo===art.arquetipo))W(`El arquetipo "${art.arquetipo}" ya se usó en ${same.filter(e=>e.arquetipo===art.arquetipo).map(e=>e.video).join(', ')} (misma marca): elegir otro (node director.js --huellas).`);}
 let best=null;for(const o of prev){const r=simil(h,o),eff=r.s*(o.marca===h.marca?1:.85);if(!best||eff>best.eff)best={o,eff,r};
  if(eff>=.6){const top=Object.entries(r.p).filter(([,v])=>v>=.7).map(([k])=>k).join(', ');W(`Se parece ${Math.round(r.s*100)} % a "${o.video}" (${o.marca}${o.marca===h.marca?', misma marca':''}): coinciden ${top||'muchas cosas'}. Cambiar skins, subtítulos, tratamiento del b-roll o el orden de las escenas.`);}}
 if(best&&best.eff<.6)O(`Estética distinta de los últimos videos (lo más parecido: "${best.o.video}", ${Math.round(best.r.s*100)} %).`);
 if(h.skins.every(x=>/\.default$/.test(x))&&h.subs==='box'&&h.broll.every(x=>x==='full'))W('Todo en el look de siempre (sin skins, subtítulos box, b-roll a pantalla completa): aplicar la dirección de arte del paso 4-pre.');
 writeJL(HUE,[...all,h]);}
const md=['# Dirección creativa','','## Para corregir',...(warn.length?warn.map(x=>'- ⚠️ '+x):['- Nada: todo convive bien.']),'','## Bien',...ok.map(x=>'- ✓ '+x),''].join('\n');
fs.writeFileSync(path.join(WD,'direction.md'),md);console.log(md);
// ── Línea de tiempo (PNG) ──
const PX=1500/T,lane=(y,h,items,col,lab)=>items.map(x=>`<div class=b style="left:${120+x.a*PX}px;top:${y}px;width:${Math.max(2,(x.b-x.a)*PX)}px;height:${h}px;background:${x.c||col}" title="${x.l||''}">${(x.b-x.a)*PX>40?(x.l||''):''}</div>`).join('')+`<div class=lab style="top:${y}px">${lab}</div>`;
const FC={wide:'#555',push:'#7a7',tight:'#4a7fd8',punch:'#FF5A1F',snap:'#D4FF3A',pull:'#999'};
const SC={hit:'#FF5A1F',whoosh:'#4ac',pop:'#ddd',ding:'#D4FF3A',error:'#f44',click:'#aaa',build:'#c6f',glitch:'#f0f',zoom:'#ff0'};
let html=`<html><body style="margin:0;background:#111;font:12px Helvetica;color:#ddd;width:1640px;height:430px;position:relative">
<style>.b{position:absolute;border-radius:3px;overflow:hidden;white-space:nowrap;font-size:10px;color:#000;padding-left:2px;box-sizing:border-box}.lab{position:absolute;left:8px;width:105px;color:#aaa}</style>`;
html+=lane(20,26,framing.map(f=>({a:f.tl_in/FPS,b:f.tl_out/FPS,c:FC[f.mode],l:f.mode})),'#555','Cámara');
html+=lane(56,26,B.map(b=>({a:b.start,b:b.end,l:b.src})),'#3b8','B-roll');
html+=lane(92,26,ov.map(j=>({a:j.start,b:j.end,l:j.id})),'#F3EEE5','Gráficos');
html+=lane(122,14,ov2.map(j=>({a:j.start,b:j.end,l:j.id})),'#cbb','Gráficos 2');
html+=lane(146,26,fsj.map(j=>({a:j.start,b:j.end,l:j.id})),'#FF5A1F','Pantalla compl.');
html+=lane(182,12,caps.map(j=>({a:j.start,b:j.end})),'#666','Subtítulos');
html+=lane(204,26,sfx.map(x=>({a:x.at,b:x.at+0.12,c:SC[x.cat]||'#fff',l:''})),'#fff','SFX');
html+=sfx.map(x=>`<div style="position:absolute;left:${120+x.at*PX}px;top:232px;font-size:9px;color:${SC[x.cat]||'#fff'};transform:rotate(60deg);transform-origin:left top">${x.id}</div>`).join('');
if(M){const bg=M.bed_gain??.08,pts=[[0,bg],[T-.8,bg],[T,0]];
  html+=`<svg style="position:absolute;left:120px;top:330px" width=1500 height=60><polyline fill=none stroke=#c6f stroke-width=2 points="${pts.map(([t,g])=>`${t*PX},${60-g/0.35*56}`).join(' ')}"/></svg><div class=lab style="top:350px">Música</div>`;}
for(let s=0;s<=T;s+=5)html+=`<div style="position:absolute;left:${120+s*PX}px;top:400px;color:#777;font-size:10px">${s}s</div><div style="position:absolute;left:${120+s*PX}px;top:14px;height:380px;border-left:1px solid #222"></div>`;
html+='</body></html>';fs.writeFileSync(path.join(WD,'timeline.html'),html);
(async()=>{try{const puppeteer=require(path.join(__dirname,'..','engine','node_modules','puppeteer-core'));
  const b=await puppeteer.launch({executablePath:CHROME,headless:true,args:['--allow-file-access-from-files']});const p=await b.newPage();
  await p.setViewport({width:1640,height:430});await p.goto(fileURL(path.join(WD,'timeline.html')));await p.screenshot({path:path.join(WD,'timeline.png')});await b.close();
  console.log('línea de tiempo:',path.join(WD,'timeline.png'));}catch(e){console.log('(no pude dibujar timeline.png:',e.message.split('\n')[0]+')');}
  logTime(WD,'Dirección creativa',(Date.now()-t0)/1000);})();
