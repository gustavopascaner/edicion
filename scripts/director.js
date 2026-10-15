// Dirección creativa unificada: revisa que video, b-roll, gráficos, subtítulos, SFX y música no compitan entre sí.
// uso: node director.js <workdir>   (después de `render.js --plan`)
// → imprime el informe, lo guarda en <workdir>/direction.md y dibuja la línea de tiempo en <workdir>/timeline.png
const fs=require('fs'),path=require('path');
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
if(B.length&&B.length<3)W(`Hay ${B.length} b-roll(s): el objetivo son 3 momentos (inicio, medio, antes del CTA).`);
if(B.length>=2){const s=B.map(b=>b.start).sort((a,b)=>a-b);if(s[s.length-1]-s[0]<T*0.35)W('Los b-rolls están amontonados: repartirlos a lo largo del video.');}
for(const f of fsj){const d=f.end-f.start;if(d<0.8||d>3.6)W(`Pantalla completa ${f.id} dura ${f2(d)}: ideal 1–3 s.`);}
const fss=fsj.map(f=>f.start).sort((a,b)=>a-b);
for(let i=1;i<fss.length;i++)if(fss[i]-fss[i-1]<6)W(`Pantallas completas muy seguidas (${f2(fss[i-1])} y ${f2(fss[i])}): espaciarlas ≥ 6 s.`);
if(T>20&&!fsj.length)W('No hay ninguna pantalla completa: sumar 1 remate fuerte cada 10–15 s.');
// cara visible y "aire"
const step=0.1;let face=0,clean=0,idle=0,maxIdle=0,idleAt=0;
const evs=[...jobs.filter(j=>j.track!=='cap').map(j=>j.start),...B.map(b=>b.start),...framing.filter(f=>/punch|snap/.test(f.mode)).map(f=>f.tl_in/FPS)].sort((a,b)=>a-b);
for(let t=0;t<T;t+=step){const covered=fsj.some(f=>t>=f.start&&t<f.end)||B.some(b=>t>=b.start&&t<b.end);
  if(!covered)face+=step;if(!covered&&!ov.some(j=>t>=j.start&&t<j.end))clean+=step;}
for(let i=0;i<=evs.length;i++){const a=i?evs[i-1]:0,b=i<evs.length?evs[i]:T;if(b-a>maxIdle){maxIdle=b-a;idleAt=a;}}
const pf=face/T*100,pc=clean/T*100;
(pf<55?W:O)(`Cara a cámara visible el ${pf.toFixed(0)}% del video${pf<55?' (poca: la persona tiene que sostener el video, objetivo ≥ 55%)':''}.`);
(pc<5?W:O)(`Cara sin ningún gráfico encima: ${pc.toFixed(0)}%${pc<5?' (muy cargado: dejar respirar 1–2 tramos cortos, por ejemplo justo después de un remate)':''}.`);
(maxIdle>12?W:O)(`Tramo más largo sin ningún evento visual: ${f2(maxIdle)} desde ${f2(idleAt)}${maxIdle>12?' (se vuelve monótono: sumar tarjeta, punch-in o b-roll)':''}.`);
if(!evs.length||evs[0]>1.0)W('Nada visual en el primer segundo: el gancho necesita texto o movimiento desde el arranque.');
// ── Sonido ──
const hits=sfx.filter(x=>x.cat==='hit');for(let i=1;i<hits.length;i++)if(hits[i].at-hits[i-1].at<4)W(`Dos golpes (hit) a menos de 4 s (${f2(hits[i-1].at)} y ${f2(hits[i].at)}): pierden fuerza.`);
for(let i=1;i<sfx.length;i++)if(sfx[i].at-sfx[i-1].at<0.25&&sfx[i].cat!=='build'&&sfx[i-1].cat!=='build')W(`SFX encimados en ${f2(sfx[i].at)}: ${sfx[i-1].id} + ${sfx[i].id}.`);
const SMAX=cfg.sfx_max??5;(sfx.length>SMAX?W:O)(`SFX: ${sfx.length} en toda la edición (máximo ${SMAX})${sfx.length>SMAX?' — sacar los menos importantes':''}: ${sfx.map(x=>x.id+' '+f2(x.at)).join(' · ')}.`);
for(let i=1;i<sfx.length;i++)if(sfx[i].at-sfx[i-1].at<3)W(`SFX muy cerca (${f2(sfx[i-1].at)} y ${f2(sfx[i].at)}): separarlos ≥ 3 s para que sea sutil.`);
const M=cfg.music&&typeof cfg.music==='object'?cfg.music:null;
if(M){if((M.envato||{}).status==='preview')W('La música es la vista previa con marca de agua de Envato: falta licenciarla.');O(`Música: gancho ${M.hook_gain??.3} → fondo ${M.bed_gain??.08} bajo la voz → cierre ${M.outro_gain??.22}.`);}
else if(cfg.music)O('Música colocada a mano (X).');else W('Sin música de fondo.');
for(const b of B){const m=(cfg.broll||{})[b.src]||{};if((m.envato||{}).status==='preview')W(`B-roll "${b.src}" es la vista previa con marca de agua: falta licenciarlo.`);}
// ── Cámara ──
const modes={};framing.forEach(f=>modes[f.mode]=(modes[f.mode]||0)+1);
if(framing.length)O('Encuadres: '+Object.entries(modes).map(([k,v])=>`${k} ×${v}`).join(' · ')+'.');
for(let i=1;i<framing.length;i++){const a=framing[i-1],b=framing[i];if(Math.abs(a.s1-b.s0)<6&&!(a.mode==='wide'&&b.mode==='wide'&&(a.s0!==a.s1)))W(`Jump cut sin cambio de encuadre entre los clips ${a.i} y ${b.i} (${a.s1}% → ${b.s0}%).`);}
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
if(M){const tot=edl.total,hook=Math.min(Math.max(...edl.clips.filter(c=>c.seg===0).map(c=>c.tl_out)),3.5*FPS)/FPS,sp=T-(cfg.tail??1.2);
  const pts=[[0,M.hook_gain??.3],[hook,M.hook_gain??.3],[hook+.6,M.bed_gain??.08],[sp,M.bed_gain??.08],[sp+.4,M.outro_gain??.22],[T-.8,M.outro_gain??.22],[T,0]];
  html+=`<svg style="position:absolute;left:120px;top:330px" width=1500 height=60><polyline fill=none stroke=#c6f stroke-width=2 points="${pts.map(([t,g])=>`${t*PX},${60-g/0.35*56}`).join(' ')}"/></svg><div class=lab style="top:350px">Música</div>`;}
for(let s=0;s<=T;s+=5)html+=`<div style="position:absolute;left:${120+s*PX}px;top:400px;color:#777;font-size:10px">${s}s</div><div style="position:absolute;left:${120+s*PX}px;top:14px;height:380px;border-left:1px solid #222"></div>`;
html+='</body></html>';fs.writeFileSync(path.join(WD,'timeline.html'),html);
(async()=>{try{const puppeteer=require(path.join(__dirname,'..','engine','node_modules','puppeteer-core'));
  const CHROME=process.env.CHROME||['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Chromium.app/Contents/MacOS/Chromium','/usr/bin/google-chrome','/usr/bin/chromium'].find(p=>fs.existsSync(p));
  const b=await puppeteer.launch({executablePath:CHROME,headless:true,args:['--allow-file-access-from-files']});const p=await b.newPage();
  await p.setViewport({width:1640,height:430});await p.goto('file://'+path.join(WD,'timeline.html'));await p.screenshot({path:path.join(WD,'timeline.png')});await b.close();
  console.log('línea de tiempo:',path.join(WD,'timeline.png'));}catch(e){console.log('(no pude dibujar timeline.png:',e.message.split('\n')[0]+')');}
  try{require('child_process').spawnSync('python3',['-I','-c',`import sys;sys.path.insert(0,${JSON.stringify(__dirname)});import timing;timing.log(${JSON.stringify(WD)},'Dirección creativa',${(Date.now()-t0)/1000})`]);}catch(e){}})();
