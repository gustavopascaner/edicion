// Paso 5: renderiza MG + subtítulos a .mov con alfa (QuickTime Animation).
// uso: node render.js <workdir> [--only=<regex>] [--test] [--par=6]
//   --test  : en vez de .mov, exporta PNGs de prueba a <workdir>/test (T=tiempos, ej T=end-0.4 o T=0.5,mid)
// Lee <workdir>/config.json, edl.json y jobs.js (module.exports = ctx => { ...J(), B(), X()... }).
const fs=require('fs'),path=require('path'),{spawn}=require('child_process');
const ENG=path.join(__dirname,'..','engine');
const puppeteer=require(path.join(ENG,'node_modules','puppeteer-core'));
// Chrome/Chromium: variable CHROME o rutas habituales de macOS / Linux / Windows
const CHROME=process.env.CHROME||['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser','C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'].find(p=>fs.existsSync(p));
const WD=path.resolve(process.argv[2]);
const cfg=JSON.parse(fs.readFileSync(path.join(WD,'config.json')));
const FPS=cfg.fps||30;
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
// S(spec, segundo del evento, {gain, dur, at}) → pone un sonido de la librería en la línea de tiempo
const missing=new Set();
function S(spec,t,o={}){const id=pick(spec),m=CAT.sounds[id];last.id=id;
  if(!fs.existsSync(path.join(SFXDIR,m.file))){if(!missing.size)console.warn('⚠️  Faltan sonidos de la librería (instalar edicion-sfx.zip, ver README). Se omiten:');
    if(!missing.has(id)){missing.add(id);console.warn('   ',id);}return;}
  let start=t-m.anchor,sin=0;if(start<0){sin=-start;start=0;}
  const dur=Math.min(o.dur||m.dur,m.dur-sin);if(dur<=0.02)return;
  sfx.push({id,file:m.file,start:+start.toFixed(3),sin:+sin.toFixed(3),dur:+dur.toFixed(3),fdur:m.dur,gain:o.gain??CAT.categories[m.cat].gain,at:+t.toFixed(3)});}
// J(id, escena, pista: 'ov'|'ov2'|'fs', inicio, fin, params, sfx)
//   sfx: 'pop' · 'whoosh' · 'ding' · id… | ['whoosh',['pop',0.8],['ding',1.6,{gain:.3}]] (segundos desde el inicio del gráfico) | null
function J(id,scene,track,start,end,p,cue){jobs.push({id,scene,track,start:+start.toFixed(3),end:+end.toFixed(3),p:p||{},sfx:cue||null});
  if(!cue)return;const tuple=Array.isArray(cue)&&typeof cue[1]==='number';const list=Array.isArray(cue)&&!tuple?cue:[cue];
  for(const c of list){const [spec,at=0,o={}]=Array.isArray(c)?c:[c];S(spec,start+at,o);}}
// B(clave de config.broll, segundo de origen, inicio en timeline, duración, [zoomInicio%, zoomFin%] para fotos)
function B(src,sin,start,dur,kb){broll.push({src,sin:+sin.toFixed(3),start:+start.toFixed(3),dur:+dur.toFixed(3),kb:kb||null});}
// X(archivo de audio absoluto, inicio, duración, ganancia lineal, segundo de origen)
function X(file,start,dur,gain,sin=0){extraSfx.push({file,start:+start.toFixed(3),dur:+dur.toFixed(3),gain,sin});}
require(path.join(WD,'jobs.js'))({J,B,X,S,W,C,CE,R,H,SG,edl,cfg,FPS});
// subtítulos: un clip por clip de V1
const KW=new Set((cfg.keywords||[]).map(norm));
edl.clips.forEach((c,i)=>{const s=c.tl_in/FPS,e=c.tl_out/FPS;
  const groups=edl.caps.filter(g=>g.clip===i).map(g=>({s:R(s,g.tl_in/FPS),e:R(s,g.tl_out/FPS),words:g.words.map(w=>({w:w.w.replace(/[¿?:]/g,'').replace(/,$/,''),s:R(s,w.s/FPS),e:R(s,w.e/FPS),k:KW.has(norm(w.w))}))}));
  J(`cap_${String(i).padStart(2,'0')}`,'cap','cap',s,e,{groups});});
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
    await page.goto('file://'+path.join(ENG,'engine.html'));await page.evaluate(()=>document.fonts.ready);
    await page.evaluate((cc)=>{window.CAPCOL=cc;window.FMT={k:v=>(v/1000).toFixed(1).replace('.',',')+'K',m:v=>(v/1e6).toFixed(2).replace('.',',')+'M'}},cfg.caption_colors||null);
    while(qi<list.length){const j=list[qi++];const dur=j.end-j.start;const nf=Math.round(dur*FPS);
      try{await page.evaluate((j,dur)=>{if(j.p.tiles)j.p.tiles.forEach(t=>t.fmt=FMT[t.fmt]);setup(j.scene,j.p,dur);},j,dur);}catch(e){console.log('ERR',j.id,e.message.split('\n')[0]);continue;}
      if(test){const ts=(process.env.T||'end-0.4').split(',');
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
  console.log('SFX:\n'+sfx.map(x=>`  ${x.at.toFixed(2).padStart(6)}  ${x.id.padEnd(16)} gain ${x.gain}`).join('\n'));}
else main().catch(e=>{console.error(e);process.exit(1)});
