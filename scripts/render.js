// Paso 5: renderiza MG + subtítulos a .mov con alfa (QuickTime Animation).
// uso: node render.js <workdir> [--only=<regex>] [--test] [--par=6]
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
// S(spec, segundo del evento, {gain, dur}) → pone un sonido de la librería en la línea de tiempo (manual: nunca se descarta)
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
// B(clave de config.broll, segundo de origen, inicio en timeline, duración, [zoomInicio%, zoomFin%] para fotos)
function B(src,sin,start,dur,kb){broll.push({src,sin:+sin.toFixed(3),start:+start.toFixed(3),dur:+dur.toFixed(3),kb:kb||null});}
// X(archivo de audio absoluto, inicio, duración, ganancia lineal, segundo de origen)
function X(file,start,dur,gain,sin=0){extraSfx.push({file,start:+start.toFixed(3),dur:+dur.toFixed(3),gain,sin});}
require(path.join(WD,'jobs.js'))({J,B,X,S,F,W,C,CE,R,H,SG,edl,cfg,FPS});
const userJobs=jobs.slice();
// subtítulos: un clip por clip de V1
const KW=new Set((cfg.keywords||[]).map(norm));
// Los subtítulos corren todo el tiempo, PERO desaparecen mientras hay un motion graphic (ov, ov2 o pantalla completa):
// las palabras que caen dentro de un MG no se muestran (el MG ya cuenta esa idea) y vuelven apenas sale.
const MGW=userJobs.filter(j=>j.track!=='cap').map(j=>[j.start-0.08,j.end+0.1]);
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
// Límite del usuario: 3 pantallas completas y como máximo 3 motion graphics superpuestos (ov/ov2) en toda la edición
{const nFs=userJobs.filter(j=>j.track==='fs').length,nOv=userJobs.filter(j=>j.track==='ov'||j.track==='ov2').length;
 if(nOv>(cfg.mg_max??3))console.warn(`⚠️  Hay ${nOv} motion graphics superpuestos: el máximo es ${cfg.mg_max??3}. Elegir los más fuertes.`);
 if(nFs>(cfg.fs_max??3))console.warn(`⚠️  Hay ${nFs} pantallas completas: el máximo es ${cfg.fs_max??3}.`);}

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
// (remates y pantallas completas > gancho > CTA > b-roll > tarjetas > detalles internos) y bien separados entre sí.
const T_=edl.total/FPS,lastSeg=Math.max(...edl.clips.map(c=>c.seg)),ctaT=edl.clips.find(c=>c.seg===lastSeg).tl_in/FPS;
const firstJob=userJobs.filter(j=>j.track!=='cap').sort((a,b)=>a.start-b.start)[0];
if(cfg.sound_design!=='manual'){
  for(const j of userJobs){if(j.sfx!=='auto'||j.track==='cap')continue;
    const rule=AUTO[j.scene]||(j.track==='fs'?()=>[['whoosh',0]]:()=>[['pop',0]]);
    for(const e of rule(j.p).filter(Boolean)){if(!(e[1]>=0&&e[1]<j.end-j.start-0.15))continue;
      const entry=e[1]===0,strongScene=/bigword|stamp/.test(j.scene);
      const score=entry?(j.track==='fs'?(strongScene?11:10):strongScene?9:j===firstJob&&j.start<1.5?9:j.start>=ctaT-0.1?7:4)
                       :(e[0]==='hit'?8:e[0]==='error'?1:2);
      ev.push({spec:e[0],t:j.start+e[1],o:{},score});}}
  for(const b of broll)ev.push({spec:'whoosh',t:b.start,o:{},score:6});}
const MAX=cfg.sfx_max??5,SEP=Math.max(3,Math.min(7,T_/(MAX+1))),kept=ev.filter(e=>e.manual);
if(kept.length>MAX)console.warn(`⚠️  Hay ${kept.length} SFX manuales y el máximo es ${MAX}: sacar algunos.`);
for(const e of ev.filter(e=>!e.manual).sort((a,b)=>b.score-a.score||a.t-b.t)){
  if(kept.length>=MAX)break;if(kept.some(k=>Math.abs(k.t-e.t)<SEP))continue;kept.push(e);}
kept.sort((a,b)=>a.t-b.t);
const missing=new Set();
for(const e of kept){const id=pick(e.spec),m=CAT.sounds[id];last.id=id;
  if(!fs.existsSync(path.join(SFXDIR,m.file))){if(!missing.size)console.warn('⚠️  Faltan sonidos de la librería (instalar edicion-sfx.zip, ver README). Se omiten:');
    if(!missing.has(id)){missing.add(id);console.warn('   ',id);}continue;}
  let start=e.t-m.anchor,sin=0;if(start<0){sin=-start;start=0;}
  const dur=Math.min(e.o.dur||m.dur,m.dur-sin);if(dur<=0.02)continue;
  sfx.push({id,cat:m.cat,file:m.file,start:+start.toFixed(3),sin:+sin.toFixed(3),dur:+dur.toFixed(3),fdur:m.dur,gain:e.o.gain??CAT.categories[m.cat].gain,at:+e.t.toFixed(3),auto:!e.manual});}

// ───── REENCUADRES (V1) ─────
// Escala por clip según la intención: punch = énfasis · snap = zoom rápido de entrada · push = acercamiento lento (preguntas, cierre)
// tight/wide alternados para disimular los jump cuts (≥ 10 % de diferencia entre clips seguidos).
// cfg.face.top = alto (0–1) de la parte de arriba de la cabeza en el cuadro: limita el zoom para no cortarla
const MAXS=cfg.max_zoom||(cfg.face&&cfg.face.top!=null?Math.min(1.3,0.47/(0.5-cfg.face.top)):1.24);
const MODES={wide:[100,103],push:[100,109],tight:[114,114],punch:[124,124],snap:[100,118],pull:[114,102]};
const cover=(a,b)=>userJobs.some(j=>j.track==='fs'&&j.start<=a+0.05&&j.end>=b-0.05)||broll.some(x=>x.start<=a+0.05&&x.start+x.dur>=b-0.05);
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
  const ov=broll.reduce((a,x)=>a+Math.max(0,Math.min(j.end,x.start+x.dur)-Math.max(j.start,x.start)),0);if(ov<(j.end-j.start)*.5)j.p._place=true;}
fs.writeFileSync(path.join(WD,'jobs.json'),JSON.stringify(jobs,null,1));
fs.writeFileSync(path.join(WD,'broll.json'),JSON.stringify({broll,extraSfx},null,1));
fs.writeFileSync(path.join(WD,'sfx.json'),JSON.stringify(sfx.sort((a,b)=>a.start-b.start),null,1));

async function main(){
  if(!CHROME)throw new Error('No encuentro Chrome. Instalalo o definí CHROME=/ruta/al/ejecutable');
  const only=process.argv.find(a=>a.startsWith('--only='));const test=process.argv.includes('--test');
  const par=+((process.argv.find(a=>a.startsWith('--par='))||'--par=6').slice(6));
  let list=jobs;if(only){const re=new RegExp(only.slice(7));list=jobs.filter(j=>re.test(j.id));}
  const A=path.join(cfg.edit_dir,'Assets');
  const outFor=j=>test?path.join(WD,'test'):path.join(A,j.track==='cap'?'Subtitulos':'MG');
  [path.join(A,'MG'),path.join(A,'Subtitulos'),path.join(WD,'test')].forEach(d=>fs.mkdirSync(d,{recursive:true}));
  const browser=await puppeteer.launch({executablePath:CHROME,headless:true,args:['--allow-file-access-from-files','--force-device-scale-factor=1','--hide-scrollbars']});
  let qi=0;
  async function worker(){const page=await browser.newPage();await page.setViewport({width:1080,height:1920,deviceScaleFactor:1});
    await page.goto(fileURL(path.join(ENG,'engine.html')));{const k=await BRAND.apply(page,BR);if(k&&k<.98&&!FIT_SAID){FIT_SAID=1;console.log(`marca: la tipografía de títulos es más ancha que la del motor → títulos al ${Math.round(k*100)} %`);}}await page.evaluate(()=>document.fonts.ready);
    await page.evaluate(L=>{window.SAFE=L.face?L:null;},LAY);
    await page.evaluate((cc)=>{window.CAPCOL=cc;window.FMT={k:v=>(v/1000).toFixed(1).replace('.',',')+'K',m:v=>(v/1e6).toFixed(2).replace('.',',')+'M'}},cfg.caption_colors||(BR?BRAND.captionColors(BR):null));
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
        const buf=await page.screenshot({omitBackground:true,type:'png',optimizeForSpeed:true});
        if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));}
      ff.stdin.end();await done;console.log('ok',j.id,nf+'f');}
    await page.close();}
  await Promise.all(Array.from({length:par},worker));await browser.close();
}
if(process.argv.includes('--plan')){console.log(jobs.filter(j=>j.track!=='cap').map(j=>`${j.id.padEnd(24)} ${j.track.padEnd(4)} ${j.start.toFixed(2)}-${j.end.toFixed(2)}`).join('\n'));console.log(JSON.stringify(broll));
  console.log('SFX:\n'+sfx.map(x=>`  ${x.at.toFixed(2).padStart(6)}  ${x.id.padEnd(16)} gain ${x.gain}${x.auto?'  (auto)':''}`).join('\n'));
  console.log('Encuadres: '+framing.map(f=>`${f.i}:${f.mode}`).join(' '));
  console.log('Ubicación: '+LAY.note+` · ${jobs.filter(j=>j.p._place).length} MG se chequean contra la cara al renderizar`);}
else{const t0=Date.now();main().then(()=>{const lab=process.argv.includes('--test')?'Render de prueba':process.argv.some(a=>a.includes('cap'))&&!process.argv.some(a=>a.includes('?!cap'))?'Render de subtítulos':'Render de motion graphics';
  logTime(WD,lab,(Date.now()-t0)/1000);}).catch(e=>{console.error(e);process.exit(1)});}
