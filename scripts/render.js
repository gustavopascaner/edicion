// Paso 5: renderiza MG + subtítulos a .mov con alfa (QuickTime Animation).
// uso: node render.js <workdir> [--only=<regex>] [--test] [--par=N]   (N por defecto: 6, o menos si hay poca RAM)
//   --test  : en vez de .mov, exporta PNGs de prueba a <workdir>/test (--t=tiempos, ej --t=end-0.4 o --t=0.5,mid)
// Lee <workdir>/config.json, edl.json y jobs.js (module.exports = ctx => { ...J(), B(), X()... }).
const fs=require('fs'),path=require('path'),{spawn}=require('child_process');
const ENG=path.join(__dirname,'..','engine');
const puppeteer=require(path.join(ENG,'node_modules','puppeteer-core'));
const {CHROME,fileURL,logTime}=require('./platform.js');
const WD=path.resolve(process.argv[2]);
const cfg=JSON.parse(fs.readFileSync(path.join(WD,'config.json')));
const FPS=cfg.fps||30;
const LAY=require('./layout.js')(cfg);
// marca (compartida con motion: ~/.config/motion/brands). Sin marca o "editorial" = el look de siempre
const BRAND=require('./brand.js'),BR=BRAND.loadBrand(cfg.brand);
if(BR)console.log(`marca: ${BR.name||BR.slug}`);let FIT_SAID=0;
const edl=JSON.parse(fs.readFileSync(path.join(WD,'edl.json')));
const norm=s=>s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[^a-z0-9]/g,'');
// W(seg, palabra, n) → segundo de timeline donde empieza esa palabra dentro del segmento
function W(i,word,nth=0){const n=norm(word);let k=0;
  for(const c of edl.caps){if(c.seg!==i)continue;for(const w of c.words){if(norm(w.w).startsWith(n)){if(k===nth)return w.s/FPS;k++;}}}
  throw new Error(`palabra "${word}" no encontrada en segmento ${i}`);}
const SG=i=>edl.clips.filter(c=>c.seg===i);
const C=i=>SG(i)[0].tl_in/FPS, CE=i=>SG(i).slice(-1)[0].tl_out/FPS;
const R=(s,t)=>+(t-s).toFixed(3);
const H=t=>`<span style="background:var(--hot);padding:0 14px">${t}</span>`;
const jobs=[],broll=[],extraSfx=[],sfx=[];
// Librería de SFX (assets/sfx/catalog.json). Un "spec" es una categoría ('whoosh', 'pop', 'hit', 'ding'…; se alternan
// sus variantes) o el id de un sonido ('bass-drop'). El anchor del sonido (golpe o arranque) cae justo en el evento.
const SFXDIR=path.join(__dirname,'..','assets','sfx'),CAT=JSON.parse(fs.readFileSync(path.join(SFXDIR,'catalog.json')));
const rot={},last={};
function pick(spec){
  const all=Object.keys(CAT.sounds).filter(k=>CAT.sounds[k].cat===spec),rotating=all.filter(k=>CAT.sounds[k].rotate!==false);
  const ids=rotating.length?rotating:all;if(!ids.length&&CAT.sounds[spec])return spec;
  if(!ids.length)throw new Error(`SFX "${spec}" no existe (ni categoría ni id). Ver: python3 -I scripts/sfx_import.py --list`);
  let k=(rot[spec]=(rot[spec]??-1)+1)%ids.length;if(ids.length>1&&ids[k]===last.id)k=(k+1)%ids.length;return ids[k];}
// S(spec, segundo del evento, {gain, dur}) → pone un sonido de la librería en la línea de tiempo (manual: no se descarta, salvo en los primeros cfg.sfx_start s)
const ev=[];
function S(spec,t,o={}){ev.push({spec,t,o,manual:true});}
// J(id, escena, pista: 'ov'|'ov2'|'fs', inicio, fin, params, sfx)
//   sfx omitido → DISEÑO SONORO AUTOMÁTICO (según la escena y sus tiempos internos: ítems, sellos, clicks…)
//   'pop' · 'whoosh' · id… | ['whoosh',['pop',0.8],['ding',1.6,{gain:.3}]] (segundos desde el inicio) → manual · null → sin sonido
function J(id,scene,track,start,end,p,cue){jobs.push({id,scene,track,start:+start.toFixed(3),end:+end.toFixed(3),p:p||{},sfx:cue===undefined?'auto':cue});
  if(cue===undefined||cue==='auto'||!cue)return;const tuple=Array.isArray(cue)&&typeof cue[1]==='number';const list=Array.isArray(cue)&&!tuple?cue:[cue];
  for(const c of list){const [spec,at=0,o={}]=Array.isArray(c)?c:[c];S(spec,start+at,o);}}
// F(seg, modo) → encuadre de todos los clips de ese segmento · F.clip(i, modo). Modos: wide · push · tight · punch · snap · pull
const framingOverride={};
function F(seg,mode){SG(seg).forEach(c=>framingOverride[c.i]=mode);} F.clip=(i,mode)=>framingOverride[i]=mode;
// B(clave de config.broll, segundo de origen, inicio en timeline, duración, [zoomInicio%, zoomFin%], {fx, bg, label, side})
//   fx (o config.broll[clave].fx): 'full' (default, pantalla completa) · 'push' (Ken Burns también en video, default [100,110])
//   · 'phone' | 'polaroid' | 'circle' | 'window' (marco de marca con agujero: MG "bx_…" + subtítulos adentro) · 'pip' (ventanita en la zona libre, la cara sigue a la vista)
function B(src,sin,start,dur,kb,o){o=o||{};const fx=o.fx||((cfg.broll||{})[src]||{}).fx||'full',b={src,sin:+sin.toFixed(3),start:+start.toFixed(3),dur:+dur.toFixed(3),kb:kb||null};
  if(fx!=='full'){b.fx=fx;if(fx==='push'&&!kb)b.kb=[100,110];['bg','label','side','w'].forEach(k=>o[k]!=null&&(b[k]=o[k]));}broll.push(b);}
// X(archivo de audio absoluto, inicio, duración, ganancia lineal, segundo de origen)
function X(file,start,dur,gain,sin=0){extraSfx.push({file,start:+start.toFixed(3),dur:+dur.toFixed(3),gain,sin});}
require(path.join(WD,'jobs.js'))({J,B,X,S,F,W,C,CE,R,H,SG,edl,cfg,FPS});
// Dirección de arte (<work>/arte.json, SKILL.md 4-pre): skins por escena y lenguaje de movimiento por defecto (lo que ponga jobs.js manda)
const ART=fs.existsSync(path.join(WD,'arte.json'))?JSON.parse(fs.readFileSync(path.join(WD,'arte.json'))):{};
for(const j of jobs){const sk=(ART.skins||{})[j.scene];if(sk&&j.p.skin==null)j.p.skin=sk;if(ART.motion&&j.p.motion==null)j.p.motion=ART.motion;}
// Estilo de subtítulos: config.caption_style > arte.json "subtitulos" > brand.json "captions" > 'box' (el de siempre)
const CAPSTYLE=(c=>typeof c==='string'?{style:c}:c)(cfg.caption_style??ART.subtitulos??BRAND.captionStyle(BR)??null);
if(CAPSTYLE&&CAPSTYLE.style&&CAPSTYLE.style!=='box')console.log(`subtítulos: estilo ${CAPSTYLE.style}`);
// Tratamientos de b-roll: geometría del agujero (lo lee build_xml.py para escalar/posicionar el b-roll) y dónde van los subtítulos
const FXBOX={phone:{box:[250,170,580,1031],capY:1330},polaroid:{box:[150,190,780,960],capY:1420},circle:{box:[150,300,780,780],capY:1300},window:{box:[60,150,960,1100],capY:1340}};
const FXW=[];
for(const b of broll){if(!b.fx||b.fx==='push')continue;const m=(cfg.broll||{})[b.src]||{};
  if(b.fx==='pip'){const ar=(m.w||1080)/(m.h||1920),zs=LAY.zones.map(z=>({z,cap:LAY.capTop>=z[0]-20&&LAY.capTop<z[1]})).filter(o=>o.z[1]-o.z[0]>=380).sort((a,c)=>a.cap-c.cap||(c.z[1]-c.z[0])-(a.z[1]-a.z[0]));
    if(!zs.length){console.warn(`⚠️  B-roll "${b.src}" con fx 'pip': no hay lugar libre de ≥ 380 px fuera de la cara → uso 'window'.`);b.fx='window';}
    else{const {z,cap}=zs[0],hh=Math.min(z[1]-z[0]-60,(b.w||460)/ar),w=hh*ar;b.box=[Math.round(b.side==='left'?70:1080-70-w),Math.round(z[0]+(z[1]-z[0]-hh)/2),Math.round(w),Math.round(hh)];b.capHide=cap;}}
  if(FXBOX[b.fx]){b.box=FXBOX[b.fx].box;b.capY=FXBOX[b.fx].capY;b.capHide=true;}
  if(!b.box){console.warn(`⚠️  fx "${b.fx}" desconocido en el b-roll "${b.src}": va a pantalla completa.`);delete b.fx;continue;}
  if(b.capHide)FXW.push([b.start-0.02,b.start+b.dur+0.02]);}
const userJobs=jobs.slice();
// subtítulos: un clip por clip de V1
const KW=new Set((cfg.keywords||[]).map(norm));
// Los subtítulos corren todo el tiempo, PERO desaparecen mientras hay un motion graphic (ov, ov2 o pantalla completa):
// las palabras que caen dentro de un MG no se muestran (el MG ya cuenta esa idea) y vuelven apenas sale.
const MGW0=userJobs.filter(j=>j.track!=='cap').map(j=>[j.start-0.08,j.end+0.1]),MGW=[...MGW0,...FXW];   // FXW: b-roll con marco (los subtítulos van adentro del marco)
const inMG=(a,b)=>MGW.some(([x,y])=>a<y&&b>x),nextMG=t=>Math.min(...MGW.filter(([x])=>x>=t).map(([x])=>x),1e9);
let capHidden=0;
edl.clips.forEach((c,i)=>{const s=c.tl_in/FPS,e=c.tl_out/FPS,groups=[];
  for(const g of edl.caps.filter(g=>g.clip===i)){
    const ws=g.words.map(w=>({w:w.w.replace(/[¿?:]/g,'').replace(/,$/,''),gs:w.s/FPS,ge:w.e/FPS,k:KW.has(norm(w.w))}));let run=[];
    const flush=(last)=>{if(!run.length)return;const a=run[0]===ws[0]?g.tl_in/FPS:run[0].gs;
      const b=Math.min(last?g.tl_out/FPS:run[run.length-1].ge+0.12,nextMG(run[0].gs));
      groups.push({s:R(s,a),e:R(s,b),words:run.map(w=>({w:w.w,s:R(s,w.gs),e:R(s,w.ge),k:w.k}))});run=[];};
    ws.forEach((w,k)=>{if(inMG(w.gs,w.ge)){flush(false);capHidden++;}else run.push(w);});flush(true);}
  if(groups.length)J(`cap_${String(i).padStart(2,'0')}`,'cap','cap',s,e,{groups,y:LAY.capTop});});
if(capHidden)console.log(`subtítulos: ${capHidden} palabras ocultas bajo motion graphics`);
// marcos de b-roll: un MG por b-roll tratado (pista de subtítulos = justo encima del b-roll y debajo de stickers/tarjetas), con los subtítulos de ese tramo adentro
broll.filter(b=>b.box).forEach((b,k)=>{const a=b.start,e=b.start+b.dur,caps=[];
  if(b.fx!=='pip')for(const g of edl.caps){const ws=g.words.filter(w=>w.s/FPS>=a-0.02&&w.s/FPS<e-0.1&&!MGW0.some(([x,y])=>w.s/FPS<y&&w.e/FPS>x));if(!ws.length)continue;
    caps.push({s:R(a,Math.max(a,ws[0].s/FPS)),e:R(a,Math.min(e,g.tl_out/FPS,ws[ws.length-1].e/FPS+0.12)),words:ws.map(w=>({w:w.w.replace(/[¿?:]/g,'').replace(/,$/,''),s:R(a,w.s/FPS),e:R(a,w.e/FPS),k:KW.has(norm(w.w))}))});}
  J(`bx_${String(k+1).padStart(2,'0')}_${b.src}`,'bframe','cap',a,e,{kind:b.fx,box:b.box,bg:b.bg,label:b.label,caps,capY:b.capY??LAY.capTop,_bx:true,free:true},null);});
// Límites: 2–4 pantallas completas (cfg.fs_max, default 4) y como máximo cfg.mg_max (default 3) motion graphics superpuestos (ov/ov2)
{const nFs=userJobs.filter(j=>j.track==='fs').length,nOv=userJobs.filter(j=>j.track==='ov'||j.track==='ov2').length;
 if(nOv>(cfg.mg_max??3))console.warn(`⚠️  Hay ${nOv} motion graphics superpuestos: el máximo es ${cfg.mg_max??3}. Elegir los más fuertes.`);
 if(nFs>(cfg.fs_max??4))console.warn(`⚠️  Hay ${nFs} pantallas completas: el máximo es ${cfg.fs_max??4}.`);}

// ───── DISEÑO SONORO AUTOMÁTICO ─────
// Cada escena dispara sonidos en sus momentos internos (segundos locales). Luego se raleán por prioridad y densidad.
const A=(spec,at)=>at==null||isNaN(at)?null:[spec,+at];
const each=(arr,f)=>(arr||[]).map(f);
const AUTO={
  listCard:p=>[['pop',0],...(p.items||[]).flatMap(it=>[A(it.mark==='check'?'ding':it.mark==='x'?'error':'pop',it.at),A('error',it.strikeAt)])],
  textcard:p=>[['pop',0],...each(p.lines,(l,k)=>/--hot|class="hl/.test(l)&&p.at?A('pop',p.at[k]):null)],
  target:p=>[['pop',0],A('pop',p.qAt)], search:p=>[['pop',0],A('click',p.typeAt),A('click',p.pickAt)], choice:p=>[['pop',0],A('click',p.pickAt)],
  flow:p=>each(p.nodes,n=>A('pop',n.at)), loop:p=>each(p.nodes,n=>A('pop',n.at)), excuses:p=>[['pop',0],...each(p.items,n=>A('pop',n.at))],
  algo:p=>[['pop',0],A('hit',p.stampAt)], check10:p=>[['pop',0],A('ding',p.tickAt),A('ding',p.goalAt)], scroll:p=>[['pop',0],A('hit',p.stopAt)],
  hook:p=>[['whoosh',0],...each(p.tagAt,t=>A('pop',t)),A('hit',p.bigAt)], stat:p=>[['pop',0],A('ding',p.countEnd)], stamp:p=>[A('hit',p.at??0)],
  hud:p=>[['glitch',0],A('click',p.labAt)], pensas:p=>[...each(p.at,t=>A('pop',t)),A('hit',p.noAt)], tracker:()=>[],
  dm:p=>[['pop',0],A('pop',p.replyAt)], follow:p=>[['pop',0],A('click',p.clickAt)], comment:p=>[['pop',0],A('click',p.typeAt),A('click',p.sendAt)],
  book:p=>[['pop',0],A('click',p.btnAt),A('hit',p.stampAt)],
  fsTitle:p=>[['whoosh',0],p.marks?A('error',p.marksAt):null], bigword:()=>[['hit',0]], counter:p=>[['whoosh',0],A('error',p.strikeAt)],
  metrics:p=>[['whoosh',0],...each(p.tiles,t=>A('pop',t.at)),A('hit',p.stampAt)], calendar:p=>[['whoosh',0],A('pop',p.qAt)],
};
// Pocos sonidos y sutiles: como máximo cfg.sfx_max (default 5) en TODA la edición, elegidos por importancia
// (remates y pantallas completas > CTA > b-roll > tarjetas > detalles internos) y bien separados entre sí.
// El video NUNCA arranca con un efecto (pedido del usuario): nada antes de cfg.sfx_start (default 1,5 s), ni automático ni manual.
const T_=edl.total/FPS,lastSeg=Math.max(...edl.clips.map(c=>c.seg)),ctaT=edl.clips.find(c=>c.seg===lastSeg).tl_in/FPS;
const NO_SFX_START=cfg.sfx_start??1.5,SFXHIST=process.env.EDICION_SFXHIST||path.join(require('os').homedir(),'.config','edicion','sfx_hist.jsonl');
const isCat=s=>Object.values(CAT.sounds).some(x=>x.cat===s),catOf=s=>isCat(s)?s:(CAT.sounds[s]||{}).cat||s;
const hasFile=id=>CAT.sounds[id]&&fs.existsSync(path.join(SFXDIR,CAT.sounds[id].file));
const CAT_MAX=cfg.sfx_cat_max??2,MIN_SCORE=cfg.sfx_min_score??3,ALT={whoosh:['zoom']};  // con 2 whoosh ya elegidos, UNA entrada/corte alterna con zoom (barrido ascendente; cfg.sfx_alt_max) para variar el timbre
const isCta=j=>j.start>=ctaT-0.1;
if(cfg.sound_design!=='manual'){
  for(const j of userJobs){if(j.sfx!=='auto'||j.track==='cap')continue;
    const rule=AUTO[j.scene]||(j.track==='fs'?()=>[['whoosh',0]]:()=>[['pop',0]]);
    for(const e of rule(j.p).filter(Boolean)){if(!(e[1]>=0&&e[1]<j.end-j.start-0.15))continue;
      const entry=e[1]===0,strongScene=/bigword|stamp/.test(j.scene);
      // puntaje: remates y revelaciones (fs) > CTA > b-roll > tarjetas > detalles internos (hit 9 · ✓ 5 · click 3,5 · ✗ 3 · pop 2 = bajo el mínimo)
      const score=entry?(j.track==='fs'?(strongScene?11:10):strongScene?9:isCta(j)?9:4)
                       :(e[0]==='hit'?9:e[0]==='ding'?5:e[0]==='click'?3.5:e[0]==='error'?3:2);
      ev.push({spec:e[0],t:j.start+e[1],o:{},score,why:`${j.id}${entry?'':' +'+e[1].toFixed(1)+'s'}`,alt:entry&&e[0]==='whoosh'?ALT.whoosh:null});}}
  for(const b of broll)ev.push({spec:'whoosh',t:b.start,o:{},score:6,why:'b-roll '+b.src,alt:ALT.whoosh});}
const dropped=[];
for(let i=ev.length-1;i>=0;i--){const x=ev[i];
  if(x.t<NO_SFX_START){if(x.manual)console.warn(`⚠️  SFX manual en ${x.t.toFixed(2)}s descartado: el video no arranca con un efecto (nada antes de ${NO_SFX_START}s).`);ev.splice(i,1);}
  else if(!x.manual&&x.t>T_-0.35){ev.splice(i,1);}}
const MAX=cfg.sfx_max??5,SEP=Math.max(3,Math.min(6,T_/(MAX+1)*.85)),kept=ev.filter(e=>e.manual);
if(kept.length>MAX)console.warn(`⚠️  Hay ${kept.length} SFX manuales y el máximo es ${MAX}: sacar algunos.`);
// Selección: por puntaje; 1.ª vuelta separados ≥ SEP s (3–6 s según el largo); 2.ª vuelta solo los remates fuertes (≥ 8) con ≥ 3 s.
// Si ya hay CAT_MAX (2) sonidos de la misma categoría y el evento tiene alternativa, se usa la alternativa (variedad de timbre).
const nCat=c=>kept.filter(k=>catOf(k.spec)===c).length,auto_=ev.filter(e=>!e.manual).sort((a,b)=>b.score-a.score||a.t-b.t),chosen=new Set();
for(const gap of [SEP,3]){for(const e of auto_){
  if(kept.length>=MAX)break;if(chosen.has(e)||e.score<MIN_SCORE||(gap===3&&e.score<8))continue;
  if(kept.some(k=>Math.abs(k.t-e.t)<gap))continue;
  if(nCat(catOf(e.spec))>=CAT_MAX&&e.alt){const a=e.alt.find(s=>nCat(s)<(cfg.sfx_alt_max??1)&&Object.keys(CAT.sounds).some(k=>CAT.sounds[k].cat===s&&CAT.sounds[k].rotate!==false&&hasFile(k)));if(a)e.spec=a;}
  kept.push(e);chosen.add(e);}}
for(const e of auto_)if(!chosen.has(e)){const n=kept.find(k=>Math.abs(k.t-e.t)<SEP);dropped.push(`${e.t.toFixed(2).padStart(6)}  ${e.spec.padEnd(7)} puntaje ${e.score}  (${e.why}) → ${e.score<MIN_SCORE?'puntaje bajo':n?`muy cerca de ${n.spec} ${n.t.toFixed(1)}s`:'máximo '+MAX}`);}
kept.sort((a,b)=>a.t-b.t);
// Rotación con memoria: se evita lo que sonó en los últimos videos (~/.config/edicion/sfx_hist.jsonl, ruta con EDICION_SFXHIST) y lo ya usado en ESTA edición.
const readHist=()=>{try{return fs.readFileSync(SFXHIST,'utf8').split('\n').filter(Boolean).map(l=>JSON.parse(l))}catch(e){return []}};
const hist=cfg.sfx_hist===false?[]:readHist().filter(h=>h.video!==cfg.name).slice(-8),usedNow={};let prevId=null;
const h32=s=>{let h=2166136261;for(const ch of s){h^=ch.charCodeAt(0);h=Math.imul(h,16777619)>>>0;}return h/4294967296;};
function smartPick(spec){
  if(!isCat(spec))return pick(spec);
  const ids=Object.keys(CAT.sounds).filter(k=>CAT.sounds[k].cat===spec&&CAT.sounds[k].rotate!==false&&hasFile(k));
  if(!ids.length)return pick(spec);
  const sc=id=>hist.reduce((a,h,i)=>a+(h.ids||[]).filter(x=>x===id).length*Math.pow(.85,hist.length-1-i),0)+3*(usedNow[id]||0)+(id===prevId?5:0)+.4*h32(cfg.name+'|'+id);
  return ids.map(id=>[sc(id),id]).sort((a,b)=>a[0]-b[0])[0][1];}
// Nivel relativo a la voz (catalog.levels): pico del SFX = pico típico de la voz − rel_db; LUFS máx. según duración; tope duro −3 dBFS.
const LV=CAT.levels||{},VOICE=cfg.voice_lufs??(()=>{try{return JSON.parse(fs.readFileSync(path.join(WD,'conform.json'))).voice_lufs}catch(e){}})()??LV.voice_lufs??-16,REFPK=cfg.sfx_ref_peak??(VOICE+(LV.voice_crest_db??11)),LREL=LV.lufs_rel||{short:10,mid:12,long:14};
function levelFor(m,effDur){const C=CAT.categories[m.cat]||{},rel=(m.rel_db??C.rel_db);
  if(rel==null||m.tp==null||cfg.sfx_levels==='legacy')return{g:C.gain??.25,db:20*Math.log10(C.gain??.25),rel:null};
  const lr=effDur<.8?LREL.short:effDur<2?LREL.mid:LREL.long,r=rel-(cfg.sfx_rel??0);
  const db=Math.min(REFPK-r-m.tp,m.lufs>-60?VOICE-lr-m.lufs:99,-3-m.tp);
  return{g:Math.pow(10,db/20),db,rel:r};}
const missing=new Set();
for(const e of kept){const id=smartPick(e.spec),m=CAT.sounds[id];last.id=id;
  if(!fs.existsSync(path.join(SFXDIR,m.file))){if(!missing.size)console.warn('⚠️  Faltan sonidos de la librería (instalar edicion-sfx.zip, ver README). Se omiten:');
    if(!missing.has(id)){missing.add(id);console.warn('   ',id);}continue;}
  usedNow[id]=(usedNow[id]||0)+1;prevId=id;
  let start=e.t-m.anchor,sin=0;if(start<0){sin=-start;start=0;}
  // cola máxima tras el golpe (catalog tail por sonido/categoría): los sonidos largos no tapan palabras
  const tail=m.tail??(CAT.categories[m.cat]||{}).tail??99,full=m.dur-sin;
  const dur=Math.min(full,e.o.dur||99,Math.max(.15,m.anchor-sin+tail));if(dur<=0.02)continue;
  const lv=levelFor(m,dur),gain=e.o.gain??(e.o.db!=null?Math.pow(10,e.o.db/20):lv.g),gdb=20*Math.log10(gain);
  const trimmed=dur<full-.03;   // se corta antes de su final → fade-out (sin clic) · si arranca adentro del archivo (sin>0) → fade-in
  sfx.push({id,cat:m.cat,file:m.file,start:+start.toFixed(3),sin:+sin.toFixed(3),dur:+dur.toFixed(3),fdur:m.dur,gain:+gain.toFixed(4),at:+e.t.toFixed(3),auto:!e.manual,
    gain_db:+gdb.toFixed(1),peak_db:+(gdb+m.tp).toFixed(1),anchor:m.anchor,fade_in:sin>.01?.03:0,fade_out:trimmed?+Math.min(.3,Math.max(.08,dur*.3)).toFixed(2):0,why:e.why||'S() manual'});}
if(cfg.sfx_hist!==false&&sfx.length){try{fs.mkdirSync(path.dirname(SFXHIST),{recursive:true});
  const all=readHist().filter(h=>h.video!==cfg.name).slice(-60);all.push({video:cfg.name,date:new Date().toISOString().slice(0,10),ids:sfx.map(x=>x.id)});
  fs.writeFileSync(SFXHIST,all.map(h=>JSON.stringify(h)).join('\n')+'\n');}catch(err){console.warn('sfx_hist: no se pudo guardar ('+err.message+')');}}
if(process.argv.includes('--plan')){
  console.log(`\nDiseño sonoro: ${sfx.length} SFX (máx ${MAX}, separación ≥ ${SEP.toFixed(1)} s, nada antes de ${NO_SFX_START} s) · voz ${VOICE} LUFS, pico de referencia ${REFPK.toFixed(0)} dBFS`);
  for(const x of sfx)console.log(`  ${x.at.toFixed(2).padStart(6)}s  ${x.id.padEnd(15)} ${x.cat.padEnd(7)} ${String(x.gain_db).padStart(6)} dB (×${x.gain})  pico ${x.peak_db} dBFS (${(x.peak_db-REFPK).toFixed(1)} vs voz)`+
    `${x.fade_out?`  corta a ${x.dur}s, fade ${x.fade_out}s`:''}${x.fade_in?`  entra en ${x.sin}s`:''}  ← ${x.why}`);
  if(dropped.length)console.log('  descartados:\n'+dropped.map(d=>'    '+d).join('\n'));
  if(hist.length)console.log(`  memoria: evita lo usado en los últimos ${hist.length} videos (${[...new Set(hist.flatMap(h=>h.ids||[]))].length} sonidos distintos)`);}

// ───── REENCUADRES (V1) ─────
// Escala por clip según la intención: punch = énfasis · snap = zoom rápido de entrada · push = acercamiento lento (preguntas, cierre)
// tight/wide alternados para disimular los jump cuts (≥ 10 % de diferencia entre clips seguidos).
// cfg.face.top = alto (0–1) de la parte de arriba de la cabeza en el cuadro: limita el zoom para no cortarla
const MAXS=cfg.max_zoom||(cfg.face&&cfg.face.top!=null?Math.min(1.3,0.47/(0.5-cfg.face.top)):1.24);
const MODES={wide:[100,103],push:[100,109],tight:[114,114],punch:[124,124],snap:[100,118],pull:[114,102]};
const cover=(a,b)=>userJobs.some(j=>j.track==='fs'&&j.start<=a+0.05&&j.end>=b-0.05)||broll.some(x=>x.fx!=='pip'&&x.start<=a+0.05&&x.start+x.dur>=b-0.05);
const strong=(a,b)=>userJobs.some(j=>/stamp|bigword/.test(j.scene)&&j.start<b&&j.end>a);
const framing=[];let lastPunch=-99,prev=null;
edl.clips.forEach((c,i)=>{const a=c.tl_in/FPS,b=c.tl_out/FPS,txt=c.text||'';let m;
  const kw=(txt.split(/\s+/)).some(w=>KW.has(norm(w)));
  if(framingOverride[i])m=framingOverride[i];
  else if(cover(a,b))m='wide';
  else if(i===0)m='snap';
  else if(i===edl.clips.length-1)m='push';
  else if((/!$/.test(txt.trim())||strong(a,b)||(kw&&b-a<2.5))&&a-lastPunch>6&&prev!=='punch')m='punch';
  else if(/\?$/.test(txt.trim()))m='push';
  else m=(prev==='wide'||prev==='push'||prev==='snap'||prev==='pull')?'tight':'wide';
  if(m===prev&&m!=='wide'&&!framingOverride[i])m=m==='tight'?'wide':'tight';
  const cap=v=>Math.min(v,Math.round(MAXS*100));let [s0,s1]=(MODES[m]||MODES.wide).map(cap);
  const pe=framing.length?framing[framing.length-1].s1:null;
  if(pe!=null&&Math.abs(pe-s0)<8&&!framingOverride[i]){   // jump cut: forzar un cambio de escala visible
    if(m==='wide'||m==='tight'){m=m==='wide'?'tight':'wide';[s0,s1]=MODES[m].map(cap);}
    else if(m==='push'){[s0,s1]=pe<108?[cap(112),cap(120)]:[100,108];}
    if(Math.abs(pe-s0)<8){[s0,s1]=pe>=108?[100,103]:[cap(114),cap(114)];m=pe>=108?'wide':'tight';}}
  if(m==='punch')lastPunch=a;
  framing.push({i,mode:m,s0,s1,ramp:m==='snap'?0.25:null,tl_in:c.tl_in,tl_out:c.tl_out});prev=m;});
fs.writeFileSync(path.join(WD,'framing.json'),JSON.stringify(framing,null,1));
// No pisar la cara: los MG superpuestos (no los que van sobre b-roll, donde la cara no se ve) se reubican si la tocan (engine: avoidFace)
for(const j of jobs){if(j.track!=='ov'&&j.track!=='ov2')continue;if(j.scene==='tracker'||j.p.free)continue;
  const ov=broll.filter(x=>x.fx!=='pip').reduce((a,x)=>a+Math.max(0,Math.min(j.end,x.start+x.dur)-Math.max(j.start,x.start)),0);if(ov<(j.end-j.start)*.5)j.p._place=true;}
fs.writeFileSync(path.join(WD,'jobs.json'),JSON.stringify(jobs,null,1));
fs.writeFileSync(path.join(WD,'broll.json'),JSON.stringify({broll,extraSfx},null,1));
fs.writeFileSync(path.join(WD,'sfx.json'),JSON.stringify(sfx.sort((a,b)=>a.start-b.start),null,1));

const CONCEPT_JS=path.join(WD,'concept.js'),LEGACY=jobs.some(j=>j.scene==='concept'&&j.p.motif);
if(jobs.some(j=>j.scene==='concept')){
  if(LEGACY)console.warn('⚠️  La pantalla conceptual usa un motivo viejo (`motif`): es una animación reciclada. Escribir una nueva en concept.js (ver SKILL.md paso 4).');
  else if(!fs.existsSync(CONCEPT_JS))console.warn(`⚠️  Falta ${CONCEPT_JS}: la pantalla conceptual se diseña y programa desde cero para cada video.`);}
async function main(){
  if(!CHROME)throw new Error('No encuentro Chrome. Instalalo o definí CHROME=/ruta/al/ejecutable');
  const only=process.argv.find(a=>a.startsWith('--only='));const test=process.argv.includes('--test');
  // pestañas de Chrome en paralelo: 6 por defecto, menos si hay poca RAM (~2,4 GB por pestaña a 1080×1920; 8 GB → 3, 16 GB → 6)
  const parDef=Math.max(2,Math.min(6,Math.floor(require('os').totalmem()/2**30/2.4)));
  const par=+((process.argv.find(a=>a.startsWith('--par='))||'--par='+parDef).slice(6));
  let list=jobs;if(only){const re=new RegExp(only.slice(7));list=jobs.filter(j=>re.test(j.id));}
  const A=path.join(cfg.edit_dir,'Assets');
  const outFor=j=>test?path.join(WD,'test'):path.join(A,j.track==='cap'?'Subtitulos':'MG');
  [path.join(A,'MG'),path.join(A,'Subtitulos'),path.join(WD,'test')].forEach(d=>fs.mkdirSync(d,{recursive:true}));
  const browser=await puppeteer.launch({executablePath:CHROME,headless:true,protocolTimeout:900000,args:['--allow-file-access-from-files','--force-device-scale-factor=1','--hide-scrollbars']});
  let qi=0;
  async function worker(){const page=await browser.newPage();await page.setViewport({width:1080,height:1920,deviceScaleFactor:1});
    await page.goto(fileURL(path.join(ENG,'engine.html')));{const k=await BRAND.apply(page,BR);if(k&&k<.98&&!FIT_SAID){FIT_SAID=1;console.log(`marca: la tipografía de títulos es más ancha que la del motor → títulos al ${Math.round(k*100)} %`);}}await page.evaluate(()=>document.fonts.ready);
    await page.evaluate(L=>{window.SAFE=L.face?L:null;},LAY);
    // animación conceptual de ESTE video (escrita desde cero) · los motivos viejos solo si una edición vieja usa `motif`
    if(fs.existsSync(CONCEPT_JS))await page.addScriptTag({path:CONCEPT_JS});
    if(LEGACY)await page.addScriptTag({path:path.join(__dirname,'..','reference','concept_ejemplos.js')});
    await page.evaluate((cc)=>{window.CAPCOL=cc;window.FMT={k:v=>(v/1000).toFixed(1).replace('.',',')+'K',m:v=>(v/1e6).toFixed(2).replace('.',',')+'M'}},cfg.caption_colors||(BR?BRAND.captionColors(BR):null));await page.evaluate(cs=>{window.CAPSTYLE=cs;},CAPSTYLE);
    while(qi<list.length){const j=list[qi++];const dur=j.end-j.start;const nf=Math.round(dur*FPS);
      try{const pl=await page.evaluate((j,dur)=>{if(j.p.tiles)j.p.tiles.forEach(t=>t.fmt=FMT[t.fmt]);return setup(j.scene,j.p,dur);},j,dur);
        if(pl&&pl.mode!=='ok')console.log(`  cara: ${j.id} ${pl.mode}${pl.mode==='movido'?` (y ${pl.from}→${pl.to}, escala ${Math.round(pl.scale*100)} %)`:' — revisar a mano'}`);}catch(e){console.log('ERR',j.id,e.message.split('\n')[0]);continue;}
      if(test){const ts=((process.argv.find(a=>a.startsWith('--t='))||'').slice(4)||process.env.T||'end-0.4').split(',');
        for(const x of ts){let t=x==='mid'?dur/2:x.startsWith('end')?dur+parseFloat(x.slice(3)):parseFloat(x);if(isNaN(t))continue;
          await page.evaluate((t)=>frame(t,Math.round(t*30)),t);await page.screenshot({path:path.join(outFor(j),`${j.id}_t${t.toFixed(2)}.png`),omitBackground:true});}
        continue;}
      const outf=path.join(outFor(j),j.id+'.mov');
      const ff=spawn('ffmpeg',['-v','error','-y','-f','image2pipe','-framerate',String(FPS),'-c:v','png','-i','-','-c:v','qtrle','-pix_fmt','argb',outf]);
      const done=new Promise(r=>ff.on('close',r));
      for(let f=0;f<nf;f++){await page.evaluate((t,f)=>frame(t,f),f/FPS,f);
        let buf;for(let k=0;;k++){try{buf=await page.screenshot({omitBackground:true,type:'png'});break;}catch(e){if(k>=2)throw e;}}  // Windows: captureScreenshot a veces se cuelga
        if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));}
      ff.stdin.end();await done;console.log('ok',j.id,nf+'f');}
    await page.close();}
  await Promise.all(Array.from({length:par},worker));await browser.close();
}
if(process.argv.includes('--plan')){console.log(jobs.filter(j=>j.track!=='cap').map(j=>`${j.id.padEnd(24)} ${j.track.padEnd(4)} ${j.start.toFixed(2)}-${j.end.toFixed(2)}`).join('\n'));console.log(JSON.stringify(broll.map(({box,capY,capHide,...b})=>b)));
  console.log('SFX:\n'+sfx.map(x=>`  ${x.at.toFixed(2).padStart(6)}  ${x.id.padEnd(16)} gain ${x.gain}${x.auto?'  (auto)':''}`).join('\n'));
  console.log('Encuadres: '+framing.map(f=>`${f.i}:${f.mode}`).join(' '));
  console.log('Ubicación: '+LAY.note+` · ${jobs.filter(j=>j.p._place).length} MG se chequean contra la cara al renderizar`);}
else{const t0=Date.now();main().then(()=>{const lab=process.argv.includes('--test')?'Render de prueba':process.argv.some(a=>a.includes('cap'))&&!process.argv.some(a=>a.includes('?!cap'))?'Render de subtítulos':'Render de motion graphics';
  logTime(WD,lab,(Date.now()-t0)/1000);}).catch(e=>{console.error(e);process.exit(1)});}
