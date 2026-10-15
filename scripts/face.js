// Paso 0.4: detecta dónde está la cara en el crudo (Chrome FaceDetector: macOS Vision / Windows FaceAnalysis)
// y decide dónde van los subtítulos y los motion graphics para no pisarla.
// uso: node face.js <workdir> [--frames=10]   → config.face {top,bottom,left,right,source:'auto'} + <workdir>/face.png
// Si config.face.manual es true no se toca (para corregir a mano). Si no detecta, avisa: estimarla mirando face.png.
const fs=require('fs'),path=require('path'),os=require('os'),{spawnSync}=require('child_process');
const ENG=path.join(__dirname,'..','engine'),puppeteer=require(path.join(ENG,'node_modules','puppeteer-core'));
const {CHROME,fileURL,logTime}=require('./platform.js');
const WD=path.resolve(process.argv[2]),CF=path.join(WD,'config.json'),cfg=JSON.parse(fs.readFileSync(CF,'utf8'));
const NF=+((process.argv.find(a=>a.startsWith('--frames='))||'--frames=10').slice(9));
const W=1080,H=1920,t0=Date.now();
const dur=+spawnSync('ffprobe',['-v','error','-show_entries','format=duration','-of','csv=p=0',cfg.src],{encoding:'utf8'}).stdout;
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'face'));const frames=[];
for(let i=0;i<NF;i++){const t=dur*(.06+.88*i/(NF-1||1)),f=path.join(dir,`f${i}.png`);
  spawnSync('ffmpeg',['-v','error','-y','-ss',t.toFixed(2),'-i',cfg.src,'-frames:v','1','-vf',`scale=${W}:${H}`,f]);if(fs.existsSync(f))frames.push(f);}
const q=(a,p)=>{const s=[...a].sort((x,y)=>x-y);return s[Math.min(s.length-1,Math.max(0,Math.round(p*(s.length-1))))];};
(async()=>{
  if(cfg.face&&cfg.face.manual){console.log('config.face.manual = true: no se modifica',JSON.stringify(cfg.face));return;}
  const br=await puppeteer.launch({executablePath:CHROME,headless:true,args:['--enable-experimental-web-platform-features','--allow-file-access-from-files']});
  const pg=await br.newPage();const boxes=[];let api=true;
  for(const f of frames){await pg.goto(fileURL(f));
    const r=await pg.evaluate(async()=>{if(!('FaceDetector' in window))return null;const im=document.querySelector('img');await im.decode();
      const fs=await new FaceDetector({fastMode:false,maxDetectedFaces:4}).detect(im);
      return fs.map(x=>({x:x.boundingBox.x,y:x.boundingBox.y,w:x.boundingBox.width,h:x.boundingBox.height}));});
    if(r===null){api=false;break;}
    if(r.length)boxes.push(r.sort((a,b)=>b.w*b.h-a.w*a.h)[0]);}
  await br.close();
  const png=path.join(WD,'face.png');
  if(!api||boxes.length<Math.max(2,NF/3)){
    spawnSync('ffmpeg',['-v','error','-y','-i',frames[Math.floor(frames.length/2)],png]);
    console.log(`⚠️  No se pudo detectar la cara (${api?'muy pocas detecciones':'Chrome sin FaceDetector'}). Mirar ${png} y poner a mano en config.json:\n   "face": {"top": <arriba de la cabeza 0–1>, "bottom": <mentón 0–1>, "manual": true}`);return;}
  // la caja del detector va de las cejas al mentón: ampliar a la cabeza (pelo) y un poco de cuello. Percentiles para cubrir el movimiento.
  const top=q(boxes.map(b=>b.y-.45*b.h),.1),bottom=q(boxes.map(b=>b.y+1.08*b.h),.9),left=q(boxes.map(b=>b.x-.12*b.w),.1),right=q(boxes.map(b=>b.x+1.12*b.w),.9);
  cfg.face={...(cfg.face||{}),top:+(Math.max(0,top)/H).toFixed(3),bottom:+(Math.min(H,bottom)/H).toFixed(3),left:+(Math.max(0,left)/W).toFixed(3),right:+(Math.min(W,right)/W).toFixed(3),source:'auto',frames:boxes.length};
  fs.writeFileSync(CF,JSON.stringify(cfg,null,1));
  const L=require('./layout.js')(cfg);
  // imagen de control: cara (rojo), zonas libres (verde), subtítulos (azul)
  const db=[`drawbox=x=${L.face[0]}:y=${L.face[1]}:w=${L.face[2]-L.face[0]}:h=${L.face[3]-L.face[1]}:color=red@0.9:t=8`,
    ...L.zones.filter(z=>z[1]-z[0]>40).map(z=>`drawbox=x=20:y=${z[0]}:w=${W-40}:h=${z[1]-z[0]}:color=green@0.25:t=fill`),
    `drawbox=x=70:y=${L.capTop}:w=${W-140}:h=${L.capH}:color=blue@0.35:t=fill`];
  spawnSync('ffmpeg',['-v','error','-y','-i',frames[Math.floor(frames.length/2)],'-vf',db.join(','),png]);
  console.log(`cara: ${Math.round(cfg.face.top*100)}–${Math.round(cfg.face.bottom*100)} % del alto (${boxes.length}/${frames.length} cuadros) · ${L.note}`);
  console.log(`control: ${png} (rojo = cara con el zoom máximo, verde = zonas libres para MG, azul = subtítulos)`);
  logTime(WD,'Detección de cara',(Date.now()-t0)/1000);
})().catch(e=>{console.error('✗',e.message);process.exit(1);});
